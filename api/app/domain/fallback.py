"""Method-aware rescue fallback. Never offer the method that just failed."""

MY_B2B_THRESHOLD_MINOR = 500_000  # RM 5,000.00

SG_DEFAULT = ["paynow", "grabpay", "shopeepay"]
MY_DEFAULT = ["duitnow", "tng", "boost", "grabpay", "fpx"]


def choose_fallback(
    *,
    country: str,
    failed_method: str,
    last_success_method: str | None,
    enabled_methods: list[str],
    amount_minor: int,
    b2b: bool = False,
) -> list[str]:
    enabled = [m for m in enabled_methods if m != failed_method and m != "card"]
    ordered: list[str] = []
    if last_success_method and last_success_method in enabled:
        ordered.append(last_success_method)
    country = country.upper()
    if country == "MY" and b2b and amount_minor >= MY_B2B_THRESHOLD_MINOR and "fpx" in enabled:
        ordered.append("fpx")
    defaults = SG_DEFAULT if country == "SG" else MY_DEFAULT
    for method in defaults:
        if method in enabled and method not in ordered:
            ordered.append(method)
    for method in enabled:
        if method not in ordered:
            ordered.append(method)
    if not ordered:
        raise ValueError(f"no fallback method for country={country} failed={failed_method}")
    return ordered
