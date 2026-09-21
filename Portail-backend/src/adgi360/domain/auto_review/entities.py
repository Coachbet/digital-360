from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ClientType(str, Enum):
    """Liste fixe des types de clients proposés dans le formulaire d'auto-review.

    Ces valeurs sont transmises telles quelles à n8n, qui adapte le ton et le
    contenu du rapport en fonction. Ajouter une valeur ici la rend disponible
    dans l'UI (le frontend lit la liste via GET /api/v1/auto-review/client-types).
    """

    ECOMMERCE = "ecommerce"
    B2B = "b2b"
    LEAD_GEN = "lead_gen"
    MARKETPLACE = "marketplace"
    LOCAL = "local"
    BRAND = "brand"
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            ClientType.ECOMMERCE: "E-commerce",
            ClientType.B2B: "B2B",
            ClientType.LEAD_GEN: "Génération de leads",
            ClientType.MARKETPLACE: "Marketplace (Amazon, Walmart)",
            ClientType.LOCAL: "Commerce local",
            ClientType.BRAND: "Notoriété / marque",
            ClientType.OTHER: "Autre",
        }[self]


class ReviewStatus(str, Enum):
    """Cycle de vie d'une demande de review automatique.

    Aucun envoi de mail n'intervient : le rapport validé se télécharge depuis le
    portail, et c'est un humain qui décide de la suite.
    """

    PENDING = "pending"                      # créée, pas encore envoyée à n8n
    PROCESSING = "processing"                # n8n a été appelé, analyse en cours
    AWAITING_APPROVAL = "awaiting_approval"  # le PPTX est prêt, en attente de relecture
    APPROVED = "approved"                    # validé par un humain, prêt à être diffusé
    FAILED = "failed"                         # échec de l'appel n8n ou de la génération

    @property
    def label(self) -> str:
        return {
            ReviewStatus.PENDING: "En attente",
            ReviewStatus.PROCESSING: "Génération en cours",
            ReviewStatus.AWAITING_APPROVAL: "À relire",
            ReviewStatus.APPROVED: "Validé",
            ReviewStatus.FAILED: "Échec",
        }[self]


@dataclass
class ReviewRequest:
    """Entité de domaine : une demande de review automatique."""

    id: str
    client_id: str
    client_type: ClientType
    data_file_ids: list[str] = field(default_factory=list)
    additional_info: str | None = None
    status: ReviewStatus = ReviewStatus.PENDING
    report_storage_key: str | None = None
    report_filename: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    approved_at: datetime | None = None

    def can_be_approved(self) -> bool:
        """Un rapport ne peut être validé que s'il a été produit et pas déjà validé."""
        return self.status == ReviewStatus.AWAITING_APPROVAL and self.report_storage_key is not None
