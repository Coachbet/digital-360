from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.auto_review.entities import ReviewStatus
from adgi360.infrastructure.db.models import ReviewRequestModel
from adgi360.infrastructure.storage.client import FileStorage


class SyncReportsUseCase:
    """Détecte les rapports déposés par n8n dans MinIO.

    n8n écrit le PowerPoint sous `reports/<review_id>/` sans prévenir le backend.
    Ce cas d'usage parcourt les reviews en cours de génération et bascule en
    « à valider » celles dont le fichier est arrivé. Il est appelé à chaque
    consultation de la liste des reviews côté frontend.
    """

    def __init__(self, session: AsyncSession, storage: FileStorage) -> None:
        self._session = session
        self._storage = storage

    async def execute(self) -> int:
        """Retourne le nombre de reviews passées en attente de validation."""
        result = await self._session.execute(
            select(ReviewRequestModel).where(
                ReviewRequestModel.status == ReviewStatus.PROCESSING.value
            )
        )
        pending = list(result.scalars().all())
        if not pending:
            return 0

        updated = 0
        for review in pending:
            objects = await self._storage.list_keys(f"reports/{review.id}/")
            if not objects:
                continue
            # Le plus récent fait foi si n8n a déposé plusieurs versions
            latest = max(objects, key=lambda o: o["last_modified"])
            review.report_storage_key = latest["key"]
            review.report_filename = latest["key"].rsplit("/", 1)[-1]
            review.status = ReviewStatus.AWAITING_APPROVAL.value
            updated += 1

        if updated:
            await self._session.commit()
        return updated
