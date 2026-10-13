"""Bot Telegram : liaison par numéro, cloisonnement des agences, lancement."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from adgi360.application.bot.telegram_bot import TelegramBotService
from adgi360.domain.accounts.entities import normalize_phone
from adgi360.infrastructure.db.base import Base
from adgi360.infrastructure.db.models import (
    ClientModel,
    DataFileModel,
    OrganizationModel,
    ReviewRequestModel,
    UserModel,
)

TG_ALICE = 111
TG_BOB = 222


@pytest.mark.parametrize(
    "raw",
    ["(514) 555-1234", "514-555-1234", "15145551234", "+1 514 555 1234", "+15145551234"],
)
def test_normalize_phone_north_american_forms(raw):
    assert normalize_phone(raw) == "+15145551234"


def test_normalize_phone_international_and_invalid():
    assert normalize_phone("+33 6 12 34 56 78") == "+33612345678"
    assert normalize_phone("0033612345678") == "+33612345678"
    with pytest.raises(ValueError):
        normalize_phone("1234")


def run(coro_factory):
    """Base SQLite en mémoire, neuve pour chaque test."""

    async def main():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            org_a = OrganizationModel(id="org-a", name="Agence A", slug="a")
            org_b = OrganizationModel(id="org-b", name="Agence B", slug="b")
            alice = UserModel(id="alice", organization_id="org-a", email="a@a.test",
                              hashed_password="x", full_name="Alice", phone="+15145551234")
            bob = UserModel(id="bob", organization_id="org-b", email="b@b.test",
                            hashed_password="x", full_name="Bob", phone="+15145559999",
                            telegram_user_id=TG_BOB)
            client = ClientModel(id="c1", organization_id="org-a", name="Maison Boréale",
                                 client_type="ecommerce")
            other = ClientModel(id="c2", organization_id="org-b", name="Nordik SaaS")
            session.add_all([org_a, org_b, alice, bob, client, other])
            await session.commit()
            try:
                return await coro_factory(session)
            finally:
                await engine.dispose()

    return asyncio.run(main())


def test_link_refuses_unknown_phone():
    reply = run(lambda s: TelegramBotService(s).link(TG_ALICE, TG_ALICE, "514 000 0000"))
    assert not reply.ok and reply.data["reason"] == "unknown_phone"


def test_link_refuses_forwarded_contact():
    # Quelqu'un transfère la fiche contact d'Alice : contact.user_id ≠ expéditeur.
    reply = run(lambda s: TelegramBotService(s).link(999, TG_ALICE, "+15145551234"))
    assert not reply.ok and reply.data["reason"] == "foreign_contact"


def test_link_success_then_recognised():
    async def scenario(s):
        service = TelegramBotService(s)
        linked = await service.link(TG_ALICE, TG_ALICE, "15145551234")
        clients = await service.list_clients(TG_ALICE)
        return linked, clients

    linked, clients = run(scenario)
    assert linked.ok and linked.data["organization_name"] == "Agence A"
    names = [c["name"] for c in clients.data["clients"]]
    assert names == ["Maison Boréale"]  # jamais les clients de l'agence B


def test_phone_already_linked_to_other_telegram():
    reply = run(lambda s: TelegramBotService(s).link(333, 333, "+15145559999"))
    assert not reply.ok and reply.data["reason"] == "already_linked"


def test_unlinked_account_is_refused():
    reply = run(lambda s: TelegramBotService(s).recent_reviews(TG_ALICE))
    assert not reply.ok and reply.data["reason"] == "not_linked"


def _mocks():
    n8n = SimpleNamespace(trigger_auto_review=AsyncMock())
    storage = SimpleNamespace(presigned_url=AsyncMock(return_value="http://minio/signed"))
    return n8n, storage


def test_launch_review_matches_client_without_accents_and_notifies_chat():
    n8n, storage = _mocks()

    async def scenario(s):
        s.add_all([
            DataFileModel(organization_id="org-a", client_id="c1", period="2026-09",
                          filename="export.xlsx", storage_key="k1"),
            DataFileModel(organization_id="org-a", client_id="c1", period="2026-09",
                          filename="notes.csv", storage_key="k2"),
        ])
        await s.commit()
        service = TelegramBotService(s)
        await service.link(TG_ALICE, TG_ALICE, "+15145551234")
        return await service.launch_review(TG_ALICE, TG_ALICE, "maison boreale", None, None,
                                           n8n, storage)

    reply = run(scenario)
    assert reply.ok, reply.message
    assert reply.data["period"] == "2026-09" and reply.data["files"] == ["export.xlsx"]
    payload = n8n.trigger_auto_review.await_args.args[0]
    assert payload["notify"] == {"telegram_chat_id": TG_ALICE}
    assert "/fail?token=" in payload["fail_callback_url"]


def test_cannot_launch_on_other_agency_client():
    n8n, storage = _mocks()
    reply = run(lambda s: TelegramBotService(s).launch_review(
        TG_BOB, TG_BOB, "Maison Boréale", None, None, n8n, storage))
    assert not reply.ok and reply.data["reason"] == "client_not_found"
    n8n.trigger_auto_review.assert_not_awaited()


def test_launch_without_xlsx_is_explained():
    n8n, storage = _mocks()

    async def scenario(s):
        await TelegramBotService(s).link(TG_ALICE, TG_ALICE, "+15145551234")
        return await TelegramBotService(s).launch_review(
            TG_ALICE, TG_ALICE, "Maison", None, None, n8n, storage)

    reply = run(scenario)
    assert not reply.ok and reply.data["reason"] == "no_data"


def test_download_is_scoped_to_agency():
    _, storage = _mocks()

    async def scenario(s):
        s.add(ReviewRequestModel(id="r1", organization_id="org-a", client_id="c1",
                                 client_type="other", status="awaiting_approval",
                                 report_storage_key="reports/r1.pptx"))
        await s.commit()
        return await TelegramBotService(s).report_download(TG_BOB, "r1", storage)

    reply = run(scenario)
    assert not reply.ok and reply.data["reason"] == "not_found"
    storage.presigned_url.assert_not_awaited()


def test_clients_list_periods_newest_first_and_launch_by_button():
    n8n, storage = _mocks()

    async def scenario(s):
        from datetime import datetime, timedelta
        now = datetime.now()
        s.add_all([
            DataFileModel(organization_id="org-a", client_id="c1", period="2026-08",
                          filename="aout.xlsx", storage_key="k1", uploaded_at=now - timedelta(days=30)),
            DataFileModel(organization_id="org-a", client_id="c1", period="2026-09",
                          filename="sept.xlsx", storage_key="k2", uploaded_at=now),
        ])
        await s.commit()
        service = TelegramBotService(s)
        await service.link(TG_ALICE, TG_ALICE, "+15145551234")
        listing = await service.list_clients(TG_ALICE)
        launched = await service.launch_review(TG_ALICE, TG_ALICE, "", "2026-08", None,
                                               n8n, storage, client_id="c1")
        return listing, launched

    listing, launched = run(scenario)
    assert listing.data["clients"][0]["periods"] == ["2026-09", "2026-08"]
    assert launched.ok and launched.data["period"] == "2026-08"
    assert launched.data["files"] == ["aout.xlsx"]


def test_button_with_other_agency_client_id_is_refused():
    n8n, storage = _mocks()
    reply = run(lambda s: TelegramBotService(s).launch_review(
        TG_BOB, TG_BOB, "", None, None, n8n, storage, client_id="c1"))
    assert not reply.ok and reply.data["reason"] == "client_not_found"
    n8n.trigger_auto_review.assert_not_awaited()
