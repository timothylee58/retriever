from datetime import datetime, timedelta, timezone

from app.domain.fallback import choose_fallback
from app.domain.forecast import build_series, discount_allowed
from app.domain.matcher import OpenInvoice, tier1, tier2
from app.domain.rescue import classify_failure
from app.signatures import hitpay_signature, hitpay_valid, stripe_signature, stripe_valid


def invoice(**kwargs):
    base = dict(
        id="inv",
        ref="INV-104",
        amount_minor=42000,
        amount_paid_minor=0,
        currency="SGD",
        due_at=datetime.now(timezone.utc),
        customer_name="Tan",
        aliases=["TAN WEI"],
    )
    base.update(kwargs)
    return OpenInvoice(**base)


def test_tier1_exact_and_currency_guard():
    hit = tier1("INV-104", "SGD", [invoice()])
    assert hit.auto and hit.tier == 1
    blocked = tier1("INV-104", "MYR", [invoice()])
    assert blocked.invoice_id is None


def test_tier2_single_candidate_only():
    now = datetime.now(timezone.utc)
    one = tier2(amount_minor=42000, currency="SGD", payer_name="tan", received_at=now, invoices=[invoice(due_at=now)])
    assert one.confidence == 0.95
    two = tier2(
        amount_minor=42000,
        currency="SGD",
        payer_name="tan",
        received_at=now,
        invoices=[invoice(due_at=now), invoice(id="b", ref="INV-105", due_at=now)],
    )
    assert two is None
    stale = tier2(
        amount_minor=42000,
        currency="SGD",
        payer_name="tan",
        received_at=now,
        invoices=[invoice(due_at=now - timedelta(days=40))],
    )
    assert stale is None


def test_fallback_never_retries_failed_method():
    sg = choose_fallback(
        country="SG",
        failed_method="card",
        last_success_method="grabpay",
        enabled_methods=["paynow", "card", "grabpay"],
        amount_minor=1000,
    )
    assert sg[0] == "grabpay"
    assert "card" not in sg
    my = choose_fallback(
        country="MY",
        failed_method="card",
        last_success_method=None,
        enabled_methods=["duitnow", "fpx", "tng"],
        amount_minor=600_000,
        b2b=True,
    )
    assert my[0] == "fpx"


def test_failure_classes_and_discount_rule():
    assert classify_failure("insufficient_funds", "stripe") == "declined"
    assert classify_failure("expired", "hitpay") == "expired"
    assert classify_failure("timeout", "poll") == "abandoned"
    ok, cost, gap_cost = discount_allowed(
        invoice_amount_minor=100_00,
        discount_pct=2,
        gap_minor=50_000,
        daily_financing_rate=0.01,
        gap_days=7,
        max_pct=2,
    )
    assert ok and cost < gap_cost
    blocked, _, _ = discount_allowed(
        invoice_amount_minor=100_00,
        discount_pct=2,
        gap_minor=10,
        daily_financing_rate=0.0001,
        gap_days=1,
        max_pct=2,
    )
    assert not blocked
    series = build_series(
        opening_balance_minor=0,
        daily_outflow_minor=100,
        receipts=[],
        start=datetime.now(timezone.utc).date(),
        horizon_days=3,
        buffer_minor=50,
    )
    assert series["gap_minor"] > 0


def test_signatures_are_constant_time_compares():
    body = b'{"id":"evt_1"}'
    good = hitpay_signature(body, "salt")
    assert hitpay_valid(body, good, "salt")
    assert not hitpay_valid(body, "nope", "salt")
    header = stripe_signature(body, "whsec_test", 1_700_000_000)
    assert stripe_valid(body, header, "whsec_test")
    assert not stripe_valid(body, header, "other")
