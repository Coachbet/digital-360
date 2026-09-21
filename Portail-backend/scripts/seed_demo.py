"""Crée un environnement de démonstration complet dans la base locale.

Usage depuis Portail-backend :
    python scripts/seed_demo.py

Le script est idempotent et ne touche qu'au compte test@adigi360.com.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from adgi360.application.auto_review.use_cases.approve_review import ApproveReviewUseCase
from adgi360.application.auto_review.use_cases.render_report import RenderReportUseCase
from adgi360.application.invoicing.use_cases.create_invoice import CreateInvoiceUseCase
from adgi360.domain.accounts.entities import UserRole
from adgi360.domain.auto_review.entities import ReviewStatus
from adgi360.domain.data.entities import build_storage_key
from adgi360.infrastructure.config.settings import settings
from adgi360.infrastructure.db.models import (
    CalendarEventModel,
    ClientModel,
    DataFileModel,
    InvoiceModel,
    OrganizationModel,
    ReviewRequestModel,
    UserModel,
)
from adgi360.infrastructure.db.session import AsyncSessionLocal, init_db
from adgi360.infrastructure.security import hash_password
from adgi360.infrastructure.storage.client import FileStorage

EMAIL = "test@adigi360.com"
PASSWORD = "Adgi360-Test-2026!"
MARKER = "[DEMO ADGI360]"

CLIENTS = [
    ("Maison Boréale", "ecommerce", "marketing@maison-boreale.example"),
    ("Nordik SaaS", "b2b", "growth@nordik-saas.example"),
    ("Café Saint-Laurent", "local", "bonjour@cafe-saint-laurent.example"),
]

FILES = {
    "Maison Boréale": [
        (
            "2026-08",
            "meta-ads-aout.csv",
            (
                "date,campagne,depenses,impressions,clics,conversions,revenus\n"
                "2026-08-01,Collection automne,420.50,38200,984,76,6240.00\n"
                "2026-08-15,Retargeting paniers,215.20,17400,612,51,4385.00\n"
            ),
        ),
        (
            "2026-08",
            "shopify-commandes-aout.csv",
            (
                "date,commandes,revenus,panier_moyen,nouveaux_clients\n"
                "2026-08-01,84,7135.00,84.94,57\n"
                "2026-08-15,96,8290.00,86.35,64\n"
            ),
        ),
        (
            "2026-07",
            "google-analytics-juillet.csv",
            (
                "canal,sessions,utilisateurs,taux_conversion\n"
                "Organic Search,12540,9820,2.7\n"
                "Paid Social,8940,7110,4.1\n"
                "Email,3210,2840,5.8\n"
            ),
        ),
    ],
    "Nordik SaaS": [
        (
            "2026-08",
            "google-ads-leads.csv",
            (
                "campagne,depenses,impressions,clics,leads,cpl\n"
                "Demo produit,1850.00,64200,2180,94,19.68\n"
                "Livre blanc,920.00,38100,1405,121,7.60\n"
            ),
        ),
        (
            "2026-08",
            "crm-pipeline.csv",
            (
                "source,leads,mql,opportunites,revenu_pipeline\n"
                "Google Ads,215,82,31,186000\n"
                "LinkedIn,74,38,19,142000\n"
            ),
        ),
    ],
    "Café Saint-Laurent": [
        (
            "2026-08",
            "instagram-insights.csv",
            (
                "publication,portee,interactions,enregistrements,visites_profil\n"
                "Nouveau brunch,18400,1342,286,719\n"
                "Terrasse ete,12600,984,192,488\n"
            ),
        ),
    ],
}


def ensure_local_database() -> None:
    url = settings.database_url.lower()
    if not any(host in url for host in ("localhost", "127.0.0.1", "@postgres:")):
        raise RuntimeError("Seed refusé : DATABASE_URL ne désigne pas la base locale")


async def seed() -> None:
    ensure_local_database()
    await init_db()
    storage = FileStorage()
    await storage.ensure_bucket()

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.email == EMAIL))
        ).scalar_one_or_none()
        if user:
            organization = await session.get(OrganizationModel, user.organization_id)
        else:
            organization = None

        if organization is None:
            organization = OrganizationModel(
                name="ADGI360 Test", slug="adgi360-test", legal_name="ADGI360 Test"
            )
            session.add(organization)
            await session.flush()
        organization.legal_name = "ADGI360 Démonstration"
        organization.tagline = "La donnée marketing, rendue claire."
        organization.address = "123 avenue de la Démonstration, Montréal, QC"
        organization.phone = "+1 514 555 0100"
        organization.email = "finance@adigi360.com"
        organization.website = "https://adigi360.com"
        organization.tax_number_1 = "DEMO-TPS-123456"
        organization.tax_number_2 = "DEMO-TVQ-987654"
        organization.registration_number = "DEMO-NEQ-0000000000"
        organization.payment_terms = "Paiement à 30 jours — coordonnées de démonstration."
        organization.payment_details = "Virement bancaire — compte de démonstration uniquement."

        if user is None:
            user = UserModel(
                organization_id=organization.id,
                email=EMAIL,
                hashed_password=hash_password(PASSWORD),
                full_name="Compte Test",
                role=UserRole.OWNER.value,
                is_active=True,
            )
            session.add(user)
        await session.commit()

        clients: dict[str, ClientModel] = {}
        for name, client_type, contact_email in CLIENTS:
            client = (
                await session.execute(
                    select(ClientModel).where(
                        ClientModel.organization_id == organization.id,
                        ClientModel.name == name,
                    )
                )
            ).scalar_one_or_none()
            if client is None:
                client = ClientModel(
                    organization_id=organization.id,
                    name=name,
                    client_type=client_type,
                    contact_email=contact_email,
                )
                session.add(client)
                await session.flush()
            clients[name] = client
        await session.commit()

        files_by_client: dict[str, list[DataFileModel]] = {name: [] for name in clients}
        for client_name, definitions in FILES.items():
            client = clients[client_name]
            for period, filename, csv_content in definitions:
                existing = (
                    await session.execute(
                        select(DataFileModel).where(
                            DataFileModel.organization_id == organization.id,
                            DataFileModel.client_id == client.id,
                            DataFileModel.period == period,
                            DataFileModel.filename == filename,
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    content = csv_content.encode("utf-8")
                    key = build_storage_key(organization.id, client.id, period, filename)
                    await storage.upload(key, content, "text/csv")
                    existing = DataFileModel(
                        organization_id=organization.id,
                        client_id=client.id,
                        period=period,
                        filename=filename,
                        storage_key=key,
                        content_type="text/csv",
                        size_bytes=len(content),
                    )
                    session.add(existing)
                    await session.flush()
                files_by_client[client_name].append(existing)
        await session.commit()

        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        event_definitions = [
            ("Lancement campagne Automne", 1, 3, "campaign", "Maison Boréale"),
            ("Point performance mensuel", 2, 1, "client_meeting", "Nordik SaaS"),
            ("Rapport mensuel à livrer", 4, 1, "report_deadline", "Maison Boréale"),
            ("Planification éditoriale", 7, 2, "internal", "Café Saint-Laurent"),
        ]
        for title, day_offset, duration, category, client_name in event_definitions:
            description = f"{MARKER} Événement de démonstration"
            exists = (
                await session.execute(
                    select(CalendarEventModel).where(
                        CalendarEventModel.organization_id == organization.id,
                        CalendarEventModel.title == title,
                        CalendarEventModel.description == description,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                start_at = now + timedelta(days=day_offset)
                session.add(
                    CalendarEventModel(
                        organization_id=organization.id,
                        client_id=clients[client_name].id,
                        title=title,
                        description=description,
                        start_at=start_at,
                        end_at=start_at + timedelta(hours=duration),
                        category=category,
                    )
                )
        await session.commit()

        deck = {
            "title": "Rapport de performance — Maison Boréale",
            "subtitle": "Août 2026",
            "slides": [
                {
                    "layout": "kpis",
                    "title": "Chiffres clés",
                    "kpis": [
                        {"label": "ROAS", "value": "5,1x", "delta": "+0,8"},
                        {"label": "Conversions", "value": "127", "delta": "+18 %"},
                        {"label": "CPC", "value": "0,40 $", "delta": "-9 %"},
                    ],
                },
                {
                    "layout": "bullets",
                    "title": "Analyse",
                    "bullets": [
                        "Le retargeting génère le meilleur retour sur dépenses.",
                        "La campagne Collection automne élargit efficacement l'audience.",
                        "L'email demeure le canal au meilleur taux de conversion.",
                    ],
                },
                {
                    "layout": "recommendations",
                    "title": "Recommandations",
                    "items": [
                        {
                            "title": "Renforcer le retargeting",
                            "detail": "Augmenter progressivement le budget sur les paniers abandonnés.",
                        },
                        {
                            "title": "Tester trois créations",
                            "detail": "Comparer produit, usage et témoignage client.",
                        },
                    ],
                },
            ],
        }

        async def ensure_review(marker: str, approved: bool = False) -> None:
            review = (
                await session.execute(
                    select(ReviewRequestModel).where(
                        ReviewRequestModel.organization_id == organization.id,
                        ReviewRequestModel.additional_info == marker,
                    )
                )
            ).scalar_one_or_none()
            if review is None:
                sources = files_by_client["Maison Boréale"][:2]
                review = ReviewRequestModel(
                    organization_id=organization.id,
                    client_id=clients["Maison Boréale"].id,
                    client_type="ecommerce",
                    data_file_ids=[item.id for item in sources],
                    additional_info=marker,
                    status=ReviewStatus.PROCESSING.value,
                )
                session.add(review)
                await session.commit()
                await session.refresh(review)
            if not review.report_storage_key:
                review = await RenderReportUseCase(session, storage).execute(review.id, deck)
            if approved and review.status == ReviewStatus.AWAITING_APPROVAL.value:
                await ApproveReviewUseCase(session).execute(review.id)

        await ensure_review(f"{MARKER} Rapport à relire")
        await ensure_review(f"{MARKER} Rapport approuvé", approved=True)

        failed_marker = f"{MARKER} Rapport en échec"
        failed = (
            await session.execute(
                select(ReviewRequestModel).where(
                    ReviewRequestModel.organization_id == organization.id,
                    ReviewRequestModel.additional_info == failed_marker,
                )
            )
        ).scalar_one_or_none()
        if failed is None:
            failed = ReviewRequestModel(
                organization_id=organization.id,
                client_id=clients["Nordik SaaS"].id,
                client_type="b2b",
                data_file_ids=[item.id for item in files_by_client["Nordik SaaS"]],
                additional_info=failed_marker,
                status=ReviewStatus.FAILED.value,
                error_message="Erreur simulée pour tester l'affichage et la relance.",
            )
            session.add(failed)
            await session.commit()

        invoice_use_case = CreateInvoiceUseCase(session, storage)
        invoice_definitions = [
            (
                f"{MARKER} Facture en attente",
                "Maison Boréale",
                "CAD",
                "qc_gst_qst",
                [
                    {"description": "Gestion Meta Ads — août", "quantity": "1", "unit_price": "1800"},
                    {"description": "Création de contenus", "quantity": "6", "unit_price": "175"},
                ],
                "issued",
            ),
            (
                f"{MARKER} Facture payée",
                "Nordik SaaS",
                "EUR",
                "eu_vat_20",
                [
                    {"description": "Pilotage Google Ads", "quantity": "1", "unit_price": "2200"},
                    {"description": "Rapport stratégique", "quantity": "1", "unit_price": "650"},
                ],
                "paid",
            ),
        ]
        for marker, client_name, currency, tax_regime, lines, final_status in invoice_definitions:
            invoice = (
                await session.execute(
                    select(InvoiceModel).where(
                        InvoiceModel.organization_id == organization.id,
                        InvoiceModel.notes == marker,
                    )
                )
            ).scalar_one_or_none()
            if invoice is None:
                client = clients[client_name]
                invoice = await invoice_use_case.execute(
                    organization_id=organization.id,
                    client_id=client.id,
                    client_name=client.name,
                    client_address="Adresse client de démonstration",
                    client_email=client.contact_email,
                    lines=lines,
                    issue_date=now.date() - timedelta(days=15),
                    due_date=now.date() + timedelta(days=15),
                    currency=currency,
                    tax_regime=tax_regime,
                    discount=Decimal(100),
                    notes=marker,
                )
            if invoice.status != final_status:
                invoice.status = final_status
                await session.commit()

        counts = {}
        for label, model in (
            ("clients", ClientModel),
            ("fichiers", DataFileModel),
            ("événements", CalendarEventModel),
            ("rapports", ReviewRequestModel),
            ("factures", InvoiceModel),
        ):
            rows = await session.execute(
                select(model).where(model.organization_id == organization.id)
            )
            counts[label] = len(rows.scalars().all())

    print("Jeu de démonstration prêt :")
    print("  " + " · ".join(f"{value} {label}" for label, value in counts.items()))
    print(f"  Connexion : {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
