from fastapi import APIRouter
from sqlalchemy import text

from adgi360.infrastructure.db.session import engine
from adgi360.infrastructure.storage.client import FileStorage

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """État des dépendances : pratique pour vérifier que Docker tourne bien."""
    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"erreur: {type(exc).__name__}"

    try:
        await FileStorage().ensure_bucket()
        checks["storage"] = "ok"
    except Exception as exc:
        checks["storage"] = f"erreur: {type(exc).__name__}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
