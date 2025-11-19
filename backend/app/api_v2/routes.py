"""
API Routes - Clean & RESTful
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import hashlib

from ..application import (
    IngestOfferDTO, SearchOffersDTO, TrackEventDTO,
    OfferDTO, OfferListDTO,
    IngestOfferUseCase, SearchOffersUseCase, TrackUserEventUseCase
)
from .dependencies import (
    get_db_session,
    get_ingest_offer_use_case,
    get_search_offers_use_case,
    get_track_event_use_case,
    get_category_service
)

router = APIRouter(prefix="/api/v2")


# ===== Helper: Get User ID from Cookie/IP =====
def get_user_id(request: Request) -> str:
    """
    Genera user_id da cookie o IP (per tracking anonimo).
    Per auth reale, sostituire con JWT token.
    """
    # Controlla cookie
    user_id_cookie = request.cookies.get("dealshub_user_id")
    if user_id_cookie:
        return user_id_cookie

    # Fallback: hash dell'IP + User-Agent
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    return hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]


# ===== Offers Endpoints =====

@router.post("/offers/ingest", response_model=OfferDTO, status_code=status.HTTP_201_CREATED)
async def ingest_offer(
    payload: IngestOfferDTO,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint per collector Telegram.
    Ingerisce nuova offerta (o aggiorna esistente).
    """
    use_case = await get_ingest_offer_use_case(session)
    result = await use_case.execute(payload)
    return result


@router.get("/offers", response_model=OfferListDTO)
async def search_offers(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    session: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint per ricerca offerte.
    Supporta filtri per categoria, ricerca full-text, score minimo.
    Cache-friendly con TTL 5 minuti.
    """
    dto = SearchOffersDTO(
        limit=limit,
        offset=offset,
        category=category,
        search=search,
        min_score=min_score,
        sort_by=sort_by,
        sort_order=sort_order
    )

    use_case = await get_search_offers_use_case(session)
    result = await use_case.execute(dto)
    return result


@router.post("/offers/{offer_id}/track", status_code=status.HTTP_202_ACCEPTED)
async def track_event(
    offer_id: int,
    event_type: str,  # view, click, save, unsave
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Track user events (view, click, save).
    Usato per analytics e recommendation engine.
    """
    user_id = get_user_id(request)

    dto = TrackEventDTO(
        user_id=user_id,
        offer_id=offer_id,
        event_type=event_type
    )

    use_case = await get_track_event_use_case(session)
    result = await use_case.execute(dto)

    return result


# ===== Categories Endpoint =====

@router.get("/categories")
async def get_categories():
    """
    Ritorna lista categorie disponibili.
    """
    category_service = get_category_service()
    categories = ["Tutte"] + list(category_service.CATEGORIES.keys()) + ["📦 Altro"]
    return categories


# ===== Health Check =====

@router.get("/health")
async def health_check():
    """Health check per monitoring"""
    return {"status": "healthy", "version": "2.0.0"}
