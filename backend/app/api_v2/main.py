"""
FastAPI Application - Clean Architecture Edition
Zero business logic: solo routing e middleware
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes import router
from .middleware import RateLimitMiddleware, PerformanceMiddleware, SecurityHeadersMiddleware
from .dependencies import startup_event, shutdown_event

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ===== App Creation =====

app = FastAPI(
    title="DealsHub API v2.0",
    description="AI-Powered Deal Intelligence Platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ===== CORS (Configurazione sicura) =====
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server
    "https://yourproductiondomain.com",  # Aggiungi il tuo dominio
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # NON più "*" in produzione!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight 1 ora
)

# ===== Security & Performance Middleware =====
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PerformanceMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)  # 120 req/min per IP

# ===== Routes =====
app.include_router(router)

# ===== Events =====
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


# ===== Root Endpoint =====
@app.get("/")
async def root():
    return {
        "message": "DealsHub API v2.0 - AI-Powered Deal Intelligence",
        "docs": "/api/docs",
        "health": "/api/v2/health"
    }
