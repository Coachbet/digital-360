import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adgi360.infrastructure.db.base import Base


class ClientModel(Base):
    """Un client de l'agence. Sert de racine pour l'organisation des fichiers
    (client > période) et pour le type de client utilisé par l'auto-review."""

    __tablename__ = "clients"
    # Unicité par agence : deux organisations peuvent avoir un client homonyme.
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_client_org_name"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Isolation multi-agences : toute lecture filtre sur cette colonne.
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Correspond aux valeurs de domain.auto_review.entities.ClientType
    client_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    files: Mapped[list["DataFileModel"]] = relationship(  # noqa: F821
        back_populates="client", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ReviewRequestModel"]] = relationship(  # noqa: F821
        back_populates="client", cascade="all, delete-orphan"
    )
