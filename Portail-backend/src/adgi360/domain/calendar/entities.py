from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventCategory(str, Enum):
    """Les quatre usages du calendrier retenus pour le portail."""

    REPORT_DEADLINE = "report_deadline"
    CAMPAIGN = "campaign"
    CLIENT_MEETING = "client_meeting"
    INTERNAL = "internal"

    @property
    def label(self) -> str:
        return {
            EventCategory.REPORT_DEADLINE: "Échéance rapport",
            EventCategory.CAMPAIGN: "Campagne",
            EventCategory.CLIENT_MEETING: "Rendez-vous client",
            EventCategory.INTERNAL: "Planning interne",
        }[self]


class EventSource(str, Enum):
    INTERNAL = "internal"
    GOOGLE = "google"


@dataclass
class CalendarEvent:
    """Entité de domaine : ne dépend d'aucune techno."""

    id: str
    title: str
    start_at: datetime
    end_at: datetime
    category: EventCategory = EventCategory.INTERNAL
    source: EventSource = EventSource.INTERNAL
    description: str | None = None
    client_id: str | None = None
