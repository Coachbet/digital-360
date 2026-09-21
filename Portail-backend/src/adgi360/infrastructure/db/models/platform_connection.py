import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from adgi360.infrastructure.db.base import Base


class PlatformConnectionModel(Base):
    """Connexion publicitaire générique.

    Les secrets sont sérialisés en JSON puis chiffrés en un seul bloc. Le
    navigateur ne reçoit que la liste des champs configurés, jamais leur valeur.
    """

    __tablename__ = "platform_connections"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "client_id", "platform",
            name="uq_platform_connection_org_client_platform",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(200), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    configured_fields: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
