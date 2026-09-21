from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from adgi360.infrastructure.config.settings import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI : fournit une session de base de données par requête."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Crée les tables si elles n'existent pas.

    Suffisant en développement. En production, remplacer par des migrations
    (Alembic) pour gérer proprement l'évolution du schéma.
    """
    # Import nécessaire pour que les modèles soient enregistrés sur Base.metadata
    from adgi360.infrastructure.db import models  # noqa: F401
    from adgi360.infrastructure.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
