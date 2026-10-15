"""Schemas from SPEC §6 and §8. Agents use these as structured output."""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

Unit = Literal["kg", "g", "l", "ml", "pcs", "pack"]
Category = Literal[
    "vegetables", "fruits", "dairy", "staples", "snacks", "beverages", "household", "personal_care", "other"
]
StoreId = Literal["freshmart", "quickbasket", "megabazaar", "kiranaconnect"]


def _uuid() -> str:
    return str(uuid4())


# --- §6.1 ListParserAgent ---------------------------------------------------
class ParsedItem(BaseModel):
    """What the model returns for one line; the API adds id/optional."""

    canonical_name: str
    original_text: str
    quantity: float = 1
    unit: Unit | None = None
    brand_preference: str | None = None
    category: Category = "other"
    notes: str | None = None


class ParsedList(BaseModel):
    """Structured output schema for ListParserAgent."""

    items: list[ParsedItem]
    detected_language: Literal["en", "ta", "hi", "mixed", "other"] = "en"


class ShoppingItem(BaseModel):
    id: str = Field(default_factory=_uuid)
    canonical_name: str
    original_text: str
    quantity: float = 1
    unit: Unit | None = None
    brand_preference: str | None = None
    category: Category = "other"
    notes: str | None = None
    optional: bool = False


class ShoppingList(BaseModel):
    items: list[ShoppingItem]
    detected_language: Literal["en", "ta", "hi", "mixed", "other"] = "en"


SourceType = Literal["text", "image", "audio", "pdf", "docx"]


class Candidate(BaseModel):
    """A catalogue product that can satisfy a list item (SPEC §8.1)."""

    product_id: str
    store_id: StoreId
    name: str
    brand: str
    pack_size: float
    pack_unit: str
    price: float
    qty: int
    line_price: float
    rating: float
    rating_count: int
    in_stock: bool
    brand_match: bool = False


class ListResponse(ShoppingList):
    list_id: str
    source_type: SourceType
    matches: dict[str, list[Candidate]]


# --- §6.2 VoucherExtractorAgent ---------------------------------------------
class Voucher(BaseModel):
    email_id: str
    store_name_raw: str
    store_id: StoreId | None = None
    code: str | None = None
    discount_type: Literal["percent", "flat"]
    value: float
    max_discount: float | None = None
    min_spend: float | None = None
    expiry: str | None = None  # YYYY-MM-DD
    applies_to_category: str | None = None
    confidence: float = 0.0


class VoucherList(BaseModel):
    vouchers: list[Voucher]


# --- §6.3 ExplainerAgent ----------------------------------------------------
class Explanation(BaseModel):
    headline: str = Field(default="", max_length=90)
    bullets: list[str] = Field(default_factory=list, max_length=4)


# --- §8.3 CartPlan ----------------------------------------------------------
class PlanLine(BaseModel):
    item_id: str
    product_id: str
    name: str
    qty: int
    line_price: float


class AppliedVoucher(BaseModel):
    code: str | None
    discount: float


class StorePlan(BaseModel):
    store_id: StoreId
    lines: list[PlanLine]
    subtotal: float
    delivery_fee: float
    voucher: AppliedVoucher | None = None
    total: float
    eta: str


class CartPlan(BaseModel):
    plan_id: str = Field(default_factory=_uuid)
    label: Literal["best", "single_store", "fastest"]
    stores: list[StorePlan]
    grand_total: float
    savings_vs_single_store: float = 0
    unavailable_items: list[str] = Field(default_factory=list)
    explanation: Explanation = Field(default_factory=Explanation)


# --- §6.5 LivePriceScoutAgent -----------------------------------------------
class WebOffer(BaseModel):
    retailer: str
    title: str
    price_inr: float
    url: str
    seen_text: str = ""


class WebOffers(BaseModel):
    offers: list[WebOffer]
