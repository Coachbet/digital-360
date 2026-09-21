"""Client de synchronisation avec Outlook Calendar. Placeholder à implémenter
(Microsoft Graph API)."""

from adgi360.domain.calendar.entities import CalendarEvent


class OutlookCalendarClient:
    async def list_events(self) -> list[CalendarEvent]:
        raise NotImplementedError("Synchro Outlook Calendar pas encore implémentée")
