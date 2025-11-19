"""
Infrastructure - SQLAlchemy ORM Models
Separati dalle Domain Entities per mantenere clean architecture
"""
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class OfferModel(Base):
    """ORM Model per Offer (con indici ottimizzati)"""
    __tablename__ = "offers"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    product_url = sa.Column(sa.Text, nullable=False)
    title = sa.Column(sa.String(500), nullable=True)
    text = sa.Column(sa.Text, nullable=True)
    image_url = sa.Column(sa.Text, nullable=True)

    # Pricing
    price = sa.Column(sa.Numeric(10, 2), nullable=True)
    original_price = sa.Column(sa.Numeric(10, 2), nullable=True)
    discount_percentage = sa.Column(sa.Integer, default=0)
    currency = sa.Column(sa.String(8), default="EUR")

    # Metadata
    shop = sa.Column(sa.String(50), nullable=True)
    category = sa.Column(sa.String(100), nullable=True, index=True)
    status = sa.Column(sa.String(20), default="verifying", index=True)

    # Analytics (NUOVO)
    deal_score = sa.Column(sa.Integer, default=0, index=True)  # Indice per ordinamento
    view_count = sa.Column(sa.Integer, default=0)
    click_count = sa.Column(sa.Integer, default=0)
    save_count = sa.Column(sa.Integer, default=0)

    # ASIN per deduplicazione
    asin = sa.Column(sa.String(20), nullable=True, index=True, unique=True)

    # Timestamps
    created_at = sa.Column(sa.DateTime, default=datetime.now, index=True)
    updated_at = sa.Column(sa.DateTime, default=datetime.now, onupdate=datetime.now)
    verified_at = sa.Column(sa.DateTime, nullable=True)

    # INDICI COMPOSTI per performance queries
    __table_args__ = (
        sa.Index('idx_status_score', 'status', 'deal_score'),
        sa.Index('idx_status_created', 'status', 'created_at'),
        sa.Index('idx_category_status', 'category', 'status'),
        sa.Index('idx_status_title_null', 'status', 'title'),  # Per priorità verifica
    )


class UserPreferenceModel(Base):
    """ORM Model per preferenze utente"""
    __tablename__ = "user_preferences"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.String(100), unique=True, nullable=False, index=True)

    # JSON columns per flessibilità
    preferred_categories = sa.Column(sa.JSON, default=list)
    max_price_by_category = sa.Column(sa.JSON, default=dict)
    saved_offer_ids = sa.Column(sa.JSON, default=list)
    price_alerts = sa.Column(sa.JSON, default=dict)

    created_at = sa.Column(sa.DateTime, default=datetime.now)
    updated_at = sa.Column(sa.DateTime, default=datetime.now, onupdate=datetime.now)


class PriceHistoryModel(Base):
    """ORM Model per storico prezzi"""
    __tablename__ = "price_history"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    asin = sa.Column(sa.String(20), nullable=False, index=True)
    price = sa.Column(sa.Numeric(10, 2), nullable=False)
    recorded_at = sa.Column(sa.DateTime, default=datetime.now, index=True)
    source = sa.Column(sa.String(50), default="scraper")

    __table_args__ = (
        sa.Index('idx_asin_recorded', 'asin', 'recorded_at'),
    )


async def create_all_tables(engine):
    """Crea tutte le tabelle con indici ottimizzati"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
