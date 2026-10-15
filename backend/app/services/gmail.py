"""Read recent offer emails from Gmail with a short-lived, read-only access token (SPEC §9).

The token is used for this request only. It is never stored or logged, and neither are email
bodies: they are passed straight to VoucherExtractorAgent and dropped.
"""

import base64
import html
import re
from collections.abc import Callable

from app.agents.voucher_extractor import BODY_LIMIT, EmailSnippet

QUERY = 'newer_than:60d (coupon OR voucher OR "promo code" OR "% off" OR cashback OR offer)'
MAX_MESSAGES = 50


class GmailAuthError(Exception):
    """The access token was rejected (expired, revoked, or missing the gmail.readonly scope)."""


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def strip_html(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", markup)
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def body_text(payload: dict) -> str:
    """Plain-text body of a Gmail message payload; falls back to stripped HTML."""
    plain: list[str] = []
    markup: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            markup.append(_decode(data))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    text = "\n".join(plain).strip() or strip_html("\n".join(markup))
    return text[:BODY_LIMIT]


def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def fetch_offer_emails(access_token: str) -> list[EmailSnippet]:
    """Blocking: call from a worker thread."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    service = build("gmail", "v1", credentials=Credentials(token=access_token), cache_discovery=False)
    try:
        listing = service.users().messages().list(userId="me", q=QUERY, maxResults=MAX_MESSAGES).execute()
        snippets = []
        for ref in listing.get("messages", [])[:MAX_MESSAGES]:
            msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            payload = msg.get("payload", {})
            snippets.append(
                EmailSnippet(
                    email_id=msg["id"],
                    sender=_header(payload, "from"),
                    date=_header(payload, "date"),
                    subject=_header(payload, "subject"),
                    body=body_text(payload),
                )
            )
        return snippets
    except HttpError as e:
        if e.resp.status in (401, 403):
            raise GmailAuthError from None
        raise


EmailFetcher = Callable[[str], list[EmailSnippet]]


def get_email_fetcher() -> EmailFetcher:
    return fetch_offer_emails
