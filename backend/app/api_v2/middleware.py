"""
Custom Middleware per Security & Performance
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting Middleware (in-memory, per IP).
    Per production, usare Redis-based rate limiter.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Escludi health check
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host
        now = datetime.now()

        # Cleanup vecchie richieste
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if now - req_time < timedelta(minutes=1)
        ]

        # Check limit
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded. Try again later."}
            )

        # Aggiungi richiesta corrente
        self.request_counts[client_ip].append(now)

        response = await call_next(request)
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware per logging performance (response time)
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000  # ms
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Log slow requests (>500ms)
        if process_time > 500:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}ms"
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware per aggiungere Security Headers
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
