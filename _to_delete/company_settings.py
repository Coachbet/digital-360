from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adgi360.infrastructure.db.base import Base

PLACEHOLDER = "À compléter"


class CompanySettingsModel(Base):
    """Coordonnées de l'agence qui apparaissent sur les factures.

    Table à une seule ligne (id fixe = "default"). Les champs légaux sont
    volontairement initialisés à « À compléter » : rien n'est inventé, et une
    facture partant avec ces mentions se voit immédiatement.
    """

    __tablename__ = "company_settings"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default="default")

    legal_name: Mapped[str] = mapped_column(String(200), default="ADIGI360")
    tagline: Mapped[str] = mapped_column(String(200), default="Grandissons ensemble !")
    address: Mapped[str] = mapped_column(Text, default=PLACEHOLDER)
    phone: Mapped[str] = mapped_column(String(50), default="+1 514-812-2857")
    email: Mapped[str] = mapped_column(String(200), default="info@adigi360.com")
    website: Mapped[str] = mapped_column(String(200), default="www.adigi360.com")

    # Mentions légales — à renseigner par l'agence
    tax_number_1_label: Mapped[str] = mapped_column(String(50), default="No TPS")
    tax_number_1: Mapped[str] = mapped_column(String(80), default=PLACEHOLDER)
    tax_number_2_label: Mapped[str] = mapped_column(String(50), default="No TVQ")
    tax_number_2: Mapped[str] = mapped_column(String(80), default=PLACEHOLDER)
    registration_number: Mapped[str] = mapped_column(String(80), default=PLACEHOLDER)

    payment_terms: Mapped[str] = mapped_column(
        Text, default="Paiement à 30 jours à compter de la date d'émission."
    )
    payment_details: Mapped[str] = mapped_column(Text, default=PLACEHOLDER)

    # Logo optionnel, stocké dans MinIO (clé S3). Sans logo, le PDF affiche
    # un monogramme typographique aux couleurs de la marque.
    logo_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
