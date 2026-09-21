import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.auto_review.entities import ReviewStatus
from adgi360.domain.data.entities import build_report_key
from adgi360.infrastructure.db.models import (
    ClientModel,
    DataFileModel,
    OrganizationModel,
    ReviewRequestModel,
)
from adgi360.infrastructure.pptx.preview import render_pptx_preview_pdf
from adgi360.infrastructure.pptx.report_renderer import deck_from_dict, render_report_pptx
from adgi360.infrastructure.storage.client import FileStorage
from adgi360.shared.exceptions import NotFoundError, ValidationError


def _safe_filename(text: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "-" for c in text)
    return "-".join(part for part in cleaned.split("-") if part) or "rapport"


class RenderReportUseCase:
    """Transforme le plan de rapport rédigé par l'IA en fichier PowerPoint.

    C'est le point d'entrée appelé par n8n une fois l'analyse terminée : n8n
    fournit la structure du deck en JSON, le backend s'occupe de la mise en
    forme et de l'archivage. Ce partage évite d'avoir à générer du PPTX depuis
    n8n, qui n'a pas de nœud pour ça.
    """

    def __init__(self, session: AsyncSession, storage: FileStorage) -> None:
        self._session = session
        self._storage = storage

    async def execute(self, review_id: str, deck_payload: dict) -> ReviewRequestModel:
        review = await self._session.get(ReviewRequestModel, review_id)
        if review is None:
            raise NotFoundError("Review introuvable")

        client = await self._session.get(ClientModel, review.client_id)
        client_name = client.name if client else ""

        # La période affichée en couverture vient des fichiers sources retenus.
        period = ""
        if review.data_file_ids:
            first = await self._session.get(DataFileModel, review.data_file_ids[0])
            if first:
                period = first.period

        if not isinstance(deck_payload, dict):
            raise ValidationError("Le plan du rapport doit être un objet JSON")

        deck = deck_from_dict(deck_payload, client_name=client_name, period=period)
        organization = await self._session.get(OrganizationModel, review.organization_id)
        template_bytes = None
        logo_bytes = None
        if organization and organization.deck_template_key:
            try:
                template_bytes = await self._storage.download(organization.deck_template_key)
            except Exception:
                template_bytes = None
        if organization and organization.logo_storage_key:
            try:
                logo_bytes = await self._storage.download(organization.logo_storage_key)
            except Exception:
                logo_bytes = None
        pptx_bytes = render_report_pptx(deck, template_bytes=template_bytes, logo_bytes=logo_bytes)

        filename = f"Rapport-{_safe_filename(client_name)}-{_safe_filename(period)}.pptx"
        key = build_report_key(review.organization_id, review.id, filename)

        await self._storage.ensure_bucket()
        await self._storage.upload(
            key,
            pptx_bytes,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        try:
            preview_bytes = await asyncio.to_thread(render_pptx_preview_pdf, pptx_bytes)
        except Exception:
            logging.getLogger(__name__).exception("Aperçu PDF indisponible")
            preview_bytes = None
        if preview_bytes:
            await self._storage.upload(
                f"{key.rsplit('.', 1)[0]}.pdf", preview_bytes, "application/pdf"
            )

        review.report_storage_key = key
        review.report_filename = filename
        review.status = ReviewStatus.AWAITING_APPROVAL.value
        review.error_message = None
        await self._session.commit()
        await self._session.refresh(review)
        return review
