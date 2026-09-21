class AdgiError(Exception):
    """Exception de base pour toutes les erreurs métier du portail."""


class NotFoundError(AdgiError):
    """Ressource demandée introuvable."""


class ValidationError(AdgiError):
    """Données fournies invalides au regard des règles métier."""


class ExternalServiceError(AdgiError):
    """Erreur lors d'un appel à un service externe (n8n, Google, MinIO/S3...)."""
