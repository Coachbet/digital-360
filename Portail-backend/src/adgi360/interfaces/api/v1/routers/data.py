from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.domain.data.entities import build_storage_key
from adgi360.infrastructure.db.models import DataFileModel
from adgi360.infrastructure.db.session import get_session
from adgi360.infrastructure.storage.client import FileStorage, get_storage
from adgi360.interfaces.api.deps import CurrentUser
from adgi360.interfaces.api.v1.routers.clients import get_owned_client
from adgi360.interfaces.api.v1.schemas.data_schemas import (
    DataFileOut,
    DownloadUrlOut,
    PeriodOut,
)

router = APIRouter(prefix="/data", tags=["data"])


async def _get_owned_file(
    file_id: str, organization_id: str, session: AsyncSession
) -> DataFileModel:
    record = await session.get(DataFileModel, file_id)
    if record is None or record.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier introuvable")
    return record


@router.get("/clients/{client_id}/periods", response_model=list[PeriodOut])
async def list_periods(
    client_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[PeriodOut]:
    """Périodes disponibles pour un client, avec le nombre de fichiers."""
    await get_owned_client(client_id, user.organization_id, session)
    result = await session.execute(
        select(DataFileModel.period, func.count(DataFileModel.id))
        .where(
            DataFileModel.organization_id == user.organization_id,
            DataFileModel.client_id == client_id,
        )
        .group_by(DataFileModel.period)
        .order_by(DataFileModel.period.desc())
    )
    return [PeriodOut(period=row[0], file_count=row[1]) for row in result.all()]


@router.get("/files", response_model=list[DataFileOut])
async def list_files(
    user: CurrentUser,
    client_id: str = Query(...),
    period: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[DataFileModel]:
    await get_owned_client(client_id, user.organization_id, session)
    query = select(DataFileModel).where(
        DataFileModel.organization_id == user.organization_id,
        DataFileModel.client_id == client_id,
    )
    if period:
        query = query.where(DataFileModel.period == period)
    result = await session.execute(query.order_by(DataFileModel.uploaded_at.desc()))
    return list(result.scalars().all())


@router.post("/files", response_model=list[DataFileOut], status_code=status.HTTP_201_CREATED)
async def upload_files(
    user: CurrentUser,
    client_id: str = Query(...),
    period: str = Query(..., description="Période, ex: 2026-08"),
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> list[DataFileModel]:
    """Dépose un ou plusieurs fichiers pour un client et une période."""
    await get_owned_client(client_id, user.organization_id, session)
    await storage.ensure_bucket()

    created: list[DataFileModel] = []
    for upload in files:
        content = await upload.read()
        filename = upload.filename or "sans-nom"
        key = build_storage_key(user.organization_id, client_id, period, filename)
        await storage.upload(key, content, upload.content_type)

        record = DataFileModel(
            organization_id=user.organization_id,
            client_id=client_id,
            period=period,
            filename=filename,
            storage_key=key,
            content_type=upload.content_type,
            size_bytes=len(content),
        )
        session.add(record)
        created.append(record)

    await session.commit()
    for record in created:
        await session.refresh(record)
    return created


@router.get("/files/{file_id}/download", response_model=DownloadUrlOut)
async def get_download_url(
    file_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> DownloadUrlOut:
    record = await _get_owned_file(file_id, user.organization_id, session)
    url = await storage.presigned_url(record.storage_key)
    return DownloadUrlOut(url=url, expires_in=3600)


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    storage: FileStorage = Depends(get_storage),
) -> None:
    record = await _get_owned_file(file_id, user.organization_id, session)
    await storage.delete(record.storage_key)
    await session.delete(record)
    await session.commit()
