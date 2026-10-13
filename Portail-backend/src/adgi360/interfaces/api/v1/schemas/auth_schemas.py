from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    # 10 caractères minimum : un seuil qui écarte les mots de passe triviaux
    # sans imposer de règles de composition, qui poussent surtout à les noter.
    password: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    phone: str | None = None
    telegram_linked: bool = False
    created_at: datetime


class OrganizationOut(BaseModel):
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


class MeOut(BaseModel):
    user: UserOut
    organization: OrganizationOut


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    organization: OrganizationOut


class PhoneUpdate(BaseModel):
    """Numéro professionnel utilisé pour lier le bot Telegram. None = retirer."""

    phone: str | None = Field(default=None, max_length=40)
