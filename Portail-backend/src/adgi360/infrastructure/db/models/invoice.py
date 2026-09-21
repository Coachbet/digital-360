import uuid
from datetime import date, datetime

from sqlalchemy import UniqueConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from adgi360.infrastructure.db.base import Base


class InvoiceModel(Base):
    """Une facture. Les lignes sont stockées en JSON : elles n'ont pas de vie
    propre en dehors de leur facture et ne sont jamais requêtées séparément."""

    __tablename__ = "invoices"
    # La numérotation est séquentielle au sein d'une agence, pas globale.
    __table_args__ = (
        UniqueConstraint("organization_id", "number", name="uq_invoice_org_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Isolation multi-agences : toute lecture filtre sur cette colonne.
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Client : rattaché au référentiel si possible, sinon saisi librement
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # [{"description": str, "quantity": str, "unit_price": str}]
    lines: Mapped[list] = mapped_column(JSON, default=list)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CAD")
    tax_regime: Mapped[str] = mapped_column(String(20), nullable=False, default="qc_gst_qst")
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="issued", index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Montants figés au moment de l'émission : une facture archivée ne doit pas
    # changer si les taux de taxes évoluent plus tard.
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    pdf_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
