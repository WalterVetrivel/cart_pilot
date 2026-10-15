"""Check VoucherExtractorAgent output before it is saved (SPEC §6.2).

The model's output is never trusted on its own: each voucher must come from an email in the batch,
quote a code that appears in that email, carry a plausible discount, and still be valid today.
"""

import hashlib
import re
from datetime import date, datetime, timedelta, timezone

from app.agents.voucher_extractor import EmailSnippet
from app.models.schemas import ExtractedVoucher, IgnoredVoucher, Voucher, VoucherSource

MIN_CONFIDENCE = 0.6
IST = timezone(timedelta(hours=5, minutes=30), "IST")  # no DST in India
MAX_PERCENT = 90
MAX_FLAT_INR = 2000


def today() -> date:
    """Voucher expiry dates are Indian calendar dates."""
    return datetime.now(IST).date()


def voucher_id(source: str, v: ExtractedVoucher) -> str:
    key = f"{source}:{v.email_id}:{v.code or ''}:{v.store_name_raw}:{v.discount_type}:{v.value}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def _why_rejected(v: ExtractedVoucher, emails: dict[str, EmailSnippet], today: date) -> str | None:
    email = emails.get(v.email_id)
    if email is None:
        return "not from a scanned email"
    if v.confidence < MIN_CONFIDENCE:
        return "not clearly a grocery voucher"
    if v.code and _normalise(v.code) not in _normalise(f"{email.subject} {email.body}"):
        return "code doesn't appear in the email"
    limit = MAX_PERCENT if v.discount_type == "percent" else MAX_FLAT_INR
    if not 0 < v.value <= limit:
        return "discount looks implausible"
    if v.expiry:
        try:
            expiry = date.fromisoformat(v.expiry)
        except ValueError:
            return "expiry date unreadable"
        if expiry < today:
            return f"expired on {expiry:%d %b %Y}"
    return None


def screen_vouchers(
    extracted: list[ExtractedVoucher], emails: list[EmailSnippet], source: VoucherSource, today: date
) -> tuple[list[Voucher], list[IgnoredVoucher]]:
    by_id = {e.email_id: e for e in emails}
    kept: dict[tuple, Voucher] = {}
    ignored: list[IgnoredVoucher] = []
    for v in extracted:
        reason = _why_rejected(v, by_id, today)
        if reason:
            ignored.append(IgnoredVoucher(store_name_raw=v.store_name_raw, code=v.code, reason=reason))
            continue
        clean = v.model_copy(
            update={
                "max_discount": v.max_discount if v.max_discount and v.max_discount > 0 else None,
                "min_spend": v.min_spend if v.min_spend and v.min_spend > 0 else None,
            }
        )
        voucher = Voucher(**clean.model_dump(), id=voucher_id(source, v), source=source)
        key = (v.store_id or v.store_name_raw.lower(), (v.code or "").upper(), v.discount_type, v.value)
        if key not in kept or voucher.confidence > kept[key].confidence:
            kept[key] = voucher
    return list(kept.values()), ignored
