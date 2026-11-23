import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import text


def scalar(db, sql: str):
    with db.connect() as conn:
        return conn.execute(text(sql)).scalar()

from app.ledger import (
    accept_webhook,
    churn_sweep,
    create_invoice,
    decide_approval,
    list_queue,
    metrics,
    process_jobs,
    request_refund,
)
from app.signatures import hitpay_signature, stripe_signature


def _invoice(db, settings, ref="INV-104", amount=42000, currency="SGD", name="Tan Wei"):
    return create_invoice(
        db,
        settings,
        customer_name=name,
        email="tan@example.com",
        ref=ref,
        amount_minor=amount,
        currency=currency,
        due_at=datetime.now(timezone.utc) + timedelta(days=7),
    )


def test_exact_reference_marks_invoice_paid(db, settings):
    created = _invoice(db, settings)
    body = json.dumps(
        {
            "id": "pay_1",
            "status": "completed",
            "amount": "420.00",
            "currency": "SGD",
            "reference_number": "INV-104",
            "payment_method": "paynow_online",
            "payer_name": "Tan Wei",
        }
    ).encode()
    status, _ = accept_webhook(db, settings, "hitpay", body, hitpay_signature(body, "salt"))
    assert status == 200
    assert process_jobs(db, settings) == 2
    row = scalar(db, "SELECT status FROM invoices WHERE ref = 'INV-104'")
    assert row == "paid"
    assert created["url"].startswith("https://sandbox.hit-pay.com/pay/")


def test_duplicate_and_bad_signature(db, settings):
    body = b'{"id":"evt_dup","status":"completed","amount":"1.00","currency":"SGD","reference_number":"MISSING"}'
    sig = hitpay_signature(body, "salt")
    assert accept_webhook(db, settings, "hitpay", body, sig)[0] == 200
    assert accept_webhook(db, settings, "hitpay", body, sig) == (200, "duplicate")
    other = b'{"id":"evt_bad","status":"completed"}'
    assert accept_webhook(db, settings, "hitpay", other, "deadbeef")[0] == 401


def test_unreferenced_payment_goes_to_queue(db, settings):
    _invoice(db, settings)
    body = json.dumps(
        {
            "id": "pay_stray",
            "status": "completed",
            "amount": "320.00",
            "currency": "SGD",
            "reference_number": "",
            "payer_name": "S$320 TAN",
        }
    ).encode()
    accept_webhook(db, settings, "hitpay", body, hitpay_signature(body, "salt"))
    process_jobs(db, settings)
    queue = list_queue(db)
    assert queue and queue[0]["kind"] == "match"
    decide_approval(db, queue[0]["id"], True, "Mei", "amount and name")
    status = scalar(db, "SELECT status FROM invoices WHERE ref = 'INV-104'")
    assert status == "partially_paid"


def test_unsigned_hitpay_webhook_does_not_mark_paid(db, settings):
    """A completed PayNow page is not a paid invoice until the signature matches."""
    _invoice(db, settings)
    body = json.dumps(
        {
            "id": "a34baeee-9dba-4b81-878d-85c719394793",
            "status": "completed",
            "amount": "420.00",
            "currency": "SGD",
            "reference_number": "INV-104",
            "payment_method": "paynow_online",
        }
    ).encode()
    assert accept_webhook(db, settings, "hitpay", body, "not-the-endpoint-salt")[0] == 401
    assert scalar(db, "SELECT status FROM invoices WHERE ref = 'INV-104'") == "issued"
    assert scalar(db, "SELECT count(*) FROM payments") == 0


def test_stripe_decline_card_creates_paynow_rescue(db, settings):
    """Card 4000000000000002 is a generic decline. metadata.reference ties it to the invoice."""
    _invoice(db, settings)
    body = json.dumps(
        {
            "id": "evt_fail",
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_fail",
                    "amount": 42000,
                    "currency": "sgd",
                    "last_payment_error": {"decline_code": "insufficient_funds"},
                    "metadata": {"reference": "INV-104"},
                }
            },
        }
    ).encode()
    header = stripe_signature(body, "whsec_test", 1_700_000_000)
    assert accept_webhook(db, settings, "stripe", body, header)[0] == 200
    process_jobs(db, settings)
    with db.connect() as conn:
        rescue = conn.execute(text("SELECT status, message_draft FROM rescues")).mappings().first()
    assert rescue["status"] == "offered"
    assert "PayNow" in rescue["message_draft"]
    pay = json.dumps(
        {
            "id": "pay_rescue",
            "status": "completed",
            "amount": "420.00",
            "currency": "SGD",
            "reference_number": "INV-104",
        }
    ).encode()
    accept_webhook(db, settings, "hitpay", pay, hitpay_signature(pay, "salt"))
    process_jobs(db, settings)
    assert scalar(db, "SELECT status FROM rescues") == "recovered"
    assert metrics(db)["recovered"] == 1


def test_partial_overpay_and_churn(db, settings):
    _invoice(db, settings, amount=10000)
    partial = json.dumps(
        {"id": "part", "status": "completed", "amount": "40.00", "currency": "SGD", "reference_number": "INV-104"}
    ).encode()
    accept_webhook(db, settings, "hitpay", partial, hitpay_signature(partial, "salt"))
    process_jobs(db, settings)
    assert scalar(db, "SELECT status FROM invoices") == "partially_paid"
    over = json.dumps(
        {"id": "over", "status": "completed", "amount": "80.00", "currency": "SGD", "reference_number": "INV-104"}
    ).encode()
    accept_webhook(db, settings, "hitpay", over, hitpay_signature(over, "salt"))
    process_jobs(db, settings)
    assert scalar(db, "SELECT status FROM invoices") == "paid"
    note = scalar(db, "SELECT count(*) FROM events WHERE type = 'payment.overpaid'")
    assert note == 1
    assert churn_sweep(db, 7)["churned"] == 0


def test_refund_requires_approval_and_rejects_over_refund(db, settings):
    _invoice(db, settings, amount=5000)
    body = json.dumps(
        {"id": "paid", "status": "completed", "amount": "50.00", "currency": "SGD", "reference_number": "INV-104"}
    ).encode()
    accept_webhook(db, settings, "hitpay", body, hitpay_signature(body, "salt"))
    process_jobs(db, settings)
    payment_id = scalar(db, "SELECT id FROM payments")
    refund = request_refund(db, str(payment_id), 2000, "goodwill")
    with pytest_raises(ValueError):
        request_refund(db, str(payment_id), 999999, "too much")
    decide_approval(db, refund["approval_id"], True, "Mei", "ok")
    with db.connect() as conn:
        status = conn.execute(text("SELECT status, amount_minor FROM refunds")).mappings().first()
    assert status["status"] == "succeeded"
    refunded = scalar(db, "SELECT amount_refunded_minor FROM payments")
    assert int(refunded) == 2000


def pytest_raises(exc):
    import pytest

    return pytest.raises(exc)
