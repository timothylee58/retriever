"""EarlyBird: explainable 14-day cash arithmetic. No ML."""

from datetime import date, timedelta


def build_series(
    *,
    opening_balance_minor: int,
    daily_outflow_minor: int,
    receipts: list[tuple[date, int]],
    start: date,
    horizon_days: int = 14,
    buffer_minor: int = 0,
) -> dict:
    by_day: dict[date, int] = {}
    for day, amount in receipts:
        by_day[day] = by_day.get(day, 0) + amount
    balance = opening_balance_minor
    series = []
    min_balance = balance
    for offset in range(horizon_days):
        day = start + timedelta(days=offset)
        balance = balance + by_day.get(day, 0) - daily_outflow_minor
        min_balance = min(min_balance, balance)
        series.append({"date": day.isoformat(), "balance_minor": balance})
    gap = max(0, buffer_minor - min_balance)
    return {"series": series, "min_balance_minor": min_balance, "gap_minor": gap}


def discount_allowed(
    *,
    invoice_amount_minor: int,
    discount_pct: float,
    gap_minor: int,
    daily_financing_rate: float,
    gap_days: int,
    max_pct: float,
) -> tuple[bool, int, int]:
    """gap_cost is the financing cost avoided if the gap is closed for gap_days."""
    discount_cost = int(invoice_amount_minor * discount_pct / 100)
    gap_cost = int(gap_minor * daily_financing_rate * gap_days)
    ok = gap_minor > 0 and discount_cost < gap_cost and discount_pct <= max_pct
    return ok, discount_cost, gap_cost
