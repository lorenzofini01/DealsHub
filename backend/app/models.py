# backend/app/models.py
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from .database import engine

Base = declarative_base()


class Offer(Base):
    __tablename__ = "offers"
    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.String, nullable=True)
    text = sa.Column(sa.Text, nullable=True)
    product_url = sa.Column(sa.Text, unique=False, index=True)
    image_url = sa.Column(sa.Text, nullable=True)

    # PREZZI
    price = sa.Column(sa.Numeric(10, 2), nullable=True)  # Prezzo Attuale
    original_price = sa.Column(sa.Numeric(10, 2), nullable=True)  # Prezzo Barrato (Listino)
    discount = sa.Column(sa.Integer, nullable=True)  # Percentuale sconto (es. 20)

    currency = sa.Column(sa.String(8), default="EUR")
    shop = sa.Column(sa.String, nullable=True)
    category = sa.Column(sa.String, nullable=True, index=True)  # Aggiunto index per velocità
    status = sa.Column(sa.String, default="verifying")
    created_at = sa.Column(sa.DateTime, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)