from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.auto_review.entities import ClientType, ReviewStatus
from adgi360.infrastructure.db.models import ClientModel, DataFileModel, ReviewRequestModel
from adgi360.infrastructure.config.settings import settings
from adgi360.infrastructure.n8n.client import N8nClient
from adgi360.infrastructure.security import create_callback_token
from adgi360.infrastructure.storage.client import FileStorage
from adgi360.shared.exceptions import ExternalServiceError, NotFoundError, ValidationError

# Durée de vie des URL de téléchargement remises à n8n. Assez large pour couvrir
# une analyse lente, assez courte pour qu'une URL qui fuite ne serve plus.
SOURCE_URL_TTL_SECONDS = 30 * 60


class LaunchAutoReviewUseCase:
    """Crée une demande de review et déclenche l'analyse par n8n.

    Répartition des rôles : n8n télécharge les fichiers sources, les fait
    analyser par l'IA locale et renvoie un plan de rapport en JSON ; le backend
    transforme ce plan en PowerPoint. L'URL de rappel est transmise dans le
    payload pour que le workflow n'ait aucune adresse codée en dur.
    """

    def __init__(
        self, session: AsyncSession, n8n_client: N8nClient, storage: FileStorage
    ) -> None:
        self._session = session
        self._n8n = n8n_client
        self._storage = storage

    async def execute(
        self,
        organization_id: str,
        client_id: str,
        client_type: str,
        data_file_ids: list[str],
        additional_info: str | None = None,
        notify_telegram_chat_id: int | None = None,
    ) -> ReviewRequestModel:
        client = await self._session.get(ClientModel, client_id)
        if client is None or client.organization_id != organization_id:
            raise NotFoundError("Client introuvable")

        try:
            resolved_type = ClientType(client_type)
        except ValueError as exc:
            raise ValidationError(f"Type de client inconnu : {client_type}") from exc

        if not data_file_ids:
            raise ValidationError("Au moins un fichier source doit être sélectionné")

        result = await self._session.execute(
            select(DataFileModel).where(
                DataFileModel.id.in_(data_file_ids),
                # Le filtre par agence empêche de rattacher à sa review le
                # fichier d'une autre organisation en devinant son identifiant.
                DataFileModel.organization_id == organization_id,
                DataFileModel.client_id == client_id,
            )
        )
        files = list(result.scalars().all())
        if len(files) != len(data_file_ids):
            raise ValidationError("Certains fichiers sélectionnés sont introuvables")
        if any(not f.filename.lower().endswith(".xlsx") for f in files):
            raise ValidationError("L'analyse accepte actuellement uniquement les fichiers Excel .xlsx")

        review = ReviewRequestModel(
            organization_id=organization_id,
            client_id=client_id,
            client_type=resolved_type.value,
            data_file_ids=data_file_ids,
            additional_info=additional_info,
            status=ReviewStatus.PENDING.value,
        )
        self._session.add(review)
        await self._session.commit()
        await self._session.refresh(review)

        payload = {
            "review_id": review.id,
            "client": {
                "id": client.id,
                "name": client.name,
                "contact_email": client.contact_email,
            },
            "client_type": resolved_type.value,
            "client_type_label": resolved_type.label,
            "additional_info": additional_info,
            # Chaque fichier porte sa propre URL de téléchargement, signée et
            # limitée dans le temps. n8n n'a donc besoin d'aucun identifiant de
            # stockage : le bucket peut rester entièrement privé.
            "source_files": [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "storage_key": f.storage_key,
                    "period": f.period,
                    "content_type": f.content_type,
                    "download_url": await self._storage.presigned_url(
                        f.storage_key,
                        expires_in=SOURCE_URL_TTL_SECONDS,
                        endpoint_url=settings.s3_n8n_endpoint_url,
                    ),
                }
                for f in files
            ],
            # Où n8n renvoie le plan du rapport une fois l'analyse terminée.
            # host.docker.internal : n8n est conteneurisé, le backend tourne sur l'hôte.
            # Jeton HMAC : n8n n'a pas de session, l'URL porte sa propre preuve.
            "render_callback_url": (
                f"{settings.backend_public_url}/api/v1/auto-review/{review.id}/render"
                f"?token={create_callback_token(review.id)}"
            ),
            # Rappel en cas d'échec de l'analyse : même jeton que le rendu,
            # pour que la review ne reste pas bloquée « en cours ».
            "fail_callback_url": (
                f"{settings.backend_public_url}/api/v1/auto-review/{review.id}/fail"
                f"?token={create_callback_token(review.id)}"
            ),
            # Renseigné quand la demande vient du bot : n8n renvoie alors le
            # PowerPoint dans la conversation Telegram d'origine.
            "notify": {"telegram_chat_id": notify_telegram_chat_id},
        }

        try:
            review.status = ReviewStatus.PROCESSING.value
            await self._session.commit()
            await self._n8n.trigger_auto_review(payload)
        except ExternalServiceError as exc:
            review.status = ReviewStatus.FAILED.value
            review.error_message = str(exc)
            await self._session.commit()
            await self._session.refresh(review)
            raise

        await self._session.refresh(review)
        return review
