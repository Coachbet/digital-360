from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    start_at: datetime
    end_at: datetime
    category: str = "internal"
    description: str | None = None
    client_id: str | None = None


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    category: str
    client_id: str | None
    source: str = "internal"


class CategoryOut(BaseModel):
    value: str
    label: str
