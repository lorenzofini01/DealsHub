"""
Application Layer Package
Orchestrazione use cases e DTOs
"""
from .dtos import (
    IngestOfferDTO, SearchOffersDTO, TrackEventDTO, SetPriceAlertDTO,
    OfferDTO, OfferListDTO, CategoryStatsDTO, DashboardStatsDTO, UserProfileDTO
)
from .use_cases import (
    IngestOfferUseCase, SearchOffersUseCase,
    TrackUserEventUseCase, VerifyOffersUseCase
)

__all__ = [
    # DTOs
    "IngestOfferDTO",
    "SearchOffersDTO",
    "TrackEventDTO",
    "SetPriceAlertDTO",
    "OfferDTO",
    "OfferListDTO",
    "CategoryStatsDTO",
    "DashboardStatsDTO",
    "UserProfileDTO",

    # Use Cases
    "IngestOfferUseCase",
    "SearchOffersUseCase",
    "TrackUserEventUseCase",
    "VerifyOffersUseCase",
]
