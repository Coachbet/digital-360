from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.application.invoicing.use_cases.create_invoice import CreateInvoiceUseCase
from adgi360.domain.data.entities import build_branding_key
from adgi360.domain.invoicing.entities import Currency, InvoiceStatus, TaxRegime
from adgi360.infrastructure.db.models import InvoiceModel
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.storage.client import FileStorage, get_storage
from adgi360.interfaces.api.deps import CurrentOrganization, CurrentUser
from adgi360.interfaces.api.v1.schemas.invoice_schemas import (
    InvoiceCreate,
    InvoiceDownloadOut,
    InvoiceOptionsOut,
    InvoiceOut,
    OptionOut,
)
from adgi360.shared.exceptions import ExternalServiceError, NotFoundError, ValidationError

router = APIRouter(prefix="/invoices", tags=["invoices"])


async def _get_owned_invoice(
    invoice_id: str, organization_id: str, session: AsyncSession
) -> InvoiceModel:
    invoice = await session.get(InvoiceModel, invoice_id)
    if invoice is None or invoice.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Facture introuvable")
    return invoice


@router.get("/options", response_model=InvoiceOptionsOut)
async def list_options() -> InvoiceOptionsOut:
    """Listes fixes alimentant les menus déroulants du formulaire."""
    return InvoiceOptionsOut(
        currencies=[OptionOut(value=c.value, label=c.label) for c in Currency],
        tax_regimes=[OptionOut(value=t.value, label=t.label) for t in TaxRegime],
        statuses=[OptionOut(value=s.value, label=s.label) for s in InvoiceStatus],
    )


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    user: CurrentUser,
    invoice_status: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[InvoiceModel]:
    query = select(InvoiceModel).where(InvoiceModel.organization_id == user.organization_id)
    if invoice_status:
        query = query.where(InvoiceModel.status == invoice_status)
    result = await session.execute(query.order_by(InvoiceModel.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> InvoiceModel:
    """Crée la facture, calcule les taxes et génère le PDF aux couleurs de l'agence."""
    try:
        return await CreateInvoiceUseCase(session, storage).execute(
            organization_id=user.organization_id,
            client_name=payload.client_name,
            lines=[line.model_dump() for line in payload.lines],
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            client_id=payload.client_id,
            client_address=payload.client_address,
            client_email=payload.client_email,
            currency=payload.currency,
            tax_regime=payload.tax_regime,
            discount=payload.discount,
            notes=payload.notes,
            signature_data_url=payload.signature_data_url,
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> InvoiceModel:
    return await _get_owned_invoice(invoice_id, user.organization_id, session)


@router.get("/{invoice_id}/pdf", response_model=InvoiceDownloadOut)
async def download_invoice(
    invoice_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> InvoiceDownloadOut:
    invoice = await _get_owned_invoice(invoice_id, user.organization_id, session)
    if not invoice.pdf_storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF indisponible pour cette facture")
    url = await storage.presigned_url(invoice.pdf_storage_key)
    return InvoiceDownloadOut(url=url, filename=f"{invoice.number}.pdf", expires_in=3600)


@router.post("/{invoice_id}/status", response_model=InvoiceOut)
async def change_status(
    invoice_id: str,
    user: CurrentUser,
    new_status: str = Query(..., alias="status"),
    session: AsyncSession = Depends(get_session),
) -> InvoiceModel:
    """Suivi du cycle de vie : émise → payée, ou annulation."""
    invoice = await _get_owned_invoice(invoice_id, user.organization_id, session)
    try:
        InvoiceStatus(new_status)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Statut inconnu : {new_status}"
        ) from exc
    invoice.status = new_status
    await session.commit()
    await session.refresh(invoice)
    return invoice
