"""Deterministic matcher. Tier 3 never auto-applies (demo rule)."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class OpenInvoice:
    id: str
    ref: str
    amount_minor: int
    amount_paid_minor: int
    currency: str
    due_at: datetime
    customer_name: str
    aliases: list[str]

    @property
    def outstanding(self) -> int:
        return self.amount_minor - self.amount_paid_minor


@dataclass
class MatchDecision:
    tier: int
    invoice_id: str | None
    confidence: float
    reason: str
    auto: bool
    model: str = "rules-v1"


def tier1(reference: str | None, currency: str, invoices: list[OpenInvoice]) -> MatchDecision | None:
    if not reference:
        return None
    for inv in invoices:
        if inv.ref == reference and inv.currency == currency and inv.outstanding > 0:
            return MatchDecision(1, inv.id, 1.0, f"Exact reference {reference}.", True)
        if inv.ref == reference and inv.currency != currency:
            return MatchDecision(
                1, None, 0.0, f"Reference {reference} currency {currency} does not match {inv.currency}.", False
            )
    return None


def tier2(
    *,
    amount_minor: int,
    currency: str,
    payer_name: str | None,
    received_at: datetime,
    invoices: list[OpenInvoice],
) -> MatchDecision | None:
    if not payer_name:
        return None
    name = payer_name.strip().lower()
    hits = []
    for inv in invoices:
        if inv.currency != currency or inv.outstanding != amount_minor:
            continue
        names = [inv.customer_name.lower(), *[a.lower() for a in inv.aliases]]
        if name not in names:
            continue
        if abs(inv.due_at - received_at) > timedelta(days=30):
            continue
        hits.append(inv)
    if len(hits) == 1:
        inv = hits[0]
        return MatchDecision(
            2,
            inv.id,
            0.95,
            f"Same amount, payer name, and due date within 30 days ({inv.ref}).",
            True,
        )
    return None
