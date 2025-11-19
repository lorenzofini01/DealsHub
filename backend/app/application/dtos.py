"""
Application Layer - DTOs (Data Transfer Objects)
Oggetti per comunicazione tra layer e con API esterna
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ============= INPUT DTOs =============

class IngestOfferDTO(BaseModel):
    """Input per ingestione nuova offerta dal collector"""
    source: str = Field(..., description="Sorgente (telegram, api, manual)")
    chat_id: str
    message_id: int
    text: str
    url: HttpUrl


class SearchOffersDTO(BaseModel):
    """Input per ricerca offerte"""
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    category: Optional[str] = None
    search: Optional[str] = None
    min_score: Optional[int] = Field(None, ge=0, le=100)
    sort_by: str = Field("created_at", regex="^(created_at|deal_score|price|discount)$")
    sort_order: str = Field("desc", regex="^(asc|desc)$")


class TrackEventDTO(BaseModel):
    """Input per tracking eventi utente"""
    user_id: str
    offer_id: int
    event_type: str = Field(..., regex="^(view|click|save|unsave)$")
    timestamp: datetime = Field(default_factory=datetime.now)


class SetPriceAlertDTO(BaseModel):
    """Input per creare price alert"""
    user_id: str
    asin: str
    target_price: Decimal = Field(..., gt=0)


# ============= OUTPUT DTOs =============

class OfferDTO(BaseModel):
    """Output per offerta singola"""
    id: int
    title: Optional[str]
    product_url: str
    image_url: Optional[str]

    price: Optional[Decimal]
    original_price: Optional[Decimal]
    discount_percentage: int
    currency: str

    shop: Optional[str]
    category: Optional[str]
    status: str

    deal_score: int
    deal_quality: str  # LEGENDARY, EXCELLENT, etc.
    view_count: int
    click_count: int
    ctr: float

    is_hot: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfferListDTO(BaseModel):
    """Output per lista offerte con metadata"""
    total: int
    limit: int
    offset: int
    offers: list[OfferDTO]


class CategoryStatsDTO(BaseModel):
    """Statistiche per categoria"""
    category: str
    total_offers: int
    avg_discount: float
    avg_deal_score: float


class DashboardStatsDTO(BaseModel):
    """Statistiche globali dashboard"""
    total_offers: int
    active_offers: int
    expired_offers: int
    avg_deal_score: float
    top_categories: list[CategoryStatsDTO]
    hot_deals_count: int


class UserProfileDTO(BaseModel):
    """Profilo utente con preferenze"""
    user_id: str
    preferred_categories: list[str]
    saved_offers_count: int
    active_alerts: int
