DECLINE_CODES = {
    "insufficient_funds",
    "do_not_honor",
    "generic_decline",
    "expired_card",
    "card_declined",
    "lost_card",
    "stolen_card",
}


def classify_failure(failure_code: str | None, source: str) -> str:
    code = (failure_code or "").lower()
    if source == "poll" or code in {"abandoned", "timeout"}:
        return "abandoned"
    if code in {"expired", "qr_expired"}:
        return "expired"
    if code in DECLINE_CODES or source == "stripe":
        return "declined"
    if code == "failed":
        return "declined"
    return "abandoned"


def draft_message(*, ref: str, amount_label: str, method_label: str, url: str) -> str:
    return (
        f"Your card payment for {ref} ({amount_label}) didn't go through. "
        f"Pay by {method_label} here: {url}"
    )
