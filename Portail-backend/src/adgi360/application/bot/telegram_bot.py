"""Cas d'usage du bot Telegram.

Le bot est un deuxième point d'entrée vers le portail, pensé pour les
gestionnaires de comptes en déplacement : lancer un rapport, suivre son état,
recevoir le PowerPoint dans la conversation.

Deux principes :

1. **Le backend ne fait pas confiance à n8n pour l'identité.** n8n vérifie
   déjà l'utilisateur (sous-workflow « Vérifier l'utilisateur »), mais chaque
   cas d'usage ci-dessous résout à nouveau le compte à partir de l'identifiant
   Telegram. Un workflow mal branché ne peut donc pas lire les données d'une
   autre agence.

2. **Les refus métier ne sont pas des erreurs techniques.** « Client
   introuvable » ou « numéro non inscrit » renvoient une réponse normale avec
   `ok: false` et un message prêt à afficher. Seules les vraies pannes (base,
   stockage, n8n) lèvent une exception : ce sont elles que n8n doit
   retenter, et qu'il ne faut pas retenter pour une faute de frappe.
"""

import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.application.auto_review.use_cases.launch_auto_review import (
    LaunchAutoReviewUseCase,
)
from adgi360.domain.accounts.entities import normalize_phone
from adgi360.domain.auto_review.entities import ReviewStatus
from adgi360.infrastructure.config.settings import settings
from adgi360.infrastructure.db.models import (
    ClientModel,
    DataFileModel,
    OrganizationModel,
    ReviewRequestModel,
    UserModel,
)
from adgi360.infrastructure.n8n.client import N8nClient
from adgi360.infrastructure.storage.client import FileStorage
from adgi360.shared.exceptions import ValidationError

# Le lien remis à n8n ne sert qu'à récupérer le fichier pour l'envoyer dans
# Telegram : quelques minutes suffisent.
DOWNLOAD_URL_TTL_SECONDS = 10 * 60

STATUS_ICONS = {
    ReviewStatus.PENDING.value: "⏳",
    ReviewStatus.PROCESSING.value: "⚙️",
    ReviewStatus.AWAITING_APPROVAL.value: "📝",
    ReviewStatus.APPROVED.value: "✅",
    ReviewStatus.FAILED.value: "❌",
}


@dataclass
class BotReply:
    ok: bool
    message: str
    data: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "message": self.message, **self.data}


