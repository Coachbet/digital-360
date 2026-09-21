from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.calendar.entities import EventCategory
from adgi360.infrastructure.calendar_sync.google_calendar import (
    GoogleCalendarClient,
    get_google_calendar_client,
)
from adgi360.infrastructure.db.models import CalendarEventModel
from adgi360.infrastructure.db.session import get_session
from adgi360.interfaces.api.deps import CurrentUser
from adgi360.interfaces.api.v1.schemas.calendar_schemas import (
    CalendarEventCreate,
    CalendarEventOut,
    CategoryOut,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories() -> list[CategoryOut]:
    return [CategoryOut(value=c.value, label=c.label) for c in EventCategory]


@router.get("/events", response_model=list[CalendarEventOut])
async def list_events(
    user: CurrentUser,
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
    google: GoogleCalendarClient = Depends(get_google_calendar_client),
) -> list[CalendarEventOut]:
    """Événements internes, complétés par ceux de Google Calendar en lecture
    seule lorsque la synchro est configurée."""
    query = select(CalendarEventModel).where(
        CalendarEventModel.organization_id == user.organization_id
    )
    if start:
        query = query.where(CalendarEventModel.end_at >= start)
    if end:
        query = query.where(CalendarEventModel.start_at <= end)
    result = await session.execute(query.order_by(CalendarEventModel.start_at))

    events = [
        CalendarEventOut.model_validate(row, from_attributes=True)
        for row in result.scalars().all()
    ]

    if google.is_configured() and start and end:
        for external in await google.list_events(start, end):
            events.append(
                CalendarEventOut(
                    id=external.id,
                    title=external.title,
                    description=external.description,
                    start_at=external.start_at,
                    end_at=external.end_at,
                    category=external.category.value,
                    client_id=external.client_id,
                    source="google",
                )
            )
        events.sort(key=lambda e: e.start_at)

    return events


@router.post("/events", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: CalendarEventCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> CalendarEventModel:
    if payload.end_at < payload.start_at:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La date de fin doit être postérieure à la date de début",
        )
    try:
        EventCategory(payload.category)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Catégorie inconnue : {payload.category}"
        ) from exc

    event = CalendarEventModel(organization_id=user.organization_id, **payload.model_dump())
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> None:
    event = await session.get(CalendarEventModel, event_id)
    if event is None or event.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Événement introuvable")
    await session.delete(event)
    await session.commit()
