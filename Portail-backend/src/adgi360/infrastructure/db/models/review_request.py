import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from adgi360.infrastructure.db.base import Base


class ReviewRequestModel(Base):
    """Une demande de review automatique.

    Cycle de vie (voir domain.auto_review.entities.ReviewStatus) :
    pending -> processing -> awaiting_approval -> approved
                          \\-> failed
    """

    __tablename__ = "review_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Isolation multi-agences : toute lecture filtre sur cette colonne.
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    client_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Liste des ids de DataFileModel sélectionnés dans le formulaire
    data_file_ids: Mapped[list] = mapped_column(JSON, default=list)
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rapport produit par le backend à partir du plan rédigé par l'IA
    report_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    report_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped["ClientModel"] = relationship(back_populates="reviews")  # noqa: F821
