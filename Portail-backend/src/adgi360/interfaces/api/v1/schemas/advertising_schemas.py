from pydantic import BaseModel, Field


class CredentialFieldOut(BaseModel):
    key: str
    label: str
    required: bool = True
    secret: bool = True
    placeholder: str = ""
    help: str = ""


class AdvertisingPlatformOut(BaseModel):
    value: str
    label: str
    description: str
    credential_fields: list[CredentialFieldOut]


class PlatformConnectionUpdate(BaseModel):
    client_id: str = Field(min_length=1, max_length=36)
    account_id: str = Field(min_length=1, max_length=200)
    credentials: dict[str, str] = Field(default_factory=dict)


class PlatformConnectionOut(BaseModel):
    platform: str
    label: str
    connected: bool
    client_id: str
    account_id: str
    configured_fields: list[str] = Field(default_factory=list)


class AdvertisingConnectionUpdate(BaseModel):
    client_id: str = Field(min_length=1, max_length=36)
    meta_ad_account_id: str = Field(min_length=2, max_length=100)
    instagram_user_id: str = Field(min_length=2, max_length=100)
    meta_access_token: str | None = Field(default=None, min_length=10, max_length=4000)
    instagram_access_token: str | None = Field(default=None, min_length=10, max_length=4000)


class AdvertisingConnectionOut(BaseModel):
    connected: bool
    client_id: str | None = None
    meta_ad_account_id: str | None = None
    instagram_user_id: str | None = None
    has_meta_token: bool = False
    has_instagram_token: bool = False


class AdvertisingKpisOut(BaseModel):
    date_preset: str
    currency: str | None = None
    spend: float = 0
    impressions: int = 0
    reach: int = 0
    clicks: int = 0
    ctr: float = 0
    cpc: float = 0
    cpm: float = 0
    conversions: float = 0
    purchase_roas: float = 0


class InstagramPostOut(BaseModel):
    id: str
    message: str = "Publication envoyée sur Instagram"
