# backend/app/schemas.py
from pydantic import BaseModel, HttpUrl
from typing import Optional

class OfferIn(BaseModel):
    source: str
    chat_id: str
    message_id: int
    text: str
    url: HttpUrl
