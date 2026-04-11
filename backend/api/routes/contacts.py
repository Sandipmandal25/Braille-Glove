from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.schemas import FavoriteResponse, FavoriteUpsertRequest
from db.models import Favorite
from db.repository import FavoriteRepository

router = APIRouter(prefix="/contacts", tags=["contacts"])

_MAX_FAVORITES = 10


def _get_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def _get_fav_repo(request: Request) -> FavoriteRepository:
    return request.app.state.fav_repo


Factory = Annotated[async_sessionmaker[AsyncSession], Depends(_get_factory)]
FavRepo = Annotated[FavoriteRepository, Depends(_get_fav_repo)]


def _to_response(fav: Favorite) -> FavoriteResponse:
    return FavoriteResponse(slot=fav.slot, name=fav.name, telegram_id=fav.telegram_id)


@router.get("", response_model=list[FavoriteResponse])
async def list_contacts(factory: Factory, fav_repo: FavRepo) -> list[FavoriteResponse]:
    async with factory() as session:
        favs = await fav_repo.list_all(session)
    return [_to_response(f) for f in favs]


@router.put("/{slot}", response_model=FavoriteResponse)
async def upsert_contact(
    slot:    int,
    body:    FavoriteUpsertRequest,
    factory: Factory,
    fav_repo: FavRepo,
) -> FavoriteResponse:
    if not (0 <= slot < _MAX_FAVORITES):
        raise HTTPException(status_code=400, detail=f"Slot must be 0–{_MAX_FAVORITES - 1}")
    async with factory() as session:
        async with session.begin():
            fav = await fav_repo.upsert(
                session,
                Favorite(slot=slot, name=body.name, telegram_id=body.telegram_id),
            )
    return _to_response(fav)


@router.delete("/{slot}", status_code=204)
async def delete_contact(slot: int, factory: Factory, fav_repo: FavRepo) -> None:
    if not (0 <= slot < _MAX_FAVORITES):
        raise HTTPException(status_code=400, detail=f"Slot must be 0–{_MAX_FAVORITES - 1}")
    async with factory() as session:
        async with session.begin():
            await fav_repo.delete_by_slot(session, slot)
