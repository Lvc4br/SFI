import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.shopping import ShoppingList, ShoppingListItem
from sfi_api.models.user import User
from sfi_api.schemas.shopping import (
    ShoppingItemCreate,
    ShoppingItemResponse,
    ShoppingItemUpdate,
    ShoppingListCreate,
    ShoppingListDetail,
    ShoppingListResponse,
    ShoppingListUpdate,
)

router = APIRouter(prefix="/shopping", tags=["shopping"])


async def _owned_list(session: AsyncSession, user_id: uuid.UUID, list_id: uuid.UUID):
    result = await session.scalar(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.user_id == user_id,
            ShoppingList.archived_at.is_(None),
        )
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    return result


@router.post("/lists", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    payload: ShoppingListCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    item = ShoppingList(user_id=user.id, name=payload.name, is_favorite=payload.is_favorite)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ShoppingListResponse.model_validate(item)


@router.get("/lists", response_model=list[ShoppingListResponse])
async def list_lists(
    favorites_only: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    query = select(ShoppingList).where(ShoppingList.user_id == user.id)
    if not include_archived:
        query = query.where(ShoppingList.archived_at.is_(None))
    if favorites_only:
        query = query.where(ShoppingList.is_favorite.is_(True))
    rows = await session.scalars(query.order_by(ShoppingList.updated_at.desc()))
    return [ShoppingListResponse.model_validate(row) for row in rows.all()]


@router.get("/lists/{list_id}", response_model=ShoppingListDetail)
async def get_list(
    list_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    item = await _owned_list(session, user.id, list_id)
    rows = await session.scalars(
        select(ShoppingListItem)
        .where(
            ShoppingListItem.list_id == item.id,
            ShoppingListItem.user_id == user.id,
        )
        .order_by(ShoppingListItem.position, ShoppingListItem.created_at)
    )
    return ShoppingListDetail(
        **ShoppingListResponse.model_validate(item).model_dump(),
        items=[ShoppingItemResponse.model_validate(row) for row in rows.all()],
    )


@router.patch("/lists/{list_id}", response_model=ShoppingListResponse)
async def update_list(
    list_id: uuid.UUID,
    payload: ShoppingListUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    item = await _owned_list(session, user.id, list_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        name = changes["name"].strip()
        if not name:
            raise HTTPException(status_code=422, detail="O nome da lista não pode ficar vazio.")
        item.name = name
    if changes.get("is_favorite") is not None:
        item.is_favorite = changes["is_favorite"]
    await session.commit()
    await session.refresh(item)
    return ShoppingListResponse.model_validate(item)


@router.post("/lists/{list_id}/archive", response_model=ShoppingListResponse)
async def archive_list(
    list_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    item = await _owned_list(session, user.id, list_id)
    item.archived_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return ShoppingListResponse.model_validate(item)


@router.post(
    "/lists/{list_id}/items",
    response_model=ShoppingItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    list_id: uuid.UUID,
    payload: ShoppingItemCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    await _owned_list(session, user.id, list_id)
    item = ShoppingListItem(user_id=user.id, list_id=list_id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ShoppingItemResponse.model_validate(item)


@router.patch("/lists/{list_id}/items/{item_id}", response_model=ShoppingItemResponse)
async def update_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ShoppingItemUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    await _owned_list(session, user.id, list_id)
    item = await session.scalar(
        select(ShoppingListItem).where(
            ShoppingListItem.id == item_id,
            ShoppingListItem.list_id == list_id,
            ShoppingListItem.user_id == user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="O nome do item não pode ficar vazio.")
        if field == "unit" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="A unidade não pode ficar vazia.")
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return ShoppingItemResponse.model_validate(item)


@router.delete("/lists/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    await _owned_list(session, user.id, list_id)
    item = await session.scalar(select(ShoppingListItem).where(
        ShoppingListItem.id == item_id,
        ShoppingListItem.list_id == list_id,
        ShoppingListItem.user_id == user.id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    await session.delete(item)
    await session.commit()
