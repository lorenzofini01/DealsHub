"""
Domain Layer - Value Objects
Oggetti immutabili che rappresentano concetti del dominio
"""
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass(frozen=True)
class Price:
    """Value Object per rappresentare un prezzo in modo type-safe"""
    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Price cannot be negative")

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"

    def discount_from(self, original: 'Price') -> int:
        """Calcola sconto percentuale rispetto a un altro prezzo"""
        if original.amount <= self.amount:
            return 0
        return int(((original.amount - self.amount) / original.amount) * 100)


@dataclass(frozen=True)
class ProductURL:
    """Value Object per URL prodotto con validazione"""
    url: str
    asin: Optional[str] = None

    def __post_init__(self):
        if not self.url.startswith("http"):
            raise ValueError("Invalid URL format")

    def is_amazon(self) -> bool:
        return "amazon" in self.url.lower() or "amzn" in self.url.lower()

    def is_ebay(self) -> bool:
        return "ebay" in self.url.lower()

    def get_clean_url(self) -> str:
        """Rimuove tracking parameters"""
        if self.asin and self.is_amazon():
            return f"https://www.amazon.it/dp/{self.asin}"
        return self.url.split('?')[0]


@dataclass(frozen=True)
class CategoryScore:
    """Value Object per rappresentare il match di una categoria"""
    category_name: str
    confidence: float  # 0.0 - 1.0

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")

    def is_confident(self) -> bool:
        """Match confidenziale se >70%"""
        return self.confidence >= 0.7
