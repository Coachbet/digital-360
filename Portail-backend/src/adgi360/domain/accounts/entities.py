"""Comptes et organisations — le socle multi-agences de Digital 360.

Une **organisation** est une agence cliente du produit. Toutes les données
métier (clients finaux, fichiers, rapports, factures, événements) lui
appartiennent et ne sont jamais visibles d'une autre organisation.

Un **utilisateur** appartient à une seule organisation. C'est volontairement
simple : les agences qui auraient besoin qu'une personne travaille pour
plusieurs structures créeront un compte par structure, plutôt que de nous
imposer une table d'appartenances multiples dès le départ.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Trois rôles suffisent à couvrir le fonctionnement d'une agence."""

    OWNER = "owner"      # a créé l'organisation : facturation, suppression, invitations
    ADMIN = "admin"      # gère les clients, les connecteurs et le branding
    MEMBER = "member"    # produit et valide les rapports

    @property
    def label(self) -> str:
        return {
            UserRole.OWNER: "Propriétaire",
            UserRole.ADMIN: "Administrateur",
            UserRole.MEMBER: "Membre",
        }[self]

    @property
    def rank(self) -> int:
        return {UserRole.MEMBER: 0, UserRole.ADMIN: 1, UserRole.OWNER: 2}[self]

    def can(self, required: "UserRole") -> bool:
        """Un rôle donne accès à tout ce que permettent les rôles inférieurs."""
        return self.rank >= required.rank


@dataclass
class Organization:
    """Une agence utilisatrice de Digital 360."""

    id: str
    name: str
    slug: str
    created_at: datetime | None = None


@dataclass
class User:
    id: str
    organization_id: str
    email: str
    full_name: str
    role: UserRole = UserRole.MEMBER
    is_active: bool = True
    phone: str | None = None
    telegram_user_id: int | None = None
    created_at: datetime | None = None


def normalize_email(email: str) -> str:
    """L'email sert d'identifiant de connexion : on le normalise pour qu'une
    différence de casse ou d'espaces ne crée pas un doublon de compte."""
    return email.strip().lower()


def normalize_phone(raw: str) -> str:
    """Ramène un numéro au format international E.164 (« +15145551234 »).

    Le même numéro arrive sous plusieurs formes : saisi dans le portail
    (« (514) 555-1234 »), partagé par Telegram (« 15145551234 » ou
    « +15145551234 »). La liaison Telegram compare des chaînes : sans cette
    normalisation unique, un utilisateur légitime serait refusé.

    Un numéro à 10 chiffres est considéré nord-américain (indicatif 1), ce qui
    correspond à la clientèle des agences québécoises.
    """
    if raw is None:
        raise ValueError("Numéro de téléphone manquant")
    text = str(raw).strip()
    digits = "".join(c for c in text if c.isdigit())
    if text.startswith("00"):
        digits = digits[2:]
    elif not text.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    if not 8 <= len(digits) <= 15:
        raise ValueError("Numéro de téléphone invalide")
    return "+" + digits


def slugify(name: str) -> str:
    """Identifiant lisible d'une organisation, utilisé dans les URL et les
    préfixes de stockage."""
    import unicodedata

    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in ascii_name)
    return "-".join(part for part in cleaned.split("-") if part) or "organisation"
