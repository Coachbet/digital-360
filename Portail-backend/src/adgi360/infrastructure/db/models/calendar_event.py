import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adgi360.infrastructure.db.base import Base


class CalendarEventModel(Base):
    """Événement du calendrier interne.

    `category` distingue les usages : échéance de rapport, campagne, rendez-vous
    client, planning interne. `source` vaut "internal" pour les événements créés
    dans le portail (les événements Google sont lus à la volée, pas stockés ici).
    """

    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Isolation multi-agences : toute lecture filtre sur cette colonne.
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # report_deadline | campaign | client_meeting | internal
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
