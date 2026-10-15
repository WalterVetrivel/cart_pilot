"""Vouchers from Gmail or demo emails (SPEC §6.2, §9, screen 5)."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.voucher_extractor import EmailSnippet, VoucherExtractor, get_voucher_extractor
from app.auth import AuthUser
from app.db import Repository, get_repository
from app.errors import ApiError
from app.models.schemas import ExtractedVoucher, Voucher, VoucherScanResult, VoucherSource
from app.services.gmail import EmailFetcher, GmailAuthError, get_email_fetcher
from app.services.vouchers import screen_vouchers, today

router = APIRouter(tags=["vouchers"])
log = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"

Repo = Annotated[Repository, Depends(get_repository)]
Extractor = Annotated[VoucherExtractor, Depends(get_voucher_extractor)]


class ScanRequest(BaseModel):
    # Short-lived OAuth token with gmail.readonly scope. Used for this request only; never stored or logged.
    gmail_access_token: str = Field(min_length=10, repr=False)


class VouchersResponse(BaseModel):
    vouchers: list[Voucher]


def demo_emails() -> list[EmailSnippet]:
    emails = []
    for path in sorted((SEED_DIR / "demo_emails").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        emails.append(EmailSnippet(sender=raw["from"], **{k: v for k, v in raw.items() if k != "from"}))
    return emails


def _seed_vouchers() -> list[ExtractedVoucher]:
    raw = json.loads((SEED_DIR / "demo_vouchers.json").read_text(encoding="utf-8"))
    return [ExtractedVoucher.model_validate(v) for v in raw]


def _save(uid: str, source: VoucherSource, extracted, emails, extracted_by: str, repo: Repository) -> VoucherScanResult:
    kept, ignored = screen_vouchers(extracted, emails, source, today())
    repo.replace_vouchers(uid, source, [v.model_dump() for v in kept])
    log.info("Vouchers from %s: %d kept, %d ignored, %d emails", source, len(kept), len(ignored), len(emails))
    return VoucherScanResult(
        source=source,
        emails_scanned=len(emails),
        extracted_by=extracted_by,
        vouchers=[Voucher.model_validate(v) for v in repo.vouchers(uid)],
        ignored=ignored,
    )


@router.get("/vouchers", response_model=VouchersResponse)
def list_vouchers(user: AuthUser, repo: Repo) -> VouchersResponse:
    return VouchersResponse(vouchers=[Voucher.model_validate(v) for v in repo.vouchers(user.uid)])


@router.post("/vouchers/demo", response_model=VoucherScanResult)
async def demo_vouchers(user: AuthUser, repo: Repo, extractor: Extractor) -> VoucherScanResult:
    """Run VoucherExtractorAgent on the bundled demo emails; fall back to the seeded vouchers."""
    emails = demo_emails()
    try:
        extracted = (await extractor.extract(emails)).vouchers
        extracted_by = "gemini"
    except Exception as e:
        log.warning("Demo voucher extraction failed, using seeded vouchers: %s", type(e).__name__)
        extracted, extracted_by = _seed_vouchers(), "seed"
    return _save(user.uid, "demo", extracted, emails, extracted_by, repo)


@router.post("/vouchers/scan", response_model=VoucherScanResult)
async def scan_gmail(
    body: ScanRequest,
    user: AuthUser,
    repo: Repo,
    extractor: Extractor,
    fetch: Annotated[EmailFetcher, Depends(get_email_fetcher)],
) -> VoucherScanResult:
    try:
        emails = await asyncio.to_thread(fetch, body.gmail_access_token)
    except GmailAuthError:
        raise ApiError(401, "gmail_auth", "Gmail didn't accept the permission. Connect Gmail again.") from None
    except Exception as e:
        log.warning("Gmail fetch failed: %s", type(e).__name__)
        raise ApiError(502, "gmail_unavailable", "Couldn't reach Gmail. Try again in a moment.") from None

    extracted: list[ExtractedVoucher] = []
    if emails:
        try:
            extracted = (await extractor.extract(emails)).vouchers
        except Exception as e:
            log.warning("Voucher extraction failed: %s", type(e).__name__)
            raise ApiError(502, "extract_failed", "Couldn't read vouchers from your emails. Try again.") from None
    return _save(user.uid, "gmail", extracted, emails, "gemini", repo)
