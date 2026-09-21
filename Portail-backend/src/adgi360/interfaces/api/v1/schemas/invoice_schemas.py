from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class InvoiceCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    lines: list[InvoiceLineIn] = Field(min_length=1)
    issue_date: date
    due_date: date | None = None
    client_id: str | None = None
    client_address: str | None = None
    client_email: str | None = None
    currency: str = "CAD"
    tax_regime: str = "qc_gst_qst"
    discount: Decimal = Decimal("0")
    notes: str | None = None
    signature_data_url: str | None = Field(default=None, max_length=3_000_000)


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: str
    client_id: str | None
    client_name: str
    client_address: str | None
    client_email: str | None
    lines: list[dict]
    currency: str
    tax_regime: str
    discount: Decimal
    status: str
    issue_date: date
    due_date: date | None
    notes: str | None
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    pdf_storage_key: str | None
    created_at: datetime


class OptionOut(BaseModel):
    value: str
    label: str


class InvoiceOptionsOut(BaseModel):
    currencies: list[OptionOut]
    tax_regimes: list[OptionOut]
    statuses: list[OptionOut]


class CompanySettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    legal_name: str
    tagline: str
    address: str
    phone: str
    email: str
    website: str
    tax_number_1_label: str
    tax_number_1: str
    tax_number_2_label: str
    tax_number_2: str
    registration_number: str
    payment_terms: str
    payment_details: str
    logo_storage_key: str | None


class CompanySettingsUpdate(BaseModel):
    legal_name: str | None = None
    tagline: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    tax_number_1_label: str | None = None
    tax_number_1: str | None = None
    tax_number_2_label: str | None = None
    tax_number_2: str | None = None
    registration_number: str | None = None
    payment_terms: str | None = None
    payment_details: str | None = None


class InvoiceDownloadOut(BaseModel):
    url: str
    filename: str
    expires_in: int
