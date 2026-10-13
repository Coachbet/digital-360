from pydantic import BaseModel, Field


class BotLinkRequest(BaseModel):
    telegram_user_id: int
    # Champ `contact.user_id` envoyé par Telegram avec le contact partagé.
    contact_user_id: int | None = None
    phone: str = Field(max_length=40)


class BotReviewRequest(BaseModel):
    telegram_user_id: int
    chat_id: int
    client: str = Field(default="", max_length=200)
    period: str | None = Field(default=None, max_length=50)
    instructions: str | None = Field(default=None, max_length=2000)
