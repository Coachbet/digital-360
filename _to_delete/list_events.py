from adgi360.domain.calendar.entities import CalendarEvent


class ListEventsUseCase:
    """Cas d'usage : récupérer les événements (internes + synchro externe).

    Placeholder : branchera plus tard sur un repository (infrastructure/db)
    et les clients Google/Outlook (infrastructure/calendar_sync).
    """

    async def execute(self) -> list[CalendarEvent]:
        return []
