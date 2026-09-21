"""Client d'appel au workflow n8n d'analyse.

Contrat : le backend envoie un POST sur le webhook n8n avec les informations de
la review. n8n télécharge les fichiers sources depuis MinIO, les fait analyser
par l'IA locale (Ollama), puis rappelle le backend sur
`POST /api/v1/auto-review/{review_id}/render` avec le plan du rapport en JSON.
Le backend produit alors le PowerPoint et bascule la review en « à relire ».

Aucun envoi de mail n'intervient dans la chaîne.
"""

import httpx

from adgi360.infrastructure.config.settings import settings
from adgi360.shared.exceptions import ExternalServiceError


class N8nClient:
    def __init__(self, webhook_url: str | None = None, timeout: float = 30.0) -> None:
        self._webhook_url = webhook_url or settings.n8n_webhook_url
        self._timeout = timeout

    async def trigger_auto_review(self, payload: dict) -> None:
        """Déclenche l'analyse. n8n répond immédiatement puis travaille en fond."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Appel n8n en échec : {exc}") from exc


def get_n8n_client() -> N8nClient:
    """Dépendance FastAPI."""
    return N8nClient()