def _fold(text: str) -> str:
    """Forme de comparaison des noms : sans accents, sans casse, sans ponctuation.
    « maison boreale » doit trouver « Maison Boréale »."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in ascii_text).split())


NOT_LINKED = BotReply(
    False,
    "Ce compte Telegram n'est lié à aucun utilisateur du portail. "
    "Envoyez /start puis partagez votre numéro.",
    {"reason": "not_linked"},
)


class TelegramBotService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------ identité
    async def _user_by_telegram(self, telegram_user_id: int) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(
                UserModel.telegram_user_id == telegram_user_id, UserModel.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def _identity(self, user: UserModel) -> dict:
        organization = await self._session.get(OrganizationModel, user.organization_id)
        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "role": user.role,
            "organization_id": user.organization_id,
            "organization_name": organization.name if organization else "",
        }

    async def link(self, telegram_user_id: int, contact_user_id: int | None, phone: str) -> BotReply:
        """Lie un compte Telegram au compte portail qui porte le même numéro.

        Le contrôle `contact_user_id == telegram_user_id` empêche d'usurper un
        collègue en transférant sa fiche contact : Telegram n'indique ce champ
        que pour le contact de l'expéditeur lui-même.
        """
        if contact_user_id != telegram_user_id:
            return BotReply(
                False,
                "Pour des raisons de sécurité, utilisez le bouton « Partager mon numéro » : "
                "le contact d'une autre personne n'est pas accepté.",
                {"reason": "foreign_contact"},
            )
        try:
            normalized = normalize_phone(phone)
        except ValueError:
            return BotReply(False, "Numéro de téléphone illisible.", {"reason": "invalid_phone"})

        result = await self._session.execute(select(UserModel).where(UserModel.phone == normalized))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return BotReply(
                False,
                f"Le numéro {normalized} n'est inscrit dans aucune agence Digital 360. "
                "Ajoutez-le dans le portail (Mon agence → Bot Telegram) ou contactez "
                "votre administrateur.",
                {"reason": "unknown_phone", "phone": normalized},
            )

        if user.telegram_user_id not in (None, telegram_user_id):
            return BotReply(
                False,
                "Ce numéro est déjà lié à un autre compte Telegram. Déliez-le depuis le "
                "portail avant de recommencer.",
                {"reason": "already_linked"},
            )

        # Un même compte Telegram ne peut représenter qu'un utilisateur.
        previous = await self._user_by_telegram(telegram_user_id)
        if previous is not None and previous.id != user.id:
            previous.telegram_user_id = None
            previous.telegram_linked_at = None
            await self._session.flush()

        user.telegram_user_id = telegram_user_id
        user.telegram_linked_at = datetime.now(UTC)
        await self._session.commit()
        identity = await self._identity(user)
        return BotReply(
            True,
            f"✅ Compte lié : {user.full_name} — {identity['organization_name']}.\n"
            "Essayez /clients ou /rapport <client>.",
            identity,
        )

    # ------------------------------------------------------------- clients
    async def list_clients(self, telegram_user_id: int) -> BotReply:
        user = await self._user_by_telegram(telegram_user_id)
        if user is None:
            return NOT_LINKED
        clients = await self._clients_of(user.organization_id)
        if not clients:
            return BotReply(True, "Aucun client dans votre agence pour l'instant.", {"clients": []})

        items = []
        for client in clients:
            latest = await self._latest_xlsx_period(client.id)
            items.append({"id": client.id, "name": client.name, "latest_period": latest})
        lines = [
            f"• {c['name']}" + (f" — données {c['latest_period']}" if c["latest_period"] else " — aucun export .xlsx")
            for c in items
        ]
        return BotReply(True, "📁 Vos clients :\n" + "\n".join(lines), {"clients": items})

    async def _clients_of(self, organization_id: str) -> list[ClientModel]:
        result = await self._session.execute(
            select(ClientModel)
            .where(ClientModel.organization_id == organization_id)
            .order_by(ClientModel.name)
        )
        return list(result.scalars().all())

    async def _latest_xlsx_period(self, client_id: str) -> str | None:
        result = await self._session.execute(
            select(DataFileModel)
            .where(DataFileModel.client_id == client_id)
            .order_by(DataFileModel.uploaded_at.desc())
        )
        for f in result.scalars().all():
            if f.filename.lower().endswith(".xlsx"):
                return f.period
        return None

    def _match_client(self, clients: list[ClientModel], query: str) -> list[ClientModel]:
        wanted = _fold(query)
        if not wanted:
            return []
        exact = [c for c in clients if _fold(c.name) == wanted]
        if exact:
            return exact
        return [c for c in clients if wanted in _fold(c.name) or _fold(c.name) in wanted]

    # ------------------------------------------------------------- rapports
    async def launch_review(
        self,
        telegram_user_id: int,
        chat_id: int,
        client_query: str,
        period: str | None,
        instructions: str | None,
        n8n: N8nClient,
        storage: FileStorage,
    ) -> BotReply:
        user = await self._user_by_telegram(telegram_user_id)
        if user is None:
            return NOT_LINKED

        clients = await self._clients_of(user.organization_id)
        matches = self._match_client(clients, client_query or "")
        if not matches:
            names = ", ".join(c.name for c in clients) or "aucun"
            return BotReply(
                False,
                f"Je ne trouve pas le client « {client_query} ». Vos clients : {names}.",
                {"reason": "client_not_found"},
            )
        if len(matches) > 1:
            names = ", ".join(c.name for c in matches)
            return BotReply(
                False,
                f"Plusieurs clients correspondent à « {client_query} » : {names}. Précisez le nom.",
                {"reason": "client_ambiguous"},
            )
        client = matches[0]

        result = await self._session.execute(
            select(DataFileModel)
            .where(
                DataFileModel.organization_id == user.organization_id,
                DataFileModel.client_id == client.id,
            )
            .order_by(DataFileModel.uploaded_at.desc())
        )
        xlsx = [f for f in result.scalars().all() if f.filename.lower().endswith(".xlsx")]
        if not xlsx:
            return BotReply(
                False,
                f"Aucun export Excel (.xlsx) n'a été déposé pour {client.name}. "
                "Déposez-le dans le portail, onglet Données.",
                {"reason": "no_data"},
            )
        chosen_period = period.strip() if period and period.strip() else xlsx[0].period
        files = [f for f in xlsx if f.period == chosen_period]
        if not files:
            periods = ", ".join(sorted({f.period for f in xlsx}, reverse=True))
            return BotReply(
                False,
                f"Pas de données {chosen_period} pour {client.name}. Périodes disponibles : {periods}.",
                {"reason": "period_not_found"},
            )

        # Même cas d'usage que le portail : mêmes contrôles, même contrat n8n.
        try:
            review = await LaunchAutoReviewUseCase(self._session, n8n, storage).execute(
                organization_id=user.organization_id,
                client_id=client.id,
                client_type=client.client_type or "other",
                data_file_ids=[f.id for f in files],
                additional_info=instructions,
                notify_telegram_chat_id=chat_id,
            )
        except ValidationError as exc:
            return BotReply(False, str(exc), {"reason": "invalid"})

        return BotReply(
            True,
            f"🚀 Rapport lancé pour {client.name} ({chosen_period}, "
            f"{len(files)} fichier{'s' if len(files) > 1 else ''}).\n"
            "L'analyse prend quelques minutes : je vous envoie le PowerPoint ici dès qu'il est prêt.",
            {
                "review_id": review.id,
                "client_name": client.name,
                "period": chosen_period,
                "files": [f.filename for f in files],
            },
        )

    async def recent_reviews(self, telegram_user_id: int, limit: int = 5) -> BotReply:
        user = await self._user_by_telegram(telegram_user_id)
        if user is None:
            return NOT_LINKED
        result = await self._session.execute(
            select(ReviewRequestModel, ClientModel)
            .join(ClientModel, ReviewRequestModel.client_id == ClientModel.id)
            .where(ReviewRequestModel.organization_id == user.organization_id)
            .order_by(ReviewRequestModel.created_at.desc())
            .limit(max(1, min(limit, 20)))
        )
        rows = result.all()
        if not rows:
            return BotReply(True, "Aucun rapport pour l'instant. Lancez-en un avec /rapport <client>.", {"reviews": []})
        items, lines = [], []
        for review, client in rows:
            status = ReviewStatus(review.status)
            when = review.created_at.strftime("%d/%m %H:%M") if review.created_at else ""
            items.append(
                {"id": review.id, "client_name": client.name, "status": status.value, "created_at": when}
            )
            lines.append(f"{STATUS_ICONS.get(status.value, '•')} {client.name} — {status.label} ({when})")
        return BotReply(True, "📊 Derniers rapports :\n" + "\n".join(lines), {"reviews": items})

    async def report_download(
        self, telegram_user_id: int, review_id: str, storage: FileStorage
    ) -> BotReply:
        """Lien temporaire vers le PowerPoint, signé pour n8n qui l'envoie dans Telegram."""
        user = await self._user_by_telegram(telegram_user_id)
        if user is None:
            return NOT_LINKED
        review = await self._session.get(ReviewRequestModel, review_id)
        if review is None or review.organization_id != user.organization_id:
            return BotReply(False, "Rapport introuvable.", {"reason": "not_found"})
        if not review.report_storage_key:
            return BotReply(False, "Le rapport n'est pas encore prêt.", {"reason": "not_ready"})
        url = await storage.presigned_url(
            review.report_storage_key,
            expires_in=DOWNLOAD_URL_TTL_SECONDS,
            endpoint_url=settings.s3_n8n_endpoint_url,
        )
        return BotReply(
            True,
            "Rapport prêt.",
            {"url": url, "filename": review.report_filename or "rapport.pptx", "status": review.status},
        )
