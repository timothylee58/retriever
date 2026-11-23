import hashlib
import hmac


def hitpay_signature(raw_body: bytes, salt: str) -> str:
    """Assumed scheme: hex HMAC-SHA256 over the raw body.

    HitPay's hash algorithm was still marked unverified in the spec (Q1).
    """
    return hmac.new(salt.encode(), raw_body, hashlib.sha256).hexdigest()


def hitpay_valid(raw_body: bytes, header: str | None, salt: str) -> bool:
    if not header or not salt:
        return False
    expected = hitpay_signature(raw_body, salt)
    return hmac.compare_digest(expected, header.strip())


def stripe_signature(raw_body: bytes, secret: str, timestamp: int) -> str:
    signed = f"{timestamp}.".encode() + raw_body
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def stripe_valid(raw_body: bytes, header: str | None, secret: str) -> bool:
    if not header or not secret:
        return False
    parts = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
    timestamp = parts.get("t")
    given = parts.get("v1")
    if not timestamp or not given:
        return False
    signed = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, given)
