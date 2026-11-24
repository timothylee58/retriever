"""Ledger writes. One merchant per database in this scaffold."""

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings
from app.domain.fallback import choose_fallback
from app.domain.forecast import build_series, discount_allowed
from app.domain.matcher import OpenInvoice, tier1, tier2
from app.domain.rescue import classify_failure, draft_message
from app.llm import suggest_match
from app.signatures import hitpay_valid, stripe_valid

MONEY = {"SGD": "S$", "MYR": "RM"}
# HitPay rejects the short names. paynow is paynow_online on the sandbox.
_HITPAY_METHOD = {"paynow": "paynow_online", "duitnow": "duitnow_online"}
METHOD_LABEL = {
    "paynow": "PayNow",
    "duitnow": "DuitNow",
    "fpx": "FPX",
    "tng": "Touch 'n Go",
    "boost": "Boost",
    "grabpay": "GrabPay",
    "shopeepay": "ShopeePay",
}


def _pg_array(values: list[str]) -> str:
    return "{" + ",".join(values) + "}"


def ensure_merchant(engine: Engine) -> str:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM merchants LIMIT 1")).first()
    if row:
        return str(row[0])
    merchant_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO merchants
                  (id, name, country, default_currency, timezone, hitpay_mode, settings)
                VALUES
                  (:id, 'Mei Ling Tuition', 'SG', 'SGD', 'Asia/Singapore', 'sandbox',
                   CAST(:settings AS jsonb))
                """
            ),
            {
                "id": merchant_id,
                "settings": json.dumps(
                    {
                        "churn_after_days": 7,
                        "auto_match_threshold": 0.9,
                        "discount_max_pct": 2.0,
                        "enabled_methods": ["paynow", "card", "grabpay", "shopeepay"],
                        "daily_outflow_minor": 20000,
                        "buffer_minor": 50000,
                        "daily_financing_rate": 0.0005,
                    }
                ),
            },
        )
    return merchant_id


def _event(conn, merchant_id: str, actor: str, type_: str, subject_type: str, subject_id: str, reason: str, payload: dict):
    conn.execute(
        text(
            """
            INSERT INTO events (merchant_id, actor, type, subject_type, subject_id, reason, payload)
            VALUES (:m, :actor, :type, :st, :sid, :reason, CAST(:payload AS jsonb))
            """
        ),
        {
            "m": merchant_id,
            "actor": actor,
            "type": type_,
            "st": subject_type,
            "sid": subject_id,
            "reason": reason,
            "payload": json.dumps(payload),
        },
    )


def create_invoice(
    engine: Engine,
    settings: Settings,
    *,
    customer_name: str,
    email: str | None,
    ref: str,
    amount_minor: int,
    currency: str,
    due_at: datetime,
) -> dict:
    merchant_id = ensure_merchant(engine)
    with engine.begin() as conn:
        customer = conn.execute(
            text(
                """
                INSERT INTO customers (merchant_id, display_name, email)
                VALUES (:m, :name, :email)
                RETURNING id
                """
            ),
            {"m": merchant_id, "name": customer_name, "email": email},
        ).first()
        invoice = conn.execute(
            text(
                """
                INSERT INTO invoices (merchant_id, customer_id, ref, amount_minor, currency, due_at, status)
                VALUES (:m, :c, :ref, :amt, :cur, :due, 'issued')
                RETURNING id
                """
            ),
            {
                "m": merchant_id,
                "c": customer[0],
                "ref": ref,
                "amt": amount_minor,
                "cur": currency,
                "due": due_at,
            },
        ).first()
        invoice_id = str(invoice[0])
        request = _create_payment_request(
            conn,
            settings,
            merchant_id=merchant_id,
            invoice_id=invoice_id,
            ref=ref,
            amount_minor=amount_minor,
            currency=currency,
            methods=["paynow"] if currency == "SGD" else ["duitnow"],
            purpose="primary",
        )
        _event(
            conn,
            merchant_id,
            "system",
            "invoice.issued",
            "invoice",
            invoice_id,
            f"Issued {ref}.",
            {"ref": ref, "amount_minor": amount_minor},
        )
    return {"invoice_id": invoice_id, "customer_id": str(customer[0]), **request}


def _create_payment_request(conn, settings: Settings, **kwargs) -> dict:
    provider_request_id = f"dry_{uuid.uuid4().hex[:12]}"
    url = f"https://sandbox.hit-pay.com/pay/{provider_request_id}"
    qr = f"PAYNOW:{kwargs['ref']}:{kwargs['amount_minor']}"
    if not settings.dry_run and settings.hitpay_api_key:
        # Live call is intentionally not the default. The sandbox field list
        # (expiry, payment_methods) is still marked unverified in the spec.
        import httpx

        response = httpx.post(
            f"{settings.hitpay_api_base}/v1/payment-requests",
            headers={"X-BUSINESS-API-KEY": settings.hitpay_api_key},
            json={
                "amount": f"{kwargs['amount_minor'] / 100:.2f}",
                "currency": kwargs["currency"],
                "reference_number": kwargs["ref"],
                **({"webhook": settings.hitpay_webhook_url} if settings.hitpay_webhook_url else {}),
                # The sandbox rejects grabpay and shopeepay on this account.
                # Send the chosen fallback only.
                "payment_methods": [_HITPAY_METHOD.get(kwargs["methods"][0], kwargs["methods"][0])],
            },
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        provider_request_id = str(body.get("id") or provider_request_id)
        url = body.get("url") or url
        qr = body.get("qr_code_data") or qr
    row = conn.execute(
        text(
            """
            INSERT INTO payment_requests
              (merchant_id, invoice_id, provider, provider_request_id, methods, url, qr_payload, purpose, status)
            VALUES
              (:m, :inv, 'hitpay', :pid, CAST(:methods AS payment_method[]), :url, :qr, :purpose, 'open')
            RETURNING id
            """
        ),
        {
            "m": kwargs["merchant_id"],
            "inv": kwargs["invoice_id"],
            "pid": provider_request_id,
            "methods": _pg_array(kwargs["methods"]),
            "url": url,
            "qr": qr,
            "purpose": kwargs["purpose"],
        },
    ).first()
    _event(
        conn,
        kwargs["merchant_id"],
        "system",
        "payment_request.created",
        "payment_request",
        str(row[0]),
        f"{kwargs['purpose']} link for {kwargs['ref']}.",
        {"url": url, "dry_run": settings.dry_run},
    )
    return {
        "payment_request_id": str(row[0]),
        "provider_request_id": provider_request_id,
        "url": url,
        "qr_payload": qr,
    }


def accept_webhook(engine: Engine, settings: Settings, provider: str, raw: bytes, header: str | None) -> tuple[int, str]:
    merchant_id = ensure_merchant(engine)
    if provider == "hitpay":
        valid = hitpay_valid(raw, header, settings.hitpay_webhook_salt)
    elif provider == "stripe":
        valid = stripe_valid(raw, header, settings.stripe_webhook_secret)
    else:
        return 404, "unknown provider"
    try:
        payload = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        payload = {}
    event_id = str(payload.get("id") or uuid.uuid5(uuid.NAMESPACE_URL, raw.hex()))
    with engine.begin() as conn:
        inserted = conn.execute(
            text(
                """
                INSERT INTO webhook_inbox
                  (merchant_id, provider, provider_event_id, signature_valid, raw_body)
                VALUES (:m, :p, :eid, :ok, :body)
                ON CONFLICT (provider, provider_event_id) DO NOTHING
                RETURNING id
                """
            ),
            {"m": merchant_id, "p": provider, "eid": event_id, "ok": valid, "body": raw},
        ).first()
        if inserted is None:
            return 200, "duplicate"
        if not valid:
            return 401, "invalid signature"
        conn.execute(
            text(
                """
                INSERT INTO jobs (merchant_id, kind, payload)
                VALUES (:m, 'process_webhook', CAST(:payload AS jsonb))
                """
            ),
            {"m": merchant_id, "payload": json.dumps({"inbox_id": str(inserted[0])})},
        )
    return 200, "queued"


def process_jobs(engine: Engine, settings: Settings, limit: int = 20) -> int:
    processed = 0
    for _ in range(limit):
        with engine.begin() as conn:
            job = conn.execute(
                text(
                    """
                    UPDATE jobs SET status = 'running', locked_at = now(), attempts = attempts + 1
                    WHERE id = (
                      SELECT id FROM jobs
                      WHERE status = 'queued' AND run_after <= now()
                      ORDER BY created_at
                      FOR UPDATE SKIP LOCKED
                      LIMIT 1
                    )
                    RETURNING id, kind, payload, merchant_id
                    """
                )
            ).mappings().first()
            if job is None:
                break
            _run_job(conn, settings, job)
            conn.execute(text("UPDATE jobs SET status = 'done' WHERE id = :id"), {"id": job["id"]})
        processed += 1
    return processed


def _run_job(conn, settings: Settings, job) -> None:
    payload = job["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    if job["kind"] == "process_webhook":
        _process_webhook(conn, settings, str(job["merchant_id"]), payload["inbox_id"])
    elif job["kind"] == "match_payment":
        _match_payment(conn, settings, str(job["merchant_id"]), payload["payment_id"])
    elif job["kind"] == "rescue_attempt":
        _rescue(conn, settings, str(job["merchant_id"]), payload["attempt_id"])
    else:
        raise ValueError(f"unknown job {job['kind']}")


def _process_webhook(conn, settings: Settings, merchant_id: str, inbox_id: str) -> None:
    row = conn.execute(
        text("SELECT provider, raw_body FROM webhook_inbox WHERE id = :id"),
        {"id": inbox_id},
    ).mappings().first()
    body = json.loads(bytes(row["raw_body"]).decode())
    provider = row["provider"]
    if provider == "stripe":
        _normalise_stripe(conn, merchant_id, body)
    else:
        _normalise_hitpay(conn, merchant_id, body)
    conn.execute(text("UPDATE webhook_inbox SET processed_at = now() WHERE id = :id"), {"id": inbox_id})


def _normalise_stripe(conn, merchant_id: str, body: dict) -> None:
    kind = body.get("type")
    obj = body.get("data", {}).get("object", {})
    if kind == "payment_intent.payment_failed":
        err = (obj.get("last_payment_error") or {}).get("decline_code") or "generic_decline"
        _insert_attempt(
            conn,
            merchant_id,
            provider_attempt_id=obj["id"],
            method="card",
            amount_minor=int(obj.get("amount") or 0),
            currency=(obj.get("currency") or "sgd").upper(),
            status="failed",
            failure_code=err,
            failure_class=classify_failure(err, "stripe"),
            reference=(obj.get("metadata") or {}).get("reference"),
        )
        return
    if kind == "payment_intent.succeeded":
        _insert_payment(
            conn,
            merchant_id,
            provider="stripe",
            provider_payment_id=obj["id"],
            amount_minor=int(obj.get("amount") or 0),
            currency=(obj.get("currency") or "sgd").upper(),
            method="card",
            payer_name=(obj.get("metadata") or {}).get("payer_name"),
            payer_reference=(obj.get("metadata") or {}).get("reference"),
        )
        return
    _event(conn, merchant_id, "provider:stripe", "webhook.ignored", "webhook", str(uuid.uuid4()), f"Ignored {kind}.", {})


def _normalise_hitpay(conn, merchant_id: str, body: dict) -> None:
    status = (body.get("status") or "").lower()
    reference = body.get("reference_number")
    amount = body.get("amount")
    amount_minor = int(round(float(amount) * 100)) if amount is not None else int(body.get("amount_minor") or 0)
    currency = (body.get("currency") or "SGD").upper()
    method = (body.get("payment_method") or "paynow").lower()
    if method not in METHOD_LABEL and method != "card":
        method = "paynow"
    payment_id = str(body.get("id") or body.get("payment_id"))
    if status == "completed":
        _insert_payment(
            conn,
            merchant_id,
            provider="hitpay",
            provider_payment_id=payment_id,
            amount_minor=amount_minor,
            currency=currency,
            method=method,
            payer_name=body.get("payer_name"),
            payer_reference=reference,
        )
    elif status in {"failed", "expired"}:
        _insert_attempt(
            conn,
            merchant_id,
            provider_attempt_id=payment_id,
            method=method,
            amount_minor=amount_minor,
            currency=currency,
            status="expired" if status == "expired" else "failed",
            failure_code=status,
            failure_class=classify_failure(status, "hitpay"),
            reference=reference,
        )
    else:
        _event(conn, merchant_id, "provider:hitpay", "webhook.ignored", "webhook", str(uuid.uuid4()), f"Ignored status {status}.", {})


def _insert_attempt(conn, merchant_id: str, **kwargs) -> None:
    row = conn.execute(
        text(
            """
            INSERT INTO payment_attempts
              (merchant_id, provider_attempt_id, method, amount_minor, currency, status, failure_code, failure_class)
            VALUES (:m, :pid, CAST(:method AS payment_method), :amt, :cur, CAST(:status AS attempt_status), :code, CAST(:klass AS failure_class))
            ON CONFLICT (provider_attempt_id) DO NOTHING
            RETURNING id
            """
        ),
        {
            "m": merchant_id,
            "pid": kwargs["provider_attempt_id"],
            "method": kwargs["method"],
            "amt": kwargs["amount_minor"],
            "cur": kwargs["currency"],
            "status": kwargs["status"],
            "code": kwargs["failure_code"],
            "klass": kwargs["failure_class"],
        },
    ).first()
    if row is None:
        return
    attempt_id = str(row[0])
    _event(conn, merchant_id, "provider", "attempt.failed", "payment_attempt", attempt_id, kwargs["failure_class"], {})
    conn.execute(
        text("INSERT INTO jobs (merchant_id, kind, payload) VALUES (:m, 'rescue_attempt', CAST(:p AS jsonb))"),
        {"m": merchant_id, "p": json.dumps({"attempt_id": attempt_id, "reference": kwargs.get("reference")})},
    )


def _insert_payment(conn, merchant_id: str, **kwargs) -> None:
    row = conn.execute(
        text(
            """
            INSERT INTO payments
              (merchant_id, provider, provider_payment_id, amount_minor, currency, method, payer_name, payer_reference, received_at)
            VALUES (:m, :prov, :pid, :amt, :cur, CAST(:method AS payment_method), :name, :ref, now())
            ON CONFLICT (provider_payment_id) DO NOTHING
            RETURNING id
            """
        ),
        {
            "m": merchant_id,
            "prov": kwargs["provider"],
            "pid": kwargs["provider_payment_id"],
            "amt": kwargs["amount_minor"],
            "cur": kwargs["currency"],
            "method": kwargs["method"],
            "name": kwargs.get("payer_name"),
            "ref": kwargs.get("payer_reference"),
        },
    ).first()
    if row is None:
        return
    payment_id = str(row[0])
    _event(conn, merchant_id, f"provider:{kwargs['provider']}", "payment.received", "payment", payment_id, "Payment received.", {})
    conn.execute(
        text("INSERT INTO jobs (merchant_id, kind, payload) VALUES (:m, 'match_payment', CAST(:p AS jsonb))"),
        {"m": merchant_id, "p": json.dumps({"payment_id": payment_id})},
    )


def _open_invoices(conn, merchant_id: str) -> list[OpenInvoice]:
    rows = conn.execute(
        text(
            """
            SELECT i.id, i.ref, i.amount_minor, i.amount_paid_minor, i.currency, i.due_at,
                   c.display_name, c.aliases
            FROM invoices i JOIN customers c ON c.id = i.customer_id
            WHERE i.merchant_id = :m AND i.status IN ('issued','overdue','partially_paid')
            """
        ),
        {"m": merchant_id},
    ).mappings()
    found = []
    for row in rows:
        due = row["due_at"]
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        found.append(
            OpenInvoice(
                str(row["id"]),
                row["ref"],
                int(row["amount_minor"]),
                int(row["amount_paid_minor"]),
                row["currency"].strip(),
                due,
                row["display_name"],
                list(row["aliases"] or []),
            )
        )
    return found


def _match_payment(conn, settings: Settings, merchant_id: str, payment_id: str) -> None:
    payment = conn.execute(text("SELECT * FROM payments WHERE id = :id"), {"id": payment_id}).mappings().first()
    invoices = _open_invoices(conn, merchant_id)
    received = payment["received_at"]
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)
    decision = tier1(payment["payer_reference"], payment["currency"].strip(), invoices)
    if decision is not None and decision.invoice_id is None and "currency" in decision.reason:
        conn.execute(
            text("UPDATE payments SET match_status = 'unmatched', match_tier = 1 WHERE id = :id"),
            {"id": payment_id},
        )
        _event(conn, merchant_id, "agent:matcher", "payment.unmatched", "payment", payment_id, decision.reason, {})
        return
    if decision is None or decision.invoice_id is None:
        decision = tier2(
            amount_minor=int(payment["amount_minor"]),
            currency=payment["currency"].strip(),
            payer_name=payment["payer_name"],
            received_at=received,
            invoices=invoices,
        )
    if decision is not None and decision.auto and decision.invoice_id:
        _allocate(conn, merchant_id, payment_id, decision.invoice_id, int(payment["amount_minor"]), None, decision)
        return
    suggestion = suggest_match(
        settings,
        amount_minor=int(payment["amount_minor"]),
        currency=payment["currency"].strip(),
        payer_name=payment["payer_name"],
        invoices=invoices,
    )
    if suggestion.invoice_id is None:
        conn.execute(
            text("UPDATE payments SET match_status = 'unmatched', match_tier = 3 WHERE id = :id"),
            {"id": payment_id},
        )
        _event(conn, merchant_id, "agent:matcher", "payment.unmatched", "payment", payment_id, suggestion.reason, {})
        return
    conn.execute(
        text(
            """
            INSERT INTO match_suggestions (merchant_id, payment_id, invoice_id, confidence, reason, model)
            VALUES (:m, :p, :i, :c, :r, :model)
            """
        ),
        {
            "m": merchant_id,
            "p": payment_id,
            "i": suggestion.invoice_id,
            "c": suggestion.confidence,
            "r": suggestion.reason,
            "model": suggestion.model,
        },
    )
    conn.execute(
        text("UPDATE payments SET match_status = 'suggested', match_tier = 3 WHERE id = :id"),
        {"id": payment_id},
    )
    approval = conn.execute(
        text(
            """
            INSERT INTO approvals (merchant_id, kind, subject_id, summary)
            VALUES (:m, 'match', :s, :summary)
            RETURNING id
            """
        ),
        {"m": merchant_id, "s": payment_id, "summary": suggestion.reason},
    ).first()
    _event(
        conn,
        merchant_id,
        "agent:matcher",
        "payment.suggested",
        "approval",
        str(approval[0]),
        suggestion.reason,
        {"confidence": suggestion.confidence, "model": suggestion.model},
    )


def _allocate(conn, merchant_id, payment_id, invoice_id, payment_amount, approved_by, decision) -> None:
    invoice = conn.execute(text("SELECT * FROM invoices WHERE id = :id"), {"id": invoice_id}).mappings().first()
    outstanding = int(invoice["amount_minor"]) - int(invoice["amount_paid_minor"])
    applied = min(payment_amount, outstanding)
    remainder = payment_amount - applied
    if applied <= 0:
        return
    conn.execute(
        text(
            """
            INSERT INTO allocations (merchant_id, payment_id, invoice_id, amount_minor, approved_by)
            VALUES (:m, :p, :i, :a, :by)
            """
        ),
        {"m": merchant_id, "p": payment_id, "i": invoice_id, "a": applied, "by": approved_by},
    )
    new_paid = int(invoice["amount_paid_minor"]) + applied
    status = "paid" if new_paid >= int(invoice["amount_minor"]) else "partially_paid"
    conn.execute(
        text("UPDATE invoices SET amount_paid_minor = :paid, status = CAST(:status AS invoice_status) WHERE id = :id"),
        {"paid": new_paid, "status": status, "id": invoice_id},
    )
    conn.execute(
        text("UPDATE payments SET match_status = 'matched', match_tier = :tier WHERE id = :id"),
        {"tier": decision.tier if decision else 0, "id": payment_id},
    )
    if approved_by and decision is None:
        pass
    payer = conn.execute(text("SELECT payer_name FROM payments WHERE id = :id"), {"id": payment_id}).first()
    if approved_by and payer and payer[0]:
        conn.execute(
            text("UPDATE customers SET aliases = aliases || ARRAY[:name] WHERE id = :id AND NOT (:name = ANY(aliases))"),
            {"name": payer[0], "id": invoice["customer_id"]},
        )
    _event(
        conn,
        merchant_id,
        "user:"+approved_by if approved_by else "agent:matcher",
        "payment.matched",
        "payment",
        payment_id,
        decision.reason if decision else "Owner allocation.",
        {"invoice_id": invoice_id, "applied": applied, "remainder": remainder},
    )
    _recover_rescue_if_invoice_paid(conn, merchant_id, invoice_id)
    if remainder > 0:
        _event(
            conn,
            merchant_id,
            "system",
            "payment.overpaid",
            "payment",
            payment_id,
            f"Unallocated remainder {remainder}. Schema has no overpayment approval kind, so this is an event.",
            {"remainder": remainder},
        )


def _recover_rescue_if_invoice_paid(conn, merchant_id: str, invoice_id: str) -> None:
    invoice = conn.execute(text("SELECT status FROM invoices WHERE id = :id"), {"id": invoice_id}).first()
    if invoice[0] != "paid":
        return
    rows = conn.execute(
        text(
            """
            SELECT r.id, r.status FROM rescues r
            JOIN payment_requests pr ON pr.id = r.fallback_request_id
            WHERE pr.invoice_id = :inv AND r.status IN ('offered','churned')
            """
        ),
        {"inv": invoice_id},
    ).mappings()
    for rescue in rows:
        new_status = "won_back" if rescue["status"] == "churned" else "recovered"
        conn.execute(
            text(
                """
                UPDATE rescues
                SET status = CAST(:status AS rescue_status), recovered_at = now()
                WHERE id = :id
                """
            ),
            {"status": new_status, "id": rescue["id"]},
        )
        _event(conn, merchant_id, "system", f"rescue.{new_status}", "rescue", str(rescue["id"]), "Fallback payment matched.", {})


def _rescue(conn, settings: Settings, merchant_id: str, attempt_id: str) -> None:
    attempt = conn.execute(text("SELECT * FROM payment_attempts WHERE id = :id"), {"id": attempt_id}).mappings().first()
    if conn.execute(text("SELECT 1 FROM rescues WHERE failed_attempt_id = :id"), {"id": attempt_id}).first():
        return
    reference_job = conn.execute(
        text("SELECT payload FROM jobs WHERE kind = 'rescue_attempt' AND payload->>'attempt_id' = :id ORDER BY created_at DESC LIMIT 1"),
        {"id": attempt_id},
    ).first()
    reference = None
    if reference_job and reference_job[0]:
        payload = reference_job[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        reference = payload.get("reference")
    invoice = None
    if reference:
        invoice = conn.execute(
            text("SELECT i.*, c.pause_chasing, c.last_success_method FROM invoices i JOIN customers c ON c.id = i.customer_id WHERE i.ref = :ref"),
            {"ref": reference},
        ).mappings().first()
    rescue = conn.execute(
        text(
            """
            INSERT INTO rescues (merchant_id, failed_attempt_id, amount_minor, currency, status, message_channel)
            VALUES (:m, :a, :amt, :cur, 'opened', 'dashboard')
            RETURNING id
            """
        ),
        {
            "m": merchant_id,
            "a": attempt_id,
            "amt": attempt["amount_minor"],
            "cur": attempt["currency"],
        },
    ).first()
    rescue_id = str(rescue[0])
    if invoice and invoice["pause_chasing"]:
        _event(conn, merchant_id, "agent:rescue", "rescue.paused", "rescue", rescue_id, "Customer pause_chasing is set.", {})
        return
    merchant = conn.execute(text("SELECT country, settings FROM merchants WHERE id = :id"), {"id": merchant_id}).mappings().first()
    settings_json = merchant["settings"] or {}
    enabled = settings_json.get("enabled_methods") or ["paynow"]
    methods = choose_fallback(
        country=merchant["country"].strip(),
        failed_method=str(attempt["method"]),
        last_success_method=str(invoice["last_success_method"]) if invoice and invoice["last_success_method"] else None,
        enabled_methods=enabled,
        amount_minor=int(attempt["amount_minor"]),
    )
    ref = reference or "UNLINKED"
    link = _create_payment_request(
        conn,
        settings,
        merchant_id=merchant_id,
        invoice_id=str(invoice["id"]) if invoice else None,
        ref=ref,
        amount_minor=int(attempt["amount_minor"]),
        currency=attempt["currency"].strip(),
        methods=methods,
        purpose="rescue",
    )
    symbol = MONEY.get(attempt["currency"].strip(), "")
    label = METHOD_LABEL.get(methods[0], methods[0])
    message = draft_message(
        ref=ref,
        amount_label=f"{symbol}{int(attempt['amount_minor'])/100:.2f}",
        method_label=label,
        url=link["url"],
    )
    conn.execute(
        text(
            """
            UPDATE rescues
            SET fallback_request_id = :req, message_draft = :msg, status = 'offered'
            WHERE id = :id
            """
        ),
        {"req": link["payment_request_id"], "msg": message, "id": rescue_id},
    )
    _event(conn, merchant_id, "agent:rescue", "rescue.link_created", "rescue", rescue_id, message, {"methods": methods})


def decide_approval(engine: Engine, approval_id: str, approve: bool, actor: str, note: str) -> dict:
    with engine.begin() as conn:
        approval = conn.execute(text("SELECT * FROM approvals WHERE id = :id"), {"id": approval_id}).mappings().first()
        if approval is None:
            raise KeyError(approval_id)
        status = "approved" if approve else "rejected"
        conn.execute(
            text(
                """
                UPDATE approvals
                SET status = CAST(:status AS approval_status), decided_by = :by, decided_at = now(), decision_note = :note
                WHERE id = :id
                """
            ),
            {"status": status, "by": actor, "note": note, "id": approval_id},
        )
        _event(
            conn,
            str(approval["merchant_id"]),
            f"user:{actor}",
            f"approval.{status}",
            "approval",
            approval_id,
            note or status,
            {"kind": approval["kind"]},
        )
        if approve and approval["kind"] == "match":
            suggestion = conn.execute(
                text("SELECT invoice_id FROM match_suggestions WHERE payment_id = :id ORDER BY created_at DESC LIMIT 1"),
                {"id": approval["subject_id"]},
            ).first()
            payment = conn.execute(text("SELECT amount_minor FROM payments WHERE id = :id"), {"id": approval["subject_id"]}).first()
            _allocate(
                conn,
                str(approval["merchant_id"]),
                str(approval["subject_id"]),
                str(suggestion[0]),
                int(payment[0]),
                actor,
                None,
            )
        if approve and approval["kind"] == "refund":
            _submit_refund(conn, approval)
        if not approve and approval["kind"] == "match":
            conn.execute(
                text("UPDATE payments SET match_status = 'unmatched' WHERE id = :id"),
                {"id": approval["subject_id"]},
            )
    return {"id": approval_id, "status": status}


def request_refund(engine: Engine, payment_id: str, amount_minor: int, reason: str) -> dict:
    with engine.begin() as conn:
        payment = conn.execute(text("SELECT * FROM payments WHERE id = :id"), {"id": payment_id}).mappings().first()
        if payment is None:
            raise KeyError(payment_id)
        remaining = int(payment["amount_minor"]) - int(payment["amount_refunded_minor"])
        if amount_minor > remaining or amount_minor <= 0:
            raise ValueError("refund exceeds remaining amount")
        merchant_id = str(payment["merchant_id"])
        approval = conn.execute(
            text(
                """
                INSERT INTO approvals (merchant_id, kind, subject_id, summary)
                VALUES (:m, 'refund', :s, :summary)
                RETURNING id
                """
            ),
            {
                "m": merchant_id,
                "s": payment_id,
                "summary": f"Refund {amount_minor} minor units: {reason}",
            },
        ).first()
        # subject_id on the approval is the payment. The refund row points at the approval.
        # Workaround: approvals.subject_id cannot be the refund id before the refund exists,
        # so it stores the payment id. See CHALLENGES.md.
        refund = conn.execute(
            text(
                """
                INSERT INTO refunds (merchant_id, payment_id, approval_id, amount_minor, reason, status)
                VALUES (:m, :p, :a, :amt, :reason, 'requested')
                RETURNING id
                """
            ),
            {
                "m": merchant_id,
                "p": payment_id,
                "a": approval[0],
                "amt": amount_minor,
                "reason": reason,
            },
        ).first()
        _event(conn, merchant_id, "system", "refund.requested", "refund", str(refund[0]), reason, {})
    return {"refund_id": str(refund[0]), "approval_id": str(approval[0])}


def _submit_refund(conn, approval) -> None:
    refund = conn.execute(
        text("SELECT * FROM refunds WHERE approval_id = :id"),
        {"id": approval["id"]},
    ).mappings().first()
    provider_refund_id = f"dry_re_{uuid.uuid4().hex[:10]}"
    conn.execute(
        text(
            """
            UPDATE refunds
            SET status = 'succeeded', provider_refund_id = :pid
            WHERE id = :id
            """
        ),
        {"pid": provider_refund_id, "id": refund["id"]},
    )
    conn.execute(
        text("UPDATE payments SET amount_refunded_minor = amount_refunded_minor + :amt WHERE id = :id"),
        {"amt": refund["amount_minor"], "id": refund["payment_id"]},
    )
    _event(
        conn,
        str(approval["merchant_id"]),
        "system",
        "refund.succeeded",
        "refund",
        str(refund["id"]),
        "Dry-run HitPay refund succeeded. No live REST call while DRY_RUN is true.",
        {"provider_refund_id": provider_refund_id},
    )


def churn_sweep(engine: Engine, older_than_days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                UPDATE rescues
                SET status = 'churned', churned_at = now()
                WHERE status = 'offered' AND created_at < :cutoff
                RETURNING id, merchant_id
                """
            ),
            {"cutoff": cutoff},
        ).mappings()
        changed = list(rows)
        for row in changed:
            _event(conn, str(row["merchant_id"]), "system", "rescue.churned", "rescue", str(row["id"]), "Unpaid after churn window.", {})
    return {"churned": len(changed)}


