"""POST /parse and list read/update (SPEC §9, screens 2-3)."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.agents.list_parser import ListParser, get_list_parser
from app.auth import AuthUser
from app.config import Settings, get_settings
from app.db import Repository, get_repository
from app.errors import ApiError
from app.models.schemas import ListResponse, ShoppingItem, ShoppingList, SourceType
from app.services.docx_text import docx_to_text
from app.services.matching import match_list

router = APIRouter(tags=["lists"])
log = logging.getLogger(__name__)

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Upload MIME type -> (source type, MIME type sent to Gemini)
ACCEPTED: dict[str, tuple[SourceType, str]] = {
    "image/jpeg": ("image", "image/jpeg"),
    "image/png": ("image", "image/png"),
    "image/webp": ("image", "image/webp"),
    "audio/webm": ("audio", "audio/webm"),
    "video/webm": ("audio", "audio/webm"),  # some browsers label audio-only recordings as video/webm
    "audio/ogg": ("audio", "audio/ogg"),
    "audio/mpeg": ("audio", "audio/mp3"),
    "audio/mp3": ("audio", "audio/mp3"),
    "audio/wav": ("audio", "audio/wav"),
    "audio/x-wav": ("audio", "audio/wav"),
    "audio/wave": ("audio", "audio/wav"),
    "audio/mp4": ("audio", "audio/mp4"),
    "audio/x-m4a": ("audio", "audio/mp4"),
    "audio/m4a": ("audio", "audio/mp4"),
    "application/pdf": ("pdf", "application/pdf"),
    DOCX: ("docx", DOCX),
}
_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".pdf": "application/pdf",
    ".docx": DOCX,
}

Repo = Annotated[Repository, Depends(get_repository)]


def _content_type(upload: UploadFile) -> str:
    ctype = (upload.content_type or "").split(";")[0].strip().lower()
    if ctype in ACCEPTED:
        return ctype
    name = (upload.filename or "").lower()
    for ext, guessed in _BY_EXTENSION.items():
        if name.endswith(ext):
            return guessed
    raise ApiError(415, "unsupported_file", "Use an image, audio, PDF or DOCX file.")


def _response(list_id: str, source_type: SourceType, shopping: ShoppingList, repo: Repository) -> ListResponse:
    return ListResponse(
        list_id=list_id,
        source_type=source_type,
        items=shopping.items,
        detected_language=shopping.detected_language,
        matches=match_list(shopping.items, repo.products()),
    )


@router.post("/parse", response_model=ListResponse)
async def parse_list(
    user: AuthUser,
    repo: Repo,
    settings: Annotated[Settings, Depends(get_settings)],
    parser: Annotated[ListParser, Depends(get_list_parser)],
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    list_id: Annotated[str | None, Form()] = None,
) -> ListResponse:
    """Reads a list. With `list_id`, the new items are appended to that list."""
    existing = None
    if list_id:
        existing = repo.get_list(user.uid, list_id)
        if existing is None:
            raise ApiError(404, "list_not_found", "That list doesn't exist.")
    text = (text or "").strip() or None
    if file is None and text is None:
        raise ApiError(422, "empty_list", "Type a list or attach a file.")

    blob: bytes | None = None
    mime: str | None = None
    source: SourceType = "text"
    if file is not None:
        ctype = _content_type(file)
        source, mime = ACCEPTED[ctype]
        blob = await file.read()
        if len(blob) > settings.max_upload_mb * 1024 * 1024:
            raise ApiError(413, "file_too_large", f"Files must be {settings.max_upload_mb} MB or smaller.")
        if not blob:
            raise ApiError(422, "empty_file", "The file is empty.")
        if source == "docx":
            try:
                docx_text = docx_to_text(blob)
            except Exception as exc:
                raise ApiError(422, "bad_docx", "Could not read that Word file.") from exc
            text = "\n".join(t for t in (text, docx_text) if t)
            blob, mime = None, None

    try:
        parsed = await parser.parse(text, blob, mime)
    except ApiError:
        raise
    except Exception as exc:
        log.exception("List parsing failed (source=%s)", source)
        message = "Couldn't read that list. Please try again."
        if settings.auth_disabled:  # local dev: show the cause in the UI
            message += f" ({type(exc).__name__}: {str(exc)[:300]})"
        raise ApiError(502, "parse_failed", message) from exc

    new_items = [ShoppingItem(**i.model_dump()) for i in parsed.items]
    if existing is not None:
        previous = ShoppingList.model_validate(existing)
        source = existing["source_type"]
        shopping = ShoppingList(items=[*previous.items, *new_items], detected_language=previous.detected_language)
    else:
        list_id = str(uuid.uuid4())
        shopping = ShoppingList(items=new_items, detected_language=parsed.detected_language)
    repo.save_list(user.uid, list_id, {"source_type": source, **shopping.model_dump()})
    log.info("Parsed list %s: +%d items from %s", list_id, len(new_items), source)
    return _response(list_id, source, shopping, repo)


@router.get("/lists/{list_id}", response_model=ListResponse)
def get_list(list_id: str, user: AuthUser, repo: Repo) -> ListResponse:
    stored = repo.get_list(user.uid, list_id)
    if stored is None:
        raise ApiError(404, "list_not_found", "That list doesn't exist.")
    return _response(list_id, stored["source_type"], ShoppingList.model_validate(stored), repo)


@router.put("/lists/{list_id}", response_model=ListResponse)
def update_list(list_id: str, body: ShoppingList, user: AuthUser, repo: Repo) -> ListResponse:
    """Saves the user's edits from the "Check the list" screen."""
    stored = repo.get_list(user.uid, list_id)
    if stored is None:
        raise ApiError(404, "list_not_found", "That list doesn't exist.")
    repo.save_list(user.uid, list_id, {"source_type": stored["source_type"], **body.model_dump()})
    return _response(list_id, stored["source_type"], body, repo)
