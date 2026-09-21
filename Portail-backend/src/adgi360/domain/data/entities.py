from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataFile:
    """Entité de domaine : un fichier source déposé pour un client et une période."""

    id: str
    organization_id: str
    client_id: str
    period: str
    filename: str
    storage_key: str
    content_type: str | None = None
    size_bytes: int | None = None
    uploaded_at: datetime | None = None


def build_storage_key(organization_id: str, client_id: str, period: str, filename: str) -> str:
    """Clé de stockage : org/<agence>/clients/<client>/<période>/<fichier>.

    Le préfixe par organisation est délibéré : il rend l'isolation visible dans
    la console MinIO, permet de purger une agence en supprimant un préfixe, et
    ouvrira la porte à des politiques d'accès S3 par agence sans rien changer
    au code applicatif.
    """
    return f"org/{organization_id}/clients/{client_id}/{period}/{filename}"


def build_report_key(organization_id: str, review_id: str, filename: str) -> str:
    """Clé de stockage des rapports générés."""
    return f"org/{organization_id}/reports/{review_id}/{filename}"


def build_invoice_key(organization_id: str, invoice_id: str, number: str) -> str:
    """Clé de stockage des factures PDF."""
    return f"org/{organization_id}/invoices/{invoice_id}/{number}.pdf"


def build_branding_key(organization_id: str, kind: str, filename: str) -> str:
    """Clé de stockage des éléments de marque (logo, gabarit PowerPoint)."""
    return f"org/{organization_id}/branding/{kind}/{filename}"


def build_social_key(organization_id: str, post_id: str, filename: str) -> str:
    """Média temporairement exposé à Meta pendant une publication sociale."""
    return f"org/{organization_id}/social/{post_id}/{filename}"
