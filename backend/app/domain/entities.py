"""
Domain Layer - Entities (Business Logic Pura)
Zero dipendenze da framework esterni. Questo è il cuore del sistema.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum


class OfferStatus(str, Enum):
    """Status lifecycle di un'offerta"""
    VERIFYING = "verifying"  # In fase di scraping
    ACTIVE = "active"        # Verificata e attiva
    EXPIRED = "expired"      # Non più disponibile
    REJECTED = "rejected"    # Scartata (spam, duplicato, ecc.)


class DealQuality(str, Enum):
    """Qualità percepita dell'offerta"""
    LEGENDARY = "legendary"  # >80% sconto o deal eccezionale
    EXCELLENT = "excellent"  # 50-80%
    GOOD = "good"            # 30-50%
    AVERAGE = "average"      # 10-30%
    POOR = "poor"            # <10%


@dataclass
class Offer:
    """
    Entity principale: rappresenta un'offerta.
    Rich Domain Model: contiene comportamenti, non solo dati.
    """
    id: Optional[int] = None
    product_url: str = ""
    title: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[str] = None

    # Pricing
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_percentage: int = 0
    currency: str = "EUR"

    # Metadata
    shop: Optional[str] = None
    category: Optional[str] = None
    status: OfferStatus = OfferStatus.VERIFYING

    # Analytics (NUOVO)
    deal_score: int = 0  # 0-100: qualità dell'offerta (calcolato da ML)
    view_count: int = 0
    click_count: int = 0
    save_count: int = 0  # Quante persone l'hanno salvata

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    verified_at: Optional[datetime] = None

    # ASIN/SKU per deduplicazione
    asin: Optional[str] = None

    def __post_init__(self):
        """Validazione e calcoli automatici"""
        if self.price and self.original_price:
            self.discount_percentage = self._calculate_discount()

    def _calculate_discount(self) -> int:
        """Calcola lo sconto percentuale"""
        if not self.price or not self.original_price or self.original_price <= self.price:
            return 0
        return int(((self.original_price - self.price) / self.original_price) * 100)

    def calculate_deal_score(self,
                           price_history_avg: Optional[Decimal] = None,
                           sentiment_score: float = 0.5,
                           category_popularity: float = 0.5) -> int:
        """
        Calcola Deal Score 0-100 basato su:
        - Sconto percentuale (40%)
        - Confronto con storico prezzi (30%)
        - Sentiment del messaggio Telegram (15%)
        - Popolarità categoria (15%)
        """
        score = 0

        # 1. Discount Score (0-40 punti)
        discount_score = min(self.discount_percentage * 0.4, 40)
        score += discount_score

        # 2. Price History Score (0-30 punti)
        if price_history_avg and self.price:
            price_diff_pct = ((price_history_avg - self.price) / price_history_avg) * 100
            price_score = min(max(price_diff_pct * 0.6, 0), 30)
            score += price_score

        # 3. Sentiment Score (0-15 punti)
        score += sentiment_score * 15

        # 4. Category Popularity (0-15 punti)
        score += category_popularity * 15

        return int(min(score, 100))

    def get_quality(self) -> DealQuality:
        """Converte deal_score in enum qualitativo"""
        if self.deal_score >= 80:
            return DealQuality.LEGENDARY
        elif self.deal_score >= 60:
            return DealQuality.EXCELLENT
        elif self.deal_score >= 40:
            return DealQuality.GOOD
        elif self.deal_score >= 20:
            return DealQuality.AVERAGE
        else:
            return DealQuality.POOR

    def mark_as_verified(self) -> None:
        """Marca come verificata"""
        self.status = OfferStatus.ACTIVE
        self.verified_at = datetime.now()

    def mark_as_expired(self) -> None:
        """Marca come scaduta"""
        self.status = OfferStatus.EXPIRED
        self.updated_at = datetime.now()

    def increment_view(self) -> None:
        """Incrementa visualizzazioni"""
        self.view_count += 1

    def increment_click(self) -> None:
        """Incrementa click (CTR tracking)"""
        self.click_count += 1

    def get_ctr(self) -> float:
        """Click-through rate"""
        if self.view_count == 0:
            return 0.0
        return (self.click_count / self.view_count) * 100

    def is_hot_deal(self) -> bool:
        """Un deal è "hot" se ha alto engagement o alto sconto"""
        return (self.deal_score >= 70 or
                self.get_ctr() > 5.0 or
                self.save_count > 10)


@dataclass
class UserPreference:
    """
    Entity per le preferenze utente (NUOVO)
    Permette personalizzazione e recommendation engine
    """
    id: Optional[int] = None
    user_id: str = ""  # Potrebbe essere un cookie hash o user_id vero se hai auth

    # Categorie preferite (learned via click tracking)
    preferred_categories: list[str] = field(default_factory=list)

    # Soglie prezzo per categoria
    max_price_by_category: dict[str, Decimal] = field(default_factory=dict)

    # Prodotti salvati (watchlist)
    saved_offer_ids: list[int] = field(default_factory=list)

    # Price alert thresholds
    price_alerts: dict[str, Decimal] = field(default_factory=dict)  # {asin: target_price}

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PriceHistory:
    """
    Entity per storico prezzi (NUOVO)
    Permette di calcolare se un'offerta è veramente buona
    """
    id: Optional[int] = None
    asin: str = ""
    price: Decimal = Decimal(0)
    recorded_at: datetime = field(default_factory=datetime.now)
    source: str = "scraper"  # scraper, manual, api, etc.
