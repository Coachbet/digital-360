"""Synchronisation Google Calendar — lecture seule.

Décision produit : le portail affiche les événements Google mais ne les modifie
jamais. Cela évite tout risque de corrompre les agendas de l'équipe et simplifie
nettement l'authentification.

Implémentation à venir : compte de service Google Workspace avec délégation
domaine, ou OAuth2 par utilisateur. Tant que les identifiants ne sont pas
configurés, `is_configured()` renvoie False et le portail fonctionne
normalement avec les seuls événements internes.
"""

from datetime import datetime

from adgi360.domain.calendar.entities import CalendarEvent


class GoogleCalendarClient:
    def __init__(self, credentials_path: str | None = None) -> None:
        self._credentials_path = credentials_path

    def is_configured(self) -> bool:
        return self._credentials_path is not None

    async def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Événements Google sur une plage de dates. Renvoie une liste vide tant
        que la synchro n'est pas configurée, pour ne pas bloquer le calendrier
        interne."""
        if not self.is_configured():
            return []
        raise NotImplementedError(
            "Synchro Google Calendar à implémenter (google-api-python-client)"
        )


def get_google_calendar_client() -> GoogleCalendarClient:
    """Dépendance FastAPI."""
    return GoogleCalendarClient()
