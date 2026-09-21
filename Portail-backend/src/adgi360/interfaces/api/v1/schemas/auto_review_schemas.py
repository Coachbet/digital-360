from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientTypeOut(BaseModel):
    """Une option de la liste fixe des types de clients."""

    value: str
    label: str


class AutoReviewCreate(BaseModel):
    client_id: str
    client_type: str = "other"
    data_file_ids: list[str] = Field(default_factory=list)
    selected_platforms: list[str] = Field(default_factory=list)
    additional_info: str | None = None


class RenderReportRequest(BaseModel):
    """Plan du rapport rédigé par l'IA, envoyé par n8n.

    Volontairement permissif : le contenu exact des diapositives est validé et
    complété côté rendu, pour qu'une réponse imparfaite du modèle produise quand
    même un rapport lisible.
    """

    title: str | None = None
    subtitle: str | None = None
    slides: list[dict] = Field(default_factory=list)


class AutoReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    client_type: str
    data_file_ids: list[str]
    additional_info: str | None
    status: str
    error_message: str | None
    report_filename: str | None
    report_storage_key: str | None
    created_at: datetime
    approved_at: datetime | None


class AutoReviewDetailOut(AutoReviewOut):
    """Version enrichie pour l'affichage : infos client et libellé du statut."""

    client_name: str
    status_label: str


class ReportDownloadOut(BaseModel):
    url: str
    filename: str
    expires_in: int


class ReportPreviewOut(ReportDownloadOut):
    mode: str = "pdf"
