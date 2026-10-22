from collections.abc import AsyncGenerator

from sqlalchemy import text
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
        # create_all crée les tables manquantes mais n'ajoute jamais de colonne
        # à une table existante. En attendant Alembic, les colonnes ajoutées
        # depuis la première version sont posées ici, de façon idempotente.
        if conn.dialect.name == "postgresql":
            for statement in _ADDED_COLUMNS:
                await conn.execute(text(statement))


# Chaque instruction doit pouvoir être rejouée à chaque démarrage sans effet.
_ADDED_COLUMNS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_user_id BIGINT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_linked_at TIMESTAMPTZ",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone ON users (phone)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_telegram_user_id ON users (telegram_user_id)",
    # Idempotence du bot : une mise à jour Telegram n'est traitée qu'une fois.
    "ALTER TABLE bot_events ADD COLUMN IF NOT EXISTS update_id BIGINT",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_bot_events_update_id ON bot_events (update_id)",
)
