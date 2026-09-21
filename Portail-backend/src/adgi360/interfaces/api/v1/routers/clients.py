from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adgi360.infrastructure.db.models import ClientModel
from adgi360.infrastructure.db.session import get_session
from adgi360.interfaces.api.deps import CurrentUser
from adgi360.interfaces.api.v1.schemas.client_schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


async def get_owned_client(
    client_id: str, organization_id: str, session: AsyncSession
) -> ClientModel:
    """Charge un client en vérifiant qu'il appartient bien à l'agence appelante.

    On répond 404 plutôt que 403 sur un client d'une autre organisation : le
    portail ne doit pas permettre de deviner l'existence de données voisines.
    """
    client = await session.get(ClientModel, client_id)
    if client is None or client.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable")
    return client


@router.get("", response_model=list[ClientOut])
async def list_clients(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[ClientModel]:
    result = await session.execute(
        select(ClientModel)
        .where(ClientModel.organization_id == user.organization_id)
        .order_by(ClientModel.name)
    )
    return list(result.scalars().all())


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ClientModel:
    existing = await session.execute(
        select(ClientModel).where(
            ClientModel.organization_id == user.organization_id,
            ClientModel.name == payload.name,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un client porte déjà ce nom")

    client = ClientModel(
        organization_id=user.organization_id,
        name=payload.name,
        client_type=payload.client_type,
        contact_email=payload.contact_email,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> ClientModel:
    return await get_owned_client(client_id, user.organization_id, session)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str, user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> None:
    client = await get_owned_client(client_id, user.organization_id, session)
    await session.delete(client)
    await session.commit()
