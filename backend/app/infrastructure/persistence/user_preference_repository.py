"""
Infrastructure - User Preference Repository
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain import UserPreference, IUserPreferenceRepository
from .sqlalchemy_models import UserPreferenceModel


class SQLAlchemyUserPreferenceRepository(IUserPreferenceRepository):
    """Repository per preferenze utente"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Optional[UserPreference]:
        """Recupera preferenze per user_id"""
        stmt = select(UserPreferenceModel).where(UserPreferenceModel.user_id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, preference: UserPreference) -> UserPreference:
        """Salva/aggiorna preferenze"""
        stmt = select(UserPreferenceModel).where(UserPreferenceModel.user_id == preference.user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            # Update
            model.preferred_categories = preference.preferred_categories
            model.max_price_by_category = {k: str(v) for k, v in preference.max_price_by_category.items()}
            model.saved_offer_ids = preference.saved_offer_ids
            model.price_alerts = {k: str(v) for k, v in preference.price_alerts.items()}
        else:
            # Create
            model = self._to_model(preference)
            self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    def _to_entity(self, model: UserPreferenceModel) -> UserPreference:
        """ORM Model -> Domain Entity"""
        from decimal import Decimal
        return UserPreference(
            id=model.id,
            user_id=model.user_id,
            preferred_categories=model.preferred_categories or [],
            max_price_by_category={k: Decimal(v) for k, v in (model.max_price_by_category or {}).items()},
            saved_offer_ids=model.saved_offer_ids or [],
            price_alerts={k: Decimal(v) for k, v in (model.price_alerts or {}).items()},
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _to_model(self, entity: UserPreference) -> UserPreferenceModel:
        """Domain Entity -> ORM Model"""
        return UserPreferenceModel(
            id=entity.id,
            user_id=entity.user_id,
            preferred_categories=entity.preferred_categories,
            max_price_by_category={k: str(v) for k, v in entity.max_price_by_category.items()},
            saved_offer_ids=entity.saved_offer_ids,
            price_alerts={k: str(v) for k, v in entity.price_alerts.items()}
        )
