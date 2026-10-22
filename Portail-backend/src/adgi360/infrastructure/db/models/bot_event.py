import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adgi360.infrastructure.db.base import Base


class BotEventModel(Base):
    """Journal des messages reçus par le bot Telegram.

    Écrit directement par n8n (nœud Postgres du sous-workflow « Vérifier
    l'utilisateur »), lu par l'équipe en cas de litige : qui a demandé quel
    rapport, depuis quel compte Telegram, et si l'accès a été accordé. C'est la
    trace d'accès attendue par la Loi 25 dès qu'un canal externe touche aux
    données des clients.

    Pas de clé étrangère sur `user_id` : un message refusé (inconnu) doit
    aussi être journalisé, et la suppression d'un compte ne doit pas effacer
    l'historique des accès.
    """

    __tablename__ = "bot_events"
    # Idempotence : Telegram peut renvoyer la même mise à jour (réseau lent,
    # webhook en échec). n8n insère avec ON CONFLICT DO NOTHING et s'arrête
    # si la ligne existait déjà. Plusieurs NULL restent permis.
    __table_args__ = (Index("uq_bot_events_update_id", "update_id", unique=True),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # « accepted », « unknown_user », « linked », « link_refused »…
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Identifiant de la mise à jour Telegram (update_id), unique.
    update_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
