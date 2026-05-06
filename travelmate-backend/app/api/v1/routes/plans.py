from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, extract, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.db.database import get_db
from app.models.models import TravelPlan, User
from app.schemas.plans import (
    SavePlanRequest,
    TravelPlanDetail,
    TravelPlanSummary,
    UpdatePlanRequest,
    UserStats,
)

router = APIRouter(prefix="/plans", tags=["Travel Plans"])


@router.post("/", response_model=TravelPlanDetail, status_code=status.HTTP_201_CREATED)
async def save_plan(
    body: SavePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = TravelPlan(user_id=current_user.id, **body.model_dump())
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    await db.execute(update(User).where(User.id == current_user.id).values(total_trips=User.total_trips + 1))
    logger.info(f"[Plans] Plan saved: {plan.id} for user {current_user.id}")
    return TravelPlanDetail.model_validate(plan)


@router.get("/", response_model=List[TravelPlanSummary])
async def list_plans(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    favourites_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(TravelPlan)
        .where(TravelPlan.user_id == current_user.id)
        .order_by(desc(TravelPlan.created_at))
        .offset(skip)
        .limit(limit)
    )
    if status_filter:
        query = query.where(TravelPlan.status == status_filter)
    if favourites_only:
        query = query.where(TravelPlan.is_favourite.is_(True))
    result = await db.execute(query)
    plans = result.scalars().all()
    return [TravelPlanSummary.model_validate(plan) for plan in plans]


@router.get("/{plan_id}", response_model=TravelPlanDetail)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found.")
    return TravelPlanDetail.model_validate(plan)


@router.patch("/{plan_id}", response_model=TravelPlanSummary)
async def update_plan(
    plan_id: str,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found.")
    updates = body.model_dump(exclude_none=True)
    if updates:
        await db.execute(update(TravelPlan).where(TravelPlan.id == plan_id).values(**updates))
        await db.refresh(plan)
    return TravelPlanSummary.model_validate(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TravelPlan).where(TravelPlan.id == plan_id, TravelPlan.user_id == current_user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found.")
    await db.delete(plan)
    logger.info(f"[Plans] Plan deleted: {plan_id}")


@router.get("/stats/me", response_model=UserStats)
async def get_my_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_result = await db.execute(select(func.count()).where(TravelPlan.user_id == current_user.id))
    total_trips = total_result.scalar() or 0

    spend_result = await db.execute(
        select(func.sum(TravelPlan.total_estimated_cost_usd)).where(TravelPlan.user_id == current_user.id)
    )
    total_spent = spend_result.scalar() or 0.0

    dest_result = await db.execute(
        select(TravelPlan.destination, func.count().label("cnt"))
        .where(TravelPlan.user_id == current_user.id)
        .group_by(TravelPlan.destination)
        .order_by(desc("cnt"))
        .limit(1)
    )
    fav_row = dest_result.first()
    favourite_destination = fav_row[0] if fav_row else None

    llm_result = await db.execute(
        select(TravelPlan.llm_used, func.count().label("cnt"))
        .where(TravelPlan.user_id == current_user.id, TravelPlan.llm_used.isnot(None))
        .group_by(TravelPlan.llm_used)
        .order_by(desc("cnt"))
        .limit(1)
    )
    llm_row = llm_result.first()
    most_used_llm = llm_row[0] if llm_row else None

    now = datetime.utcnow()
    month_result = await db.execute(
        select(func.count()).where(
            TravelPlan.user_id == current_user.id,
            extract("month", TravelPlan.created_at) == now.month,
            extract("year", TravelPlan.created_at) == now.year,
        )
    )
    trips_this_month = month_result.scalar() or 0

    return UserStats(
        total_trips=total_trips,
        total_spent_usd=round(total_spent, 2),
        favourite_destination=favourite_destination,
        most_used_llm=most_used_llm,
        trips_this_month=trips_this_month,
    )
