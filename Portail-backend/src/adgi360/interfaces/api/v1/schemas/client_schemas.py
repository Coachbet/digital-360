from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_type: str = "other"
    contact_email: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    client_type: str
    contact_email: str | None
    created_at: datetime
