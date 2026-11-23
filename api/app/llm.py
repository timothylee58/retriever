"""Grok (xAI) structured suggestion. Any failure falls back to rules-v1."""

import json

import httpx

from app.config import Settings
from app.domain.matcher import MatchDecision, OpenInvoice


def rules_suggestion(amount_minor: int, payer_name: str | None, invoices: list[OpenInvoice]) -> MatchDecision:
    if not invoices:
        return MatchDecision(3, None, 0.0, "No open invoice is close enough.", False, "rules-v1")
    best = min(invoices, key=lambda inv: abs(inv.outstanding - amount_minor))
    gap = abs(best.outstanding - amount_minor)
    confidence = 0.82 if gap == 0 else max(0.4, 0.8 - gap / max(best.outstanding, 1))
    confidence = min(confidence, 0.89)
    who = payer_name or "unknown payer"
    return MatchDecision(
        3,
        best.id,
        round(confidence, 2),
        f"Closest open invoice {best.ref} for {who} (amount gap {gap}).",
        False,
        "rules-v1",
    )


def suggest_match(
    settings: Settings,
    *,
    amount_minor: int,
    currency: str,
    payer_name: str | None,
    invoices: list[OpenInvoice],
) -> MatchDecision:
    fallback = rules_suggestion(amount_minor, payer_name, invoices)
    if not settings.xai_api_key or not invoices:
        return fallback
    catalog = [
        {
            "invoice_id": inv.id,
            "ref": inv.ref,
            "outstanding_minor": inv.outstanding,
            "currency": inv.currency,
            "name": inv.customer_name,
        }
        for inv in invoices[:5]
    ]
    prompt = {
        "payment": {"amount_minor": amount_minor, "currency": currency, "payer_name": payer_name},
        "candidates": catalog,
        "reply_schema": {"invoice_id": "uuid or null", "confidence": "0-1", "reason": "plain English"},
    }
    try:
        response = httpx.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.xai_api_key}"},
            json={
                "model": settings.llm_model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "Reply with JSON only. Do not invent an invoice id that is not in candidates.",
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        invoice_id = parsed.get("invoice_id")
        allowed = {inv.id for inv in invoices}
        if invoice_id not in allowed:
            return fallback
        confidence = float(parsed.get("confidence") or 0)
        return MatchDecision(
            3,
            invoice_id,
            max(0.0, min(confidence, 0.99)),
            str(parsed.get("reason") or fallback.reason),
            False,
            settings.llm_model,
        )
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return fallback
