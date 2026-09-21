from pydantic import BaseModel, ConfigDict, Field

HEX = r"^#[0-9A-Fa-f]{6}$"


class OrganizationProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str

    brand_primary: str
    brand_ink: str
    brand_accent: str
    tagline: str | None
    logo_storage_key: str | None
    deck_template_key: str | None

    legal_name: str | None
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    tax_number_1_label: str
    tax_number_1: str | None
    tax_number_2_label: str
    tax_number_2: str | None
    registration_number: str | None
    payment_terms: str | None
    payment_details: str | None


class OrganizationProfileUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs envoyés sont modifiés.

    Les couleurs sont validées au format hexadécimal — une valeur libre casserait
    le rendu des PDF et des decks sans message d'erreur exploitable.
    """

    name: str | None = Field(default=None, min_length=2, max_length=200)
    tagline: str | None = None

    brand_primary: str | None = Field(default=None, pattern=HEX)
    brand_ink: str | None = Field(default=None, pattern=HEX)
    brand_accent: str | None = Field(default=None, pattern=HEX)

    legal_name: str | None = None
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


class BrandingOut(BaseModel):
    name: str
    tagline: str | None
    primary: str
    ink: str
    accent: str
    has_logo: bool
    has_deck_template: bool
