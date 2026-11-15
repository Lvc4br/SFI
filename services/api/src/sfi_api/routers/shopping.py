import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.product import ShoppingProduct
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


async def _validate_product(
    session: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID | None
) -> ShoppingProduct | None:
    if product_id is None:
        return None
    product = await session.scalar(
        select(ShoppingProduct).where(
            ShoppingProduct.id == product_id,
            ShoppingProduct.user_id == user_id,
            ShoppingProduct.archived_at.is_(None),
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return product


@router.post("/lists", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    payload: ShoppingListCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    item = ShoppingList(user_id=user.id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ShoppingListResponse.model_validate(item)


@router.get("/lists", response_model=list[ShoppingListResponse])
async def list_lists(
    favorites_only: bool = Query(default=False),
    templates_only: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    query = select(ShoppingList).where(ShoppingList.user_id == user.id)
    if not include_archived:
        query = query.where(ShoppingList.archived_at.is_(None))
    if favorites_only:
        query = query.where(ShoppingList.is_favorite.is_(True))
    if templates_only:
        query = query.where(ShoppingList.is_template.is_(True))
    rows = await session.scalars(query.order_by(ShoppingList.updated_at.desc()))
    return [ShoppingListResponse.model_validate(row) for row in rows.all()]


@router.post(
    "/lists/from-template/{template_id}",
    response_model=ShoppingListDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_list_from_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    template = await _owned_list(session, user.id, template_id)
    if not template.is_template:
        raise HTTPException(status_code=409, detail="A lista informada não é um modelo.")
    source_items = await session.scalars(
        select(ShoppingListItem)
        .where(ShoppingListItem.list_id == template.id, ShoppingListItem.user_id == user.id)
        .order_by(ShoppingListItem.position, ShoppingListItem.created_at)
    )
    new_list = ShoppingList(
        user_id=user.id,
        name=template.name,
        is_favorite=False,
        is_template=False,
    )
    session.add(new_list)
    await session.flush()
    copied_items = [
        ShoppingListItem(
            user_id=user.id,
            list_id=new_list.id,
            product_id=item.product_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            is_checked=False,
            position=item.position,
            notes=item.notes,
        )
        for item in source_items.all()
    ]
    session.add_all(copied_items)
    await session.commit()
    await session.refresh(new_list)
    return ShoppingListDetail(
        **ShoppingListResponse.model_validate(new_list).model_dump(),
        items=[ShoppingItemResponse.model_validate(item) for item in copied_items],
    )


@router.get("/lists/{list_id}", response_model=ShoppingListDetail)
async def get_list(
    list_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    item = await _owned_list(session, user.id, list_id)
    rows = await session.scalars(
        select(ShoppingListItem)
        .where(ShoppingListItem.list_id == item.id, ShoppingListItem.user_id == user.id)
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
    for field in ("is_favorite", "is_template"):
        if changes.get(field) is not None:
            setattr(item, field, changes[field])
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
    shopping_list = await _owned_list(session, user.id, list_id)
    product = await _validate_product(session, user.id, payload.product_id)
    shopping_list.updated_at = datetime.now(UTC)
    item = ShoppingListItem(user_id=user.id, list_id=list_id, **payload.model_dump())
    if product is not None:
        item.name = payload.name or product.name
        item.unit = payload.unit or product.unit
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
    changes = payload.model_dump(exclude_unset=True)
    if "product_id" in changes:
        await _validate_product(session, user.id, changes["product_id"])
    for field, value in changes.items():
        if field in {"name", "quantity", "unit", "is_checked", "position"} and value is None:
            raise HTTPException(status_code=422, detail=f"O campo {field} não pode ser nulo.")
        if field == "name" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="O nome do item não pode ficar vazio.")
        if field == "unit" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="A unidade não pode ficar vazia.")
        setattr(item, field, value)
    shopping_list = await _owned_list(session, user.id, list_id)
    shopping_list.updated_at = datetime.now(UTC)
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
    shopping_list = await _owned_list(session, user.id, list_id)
    shopping_list.updated_at = datetime.now(UTC)
    await session.delete(item)
    await session.commit()
