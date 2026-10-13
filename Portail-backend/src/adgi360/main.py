import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adgi360.infrastructure.config.settings import settings
from adgi360.infrastructure.db.session import init_db
from adgi360.infrastructure.storage.client import FileStorage
from adgi360.interfaces.api.v1.routers import (
    advertising,
    auth,
    auto_review,
    bot,
    calendar,
    clients,
    data,
    health,
    invoices,
    organization,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Au démarrage : crée les tables et s'assure que le bucket existe.

    Les erreurs ne sont pas fatales pour laisser l'API démarrer même si Docker
    n'est pas encore lancé — /api/v1/health répondra et indiquera le problème.
    """
    try:
        await init_db()
    except Exception as exc:
        logger.warning("Base de données indisponible au démarrage : %s", exc)
    try:
        await FileStorage().ensure_bucket()
    except Exception as exc:
        logger.warning("Stockage indisponible au démarrage : %s", exc)
    yield


app = FastAPI(
    title="Digital 360 — API",
    version="0.2.0",
    description=(
        "Plateforme multi-agences : données clients, rapports générés par IA, "
        "calendrier et facturation. Chaque agence ne voit que ses propres données."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    health.router,
    auth.router,
    advertising.router,
    organization.router,
    clients.router,
    data.router,
    auto_review.router,
    bot.router,
    calendar.router,
    invoices.router,
):
    app.include_router(router, prefix="/api/v1")