def run_forecast(engine: Engine, settings: Settings) -> dict:
    merchant_id = ensure_merchant(engine)
    with engine.begin() as conn:
        merchant = conn.execute(text("SELECT settings FROM merchants WHERE id = :id"), {"id": merchant_id}).mappings().first()
        cfg = merchant["settings"] or {}
        invoices = _open_invoices(conn, merchant_id)
        start = datetime.now(timezone.utc).date()
        receipts = [(inv.due_at.date(), inv.outstanding) for inv in invoices]
        built = build_series(
            opening_balance_minor=int(cfg.get("opening_balance_minor") or 0),
            daily_outflow_minor=int(cfg.get("daily_outflow_minor") or 0),
            receipts=receipts,
            start=start,
            buffer_minor=int(cfg.get("buffer_minor") or 0),
        )
        forecast = conn.execute(
            text(
                """
                INSERT INTO forecasts (merchant_id, series, min_balance_minor, gap_minor, inputs)
                VALUES (:m, CAST(:series AS jsonb), :minb, :gap, CAST(:inputs AS jsonb))
                RETURNING id
                """
            ),
            {
                "m": merchant_id,
                "series": json.dumps(built["series"]),
                "minb": built["min_balance_minor"],
                "gap": built["gap_minor"],
                "inputs": json.dumps({"source": "scaffold"}),
            },
        ).first()
        offer = None
        if built["gap_minor"] > 0 and invoices:
            target = max(invoices, key=lambda inv: inv.outstanding)
            pct = float(cfg.get("discount_max_pct") or 2.0)
            ok, cost, gap_cost = discount_allowed(
                invoice_amount_minor=target.outstanding,
                discount_pct=pct,
                gap_minor=built["gap_minor"],
                daily_financing_rate=float(cfg.get("daily_financing_rate") or 0.0005),
                gap_days=7,
                max_pct=pct,
            )
            if ok:
                offer_row = conn.execute(
                    text(
                        """
                        INSERT INTO discount_offers
                          (merchant_id, forecast_id, invoice_id, discount_pct, discount_cost_minor, gap_cost_minor, status)
                        VALUES (:m, :f, :i, :pct, :cost, :gap_cost, 'proposed')
                        RETURNING id
                        """
                    ),
                    {
                        "m": merchant_id,
                        "f": forecast[0],
                        "i": target.id,
                        "pct": pct,
                        "cost": cost,
                        "gap_cost": gap_cost,
                    },
                ).first()
                conn.execute(
                    text(
                        """
                        INSERT INTO approvals (merchant_id, kind, subject_id, summary)
                        VALUES (:m, 'discount', :s, :summary)
                        """
                    ),
                    {
                        "m": merchant_id,
                        "s": offer_row[0],
                        "summary": f"Offer {pct}% off {target.ref} because discount cost {cost} < gap cost {gap_cost}.",
                    },
                )
                offer = {"invoice_ref": target.ref, "discount_pct": pct, "discount_cost_minor": cost}
        _event(conn, merchant_id, "system", "forecast.built", "forecast", str(forecast[0]), "14-day forecast.", built)
    return {"forecast_id": str(forecast[0]), **built, "offer": offer}


