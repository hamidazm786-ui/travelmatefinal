# app/api/v1/routes/plans.py
# ============================================================
#  /api/v1/plans  — Travel plan CRUD (all protected by auth)
# ============================================================

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, desc
from typing import List, Optional

from app.db.database import get_db
from app.models.models import User, TravelPlan
from app.schemas.plans import (
    TravelPlanSummary, TravelPlanDetail,
    SavePlanRequest, UpdatePlanRequest, UserStats,
)
from app.core.dependencies import get_current_user
from app.core.logging import logger

router = APIRouter(prefix="/plans", tags=["Travel Plans"])


# ── POST /api/v1/plans  — Save a generated plan ──────────────

@router.post("/", response_model=TravelPlanDetail, status_code=status.HTTP_201_CREATED)
async def save_plan(
    body: SavePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a generated travel plan to the database.
    Called automatically after /travel/plan generates a plan.
    """
    plan = TravelPlan(
        user_id=current_user.id,
        origin=body.origin,
        destination=body.destination,
        departure_date=body.departure_date,
        return_date=body.return_date,
        duration_days=body.duration_days,
        travelers=body.travelers,
        budget_usd=body.budget_usd,
        budget_level=body.budget_level,
        trip_type=body.trip_type,
        extra_notes=body.extra_notes,
        plan_json=body.plan_json,
        summary=body.summary,
        total_estimated_cost_usd=body.total_estimated_cost_usd,
        llm_used=body.llm_used,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)

    # Increment user's total_trips counter
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(total_trips=User.total_trips + 1)
    )

    logger.info(f"[Plans] Plan saved: {plan.id} for user {current_user.id}")
    return TravelPlanDetail.model_validate(plan)


# ── GET /api/v1/plans  — List all plans for current user ─────

@router.get("/", response_model=List[TravelPlanSummary])
async def list_plans(
    skip: int  = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    favourites_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all travel plans for the authenticated user.
    Supports pagination, status filter, and favourites filter.
    """
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
        query = query.where(TravelPlan.is_favourite == True)

    result = await db.execute(query)
    plans = result.scalars().all()
    return [TravelPlanSummary.model_validate(p) for p in plans]


# ── GET /api/v1/plans/{plan_id}  — Get a single plan ─────────

@router.get("/{plan_id}", response_model=TravelPlanDetail)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full detail of a specific travel plan."""
    result = await db.execute(
        select(TravelPlan).where(
            TravelPlan.id == plan_id,
            TravelPlan.user_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found.")
    return TravelPlanDetail.model_validate(plan)


# ── PATCH /api/v1/plans/{plan_id}  — Update plan metadata ────

@router.patch("/{plan_id}", response_model=TravelPlanSummary)
async def update_plan(
    plan_id: str,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update plan status, favourite flag, or notes."""
    result = await db.execute(
        select(TravelPlan).where(
            TravelPlan.id == plan_id,
            TravelPlan.user_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found.")

    updates = body.model_dump(exclude_none=True)
    if updates:
        await db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(**updates)
        )
        await db.refresh(plan)

    return TravelPlanSummary.model_validate(plan)


# ── DELETE /api/v1/plans/{plan_id}  — Delete a plan ──────────

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a travel plan."""
    result = await db.execute(
        select(TravelPlan).where(
            TravelPlan.id == plan_id,
            TravelPlan.user_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found.")

    await db.delete(plan)
    logger.info(f"[Plans] Plan deleted: {plan_id}")


# ── GET /api/v1/plans/stats/me  — Dashboard stats ────────────

@router.get("/stats/me", response_model=UserStats)
async def get_my_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregated stats for the user's dashboard."""
    from datetime import datetime
    from sqlalchemy import extract

    # Total trips
    total_result = await db.execute(
        select(func.count()).where(TravelPlan.user_id == current_user.id)
    )
    total_trips = total_result.scalar() or 0

    # Total estimated spend
    spend_result = await db.execute(
        select(func.sum(TravelPlan.total_estimated_cost_usd))
        .where(TravelPlan.user_id == current_user.id)
    )
    total_spent = spend_result.scalar() or 0.0

    # Favourite destination
    dest_result = await db.execute(
        select(TravelPlan.destination, func.count().label("cnt"))
        .where(TravelPlan.user_id == current_user.id)
        .group_by(TravelPlan.destination)
        .order_by(desc("cnt"))
        .limit(1)
    )
    fav_row = dest_result.first()
    favourite_destination = fav_row[0] if fav_row else None

    # Most used LLM
    llm_result = await db.execute(
        select(TravelPlan.llm_used, func.count().label("cnt"))
        .where(TravelPlan.user_id == current_user.id, TravelPlan.llm_used.isnot(None))
        .group_by(TravelPlan.llm_used)
        .order_by(desc("cnt"))
        .limit(1)
    )
    llm_row = llm_result.first()
    most_used_llm = llm_row[0] if llm_row else None

    # Trips this month
    now = datetime.utcnow()
    month_result = await db.execute(
        select(func.count())
        .where(
            TravelPlan.user_id == current_user.id,
            extract("month", TravelPlan.created_at) == now.month,
            extract("year",  TravelPlan.created_at) == now.year,
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
