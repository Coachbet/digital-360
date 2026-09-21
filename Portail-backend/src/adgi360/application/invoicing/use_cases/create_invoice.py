import base64
import binascii
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.data.entities import build_invoice_key
from adgi360.domain.invoicing.entities import (
    Currency,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    TaxRegime,
    build_invoice_number,
)
from adgi360.infrastructure.db.models import InvoiceModel, OrganizationModel
from adgi360.infrastructure.pdf.invoice_renderer import render_invoice_pdf
from adgi360.infrastructure.storage.client import FileStorage
from adgi360.shared.exceptions import NotFoundError, ValidationError

PLACEHOLDER = "À compléter"


def _decode_signature(data_url: str | None) -> bytes | None:
    if not data_url:
        return None
    try:
        header, encoded = data_url.split(",", 1)
        if header not in {"data:image/png;base64", "data:image/jpeg;base64"}:
            raise ValueError
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValidationError("La signature doit être une image PNG ou JPEG valide") from exc
    if len(content) > 2 * 1024 * 1024:
        raise ValidationError("La signature dépasse 2 Mo")
    return content


class CreateInvoiceUseCase:
    """Crée une facture, calcule les montants, produit le PDF et l'archive.

    Le PDF est généré une seule fois, à l'émission, et stocké : une facture
    émise ne doit plus changer, même si les coordonnées de l'agence ou les taux
    de taxes évoluent ensuite.
    """

    def __init__(self, session: AsyncSession, storage: FileStorage) -> None:
        self._session = session
        self._storage = storage

    async def _next_number(self, organization_id: str, year: int) -> str:
        """Séquence par agence et par année : chaque organisation a sa propre
        numérotation, sans trou ni chevauchement avec les autres."""
        prefix = f"{year}-"
        result = await self._session.execute(
            select(func.count(InvoiceModel.id)).where(
                InvoiceModel.organization_id == organization_id,
                InvoiceModel.number.contains(prefix),
            )
        )
        return build_invoice_number(year, (result.scalar() or 0) + 1)

    async def execute(
        self,
        organization_id: str,
        client_name: str,
        lines: list[dict],
        issue_date: date,
        due_date: date | None = None,
        client_id: str | None = None,
        client_address: str | None = None,
        client_email: str | None = None,
        currency: str = "CAD",
        tax_regime: str = "qc_gst_qst",
        discount: Decimal | float = 0,
        notes: str | None = None,
        signature_data_url: str | None = None,
    ) -> InvoiceModel:
        organization = await self._session.get(OrganizationModel, organization_id)
        if organization is None:
            raise NotFoundError("Organisation introuvable")

        if not lines:
            raise ValidationError("Une facture doit comporter au moins une ligne")

        try:
            resolved_currency = Currency(currency)
            resolved_regime = TaxRegime(tax_regime)
        except ValueError as exc:
            raise ValidationError(f"Devise ou régime de taxes inconnu : {exc}") from exc

        domain_lines = []
        for raw in lines:
            quantity = Decimal(str(raw.get("quantity", 0)))
            unit_price = Decimal(str(raw.get("unit_price", 0)))
            description = (raw.get("description") or "").strip()
            if not description:
                raise ValidationError("Chaque ligne doit avoir une description")
            if quantity <= 0:
                raise ValidationError(f"Quantité invalide pour « {description} »")
            domain_lines.append(
                InvoiceLine(description=description, quantity=quantity, unit_price=unit_price)
            )

        number = await self._next_number(organization_id, issue_date.year)

        invoice = Invoice(
            id="",
            number=number,
            client_name=client_name,
            client_address=client_address,
            client_email=client_email,
            lines=domain_lines,
            currency=resolved_currency,
            tax_regime=resolved_regime,
            status=InvoiceStatus.ISSUED,
            issue_date=issue_date,
            due_date=due_date,
            notes=notes,
            discount=Decimal(str(discount or 0)),
        )
        totals = invoice.compute()

        record = InvoiceModel(
            organization_id=organization_id,
            number=number,
            client_id=client_id,
            client_name=client_name,
            client_address=client_address,
            client_email=client_email,
            lines=[
                {
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                }
                for line in domain_lines
            ],
            currency=resolved_currency.value,
            tax_regime=resolved_regime.value,
            discount=invoice.discount,
            status=InvoiceStatus.ISSUED.value,
            issue_date=issue_date,
            due_date=due_date,
            notes=notes,
            subtotal=totals.subtotal,
            tax_total=sum((amount for _, amount in totals.taxes), Decimal("0")),
            total=totals.total,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)

        invoice.id = record.id
        company = self._company_dict(organization)

        logo_bytes = None
        if organization.logo_storage_key:
            try:
                logo_bytes = await self._storage.download(organization.logo_storage_key)
            except Exception:
                logo_bytes = None  # logo illisible : on retombe sur le monogramme

        signature_bytes = _decode_signature(signature_data_url)
        pdf_bytes = render_invoice_pdf(
            invoice, totals, company, logo_bytes, signature_bytes
        )
        key = build_invoice_key(organization_id, record.id, number)
        await self._storage.ensure_bucket()
        await self._storage.upload(key, pdf_bytes, "application/pdf")

        record.pdf_storage_key = key
        await self._session.commit()
        await self._session.refresh(record)
        return record

    @staticmethod
    def _company_dict(organization: OrganizationModel) -> dict:
        """Coordonnées imprimées sur la facture.

        Les champs légaux non renseignés affichent « À compléter » : une facture
        incomplète doit se voir au premier coup d'œil plutôt que de partir avec
        des mentions manquantes.
        """
        return {
            "legal_name": organization.legal_name or organization.name,
            "tagline": organization.tagline or "",
            "address": organization.address or PLACEHOLDER,
            "phone": organization.phone or PLACEHOLDER,
            "email": organization.email or PLACEHOLDER,
            "website": organization.website or "",
            "tax_number_1_label": organization.tax_number_1_label,
            "tax_number_1": organization.tax_number_1 or PLACEHOLDER,
            "tax_number_2_label": organization.tax_number_2_label,
            "tax_number_2": organization.tax_number_2 or PLACEHOLDER,
            "registration_number": organization.registration_number or PLACEHOLDER,
            "payment_terms": organization.payment_terms
            or "Paiement à 30 jours à compter de la date d'émission.",
            "payment_details": organization.payment_details or PLACEHOLDER,
            "brand_primary": organization.brand_primary,
            "brand_ink": organization.brand_ink,
        }
