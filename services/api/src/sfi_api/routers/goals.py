import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.goals import FinancialGoal, GoalEntry
from sfi_api.models.user import User
from sfi_api.schemas.goals import (
    GoalCreate,
    GoalEntryCreate,
    GoalEntryResponse,
    GoalResponse,
    GoalUpdate,
)

router = APIRouter(prefix="/goals", tags=["goals"])
SESSION_DEPENDENCY = Depends(get_session)
USER_DEPENDENCY = Depends(get_current_user)


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    goal = FinancialGoal(
        user_id=user.id,
        **payload.model_dump(),
        current_amount=Decimal("0.00"),
        status="active",
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    include_archived: bool = False,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    query = select(FinancialGoal).where(FinancialGoal.user_id == user.id)
    if not include_archived:
        query = query.where(FinancialGoal.status != "archived")
    result = await session.scalars(
        query.order_by(
            FinancialGoal.target_date.asc().nulls_last(),
            FinancialGoal.created_at.desc(),
        )
    )
    return list(result.all())


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    goal = await session.scalar(
        select(FinancialGoal).where(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == user.id,
        )
    )
    if goal is None:
        raise HTTPException(404, "Meta não encontrada.")
    return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    payload: GoalUpdate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    goal = await session.scalar(
        select(FinancialGoal)
        .where(FinancialGoal.id == goal_id, FinancialGoal.user_id == user.id)
        .with_for_update()
    )
    if goal is None:
        raise HTTPException(404, "Meta não encontrada.")
    if goal.status == "archived":
        raise HTTPException(409, "Uma meta arquivada não pode ser alterada.")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("status") == "active" and goal.current_amount >= goal.target_amount:
        raise HTTPException(409, "A meta já atingiu o valor definido.")
    for key, value in changes.items():
        setattr(goal, key, value)
    if goal.status != "archived":
        goal.status = (
            "completed" if goal.current_amount >= goal.target_amount else goal.status
        )
    await session.commit()
    await session.refresh(goal)
    return goal


@router.get("/{goal_id}/entries", response_model=list[GoalEntryResponse])
async def list_goal_entries(
    goal_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    goal = await session.scalar(
        select(FinancialGoal.id).where(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == user.id,
        )
    )
    if goal is None:
        raise HTTPException(404, "Meta não encontrada.")
    result = await session.scalars(
        select(GoalEntry)
        .where(GoalEntry.goal_id == goal_id, GoalEntry.user_id == user.id)
        .order_by(GoalEntry.occurred_at.desc(), GoalEntry.created_at.desc())
    )
    return list(result.all())


@router.post(
    "/{goal_id}/entries",
    response_model=GoalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_goal_entry(
    goal_id: uuid.UUID,
    payload: GoalEntryCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    goal = await session.scalar(
        select(FinancialGoal)
        .where(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == user.id,
            FinancialGoal.status.in_(["active", "completed"]),
        )
        .with_for_update()
    )
    if goal is None:
        raise HTTPException(404, "Meta ativa não encontrada.")
    existing = await session.scalar(
        select(GoalEntry).where(
            GoalEntry.user_id == user.id,
            GoalEntry.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        raise HTTPException(409, "Esta chave de idempotência já foi utilizada.")

    if payload.entry_type == "withdrawal" and payload.amount > goal.current_amount:
        raise HTTPException(422, "A retirada não pode superar o valor acumulado.")
    if payload.entry_type == "contribution":
        goal.current_amount += payload.amount
    else:
        goal.current_amount -= payload.amount
    goal.current_amount = goal.current_amount.quantize(Decimal("0.01"))
    goal.status = (
        "completed"
        if goal.current_amount >= goal.target_amount
        else "active"
    )
    entry = GoalEntry(
        user_id=user.id,
        goal_id=goal.id,
        **payload.model_dump(),
    )
    session.add(entry)
    try:
        await session.commit()
        await session.refresh(entry)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409, "O movimento já foi registrado ou conflitou com outro lançamento."
        ) from None
    return entry