def metrics(engine: Engine) -> dict:
    ensure_merchant(engine)
    with engine.connect() as conn:
        recovery = conn.execute(text("SELECT * FROM v_recovery")).mappings().first()
        risk = conn.execute(text("SELECT * FROM v_at_risk")).mappings().first()
    return {
        "recovered": int(recovery["recovered"] or 0),
        "failures": int(recovery["failures"] or 0),
        "churned": int(recovery["churned"] or 0),
        "recovery_rate": float(recovery["recovery_rate"] or 0),
        "churn_rate": float(recovery["churn_rate"] or 0),
        "at_risk_minor": int(risk["at_risk_minor"] or 0),
    }


def list_events(engine: Engine) -> list[dict]:
    rows = fetch_dicts(
        engine,
        "SELECT occurred_at, actor, type, reason FROM events ORDER BY occurred_at DESC LIMIT 50",
    )
    return rows


def list_queue(engine: Engine) -> list[dict]:
    return fetch_dicts(
        engine,
        """
        SELECT a.id, a.kind, a.summary, a.status, p.amount_minor, p.payer_name
        FROM approvals a
        LEFT JOIN payments p ON p.id = a.subject_id
        WHERE a.status = 'pending'
        ORDER BY a.created_at DESC
        """,
    )


def list_rescues(engine: Engine) -> list[dict]:
    return fetch_dicts(
        engine,
        """
        SELECT id, status, amount_minor, currency, message_draft, created_at
        FROM rescues ORDER BY created_at DESC LIMIT 50
        """,
    )


