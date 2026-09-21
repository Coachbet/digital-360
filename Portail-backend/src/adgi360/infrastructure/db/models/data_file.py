import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adgi360.infrastructure.db.base import Base


class DataFileModel(Base):
    """Un fichier déposé dans le module Data, rangé par client puis par période.

    Le contenu vit dans MinIO/S3 ; cette table garde les métadonnées et la clé
    de stockage (`storage_key`) qui permet de le retrouver.
    """

    __tablename__ = "data_files"

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
    # Période au format libre mais normalisé côté API : "2026-08", "2026-Q3", "campagne-ete"
    period: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    client: Mapped["ClientModel"] = relationship(back_populates="files")  # noqa: F821
