import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from adgi360.infrastructure.db.base import Base


class AdvertisingConnectionModel(Base):
    """Identifiants Meta propres à une agence, chiffrés avant écriture."""

    __tablename__ = "advertising_connections"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "client_id", name="uq_advertising_connection_org_client"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meta_ad_account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    instagram_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    meta_access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    instagram_access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
