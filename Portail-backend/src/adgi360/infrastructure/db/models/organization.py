import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adgi360.infrastructure.db.base import Base


class OrganizationModel(Base):
    """Une agence. C'est la racine d'isolation : chaque donnée métier porte un
    `organization_id`, et toutes les requêtes le filtrent.

    Le branding vit ici plutôt que dans une table séparée : ce sont des
    attributs de l'agence, toujours lus en même temps qu'elle, et il n'y en a
    qu'un jeu par organisation.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)

    # --- Identité de marque, reprise sur les decks et les factures générés
    brand_primary: Mapped[str] = mapped_column(String(7), default="#6C4CF1")
    brand_ink: Mapped[str] = mapped_column(String(7), default="#171633")
    brand_accent: Mapped[str] = mapped_column(String(7), default="#EDE9FE")
    tagline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Gabarit PowerPoint téléversé par l'agence, utilisé comme base des rapports
    deck_template_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # --- Coordonnées légales, imprimées sur les factures
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tax_number_1_label: Mapped[str] = mapped_column(String(50), default="No TPS")
    tax_number_1: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tax_number_2_label: Mapped[str] = mapped_column(String(50), default="No TVQ")
    tax_number_2: Mapped[str | None] = mapped_column(String(80), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    users: Mapped[list["UserModel"]] = relationship(  # noqa: F821
        back_populates="organization", cascade="all, delete-orphan"
    )


class UserModel(Base):
    """Un compte de connexion, rattaché à une organisation.

    Le mot de passe n'est jamais stocké en clair : seul son hachage bcrypt est
    conservé, et rien dans l'API ne renvoie ce champ.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped["OrganizationModel"] = relationship(back_populates="users")