def fetch_dicts(engine: Engine, sql: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
    result = []
    for row in rows:
        item = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                item[key] = value.isoformat()
            else:
                item[key] = value if not hasattr(value, "hex") else str(value)
            if key.endswith("minor") and value is not None:
                item[key] = int(value)
        result.append(item)
    return result


def mcp_call(engine: Engine, settings: Settings, name: str, arguments: dict) -> dict:
    if name == "get_recovery_summary":
        return metrics(engine)
    if name == "list_open_rescues":
        return {"rescues": [r for r in list_rescues(engine) if r["status"] in {"opened", "offered"}]}
    if name == "list_unmatched_payments":
        return {"queue": list_queue(engine)}
    if name == "get_cash_forecast":
        return run_forecast(engine, settings)
    if name == "ingest_hitpay_snapshot":
        merchant_id = ensure_merchant(engine)
        balance = int(arguments.get("balance_minor") or 0)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE merchants
                    SET settings = settings || CAST(:patch AS jsonb)
                    WHERE id = :id
                    """
                ),
                {"patch": json.dumps({"opening_balance_minor": balance}), "id": merchant_id},
            )
        return {"stored_balance_minor": balance}
    if name == "propose_discount_offer":
        return run_forecast(engine, settings)
    raise KeyError(name)
