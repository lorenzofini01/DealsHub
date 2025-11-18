import os
from fastapi import FastAPI, HTTPException
from . import models, crud, schemas, database
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

# Importiamo la lista categorie dal worker per coerenza
from .tasks import CATEGORY_RULES

app = FastAPI(title="DealsHub API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    await database.connect()
    await models.create_tables()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/api/offers/ingest", status_code=201)
async def ingest_offer(payload: schemas.OfferIn):
    offer = await crud.create_or_update_offer(payload)
    return offer

@app.get("/api/offers/active")
async def get_active_offers(limit: int = 50, offset: int = 0, category: Optional[str] = None, search: Optional[str] = None):
    return await crud.get_offers(status="active", limit=limit, offset=offset, category=category, search=search)

# NUOVO ENDPOINT
@app.get("/api/categories")
async def get_categories():
    # Restituisce la lista pulita (solo nomi) per il frontend
    cats = [r["name"] for r in CATEGORY_RULES]
    # Aggiungi "Tutte" all'inizio e "Altro" alla fine
    return ["Tutte"] + cats + ["📦 Altro"]