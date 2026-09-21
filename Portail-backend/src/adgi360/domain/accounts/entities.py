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
    created_at: datetime | None = None


def normalize_email(email: str) -> str:
    """L'email sert d'identifiant de connexion : on le normalise pour qu'une
    différence de casse ou d'espaces ne crée pas un doublon de compte."""
    return email.strip().lower()


def slugify(name: str) -> str:
    """Identifiant lisible d'une organisation, utilisé dans les URL et les
    préfixes de stockage."""
    import unicodedata

    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in ascii_name)
    return "-".join(part for part in cleaned.split("-") if part) or "organisation"
