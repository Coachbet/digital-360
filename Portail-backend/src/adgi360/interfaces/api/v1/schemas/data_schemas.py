from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DataFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    period: str
    filename: str
    storage_key: str
    content_type: str | None
    size_bytes: int | None
    uploaded_at: datetime


class PeriodOut(BaseModel):
    """Une période pour un client donné, avec le nombre de fichiers qu'elle contient."""

    period: str
    file_count: int


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int
