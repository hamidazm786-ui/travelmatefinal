from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_optional_user
from app.core.logging import logger
from app.db.database import get_db
from app.models.models import TravelPlan, User
from app.schemas.plans import TravelPlanDetail
from app.schemas.travel import TravelPlanResponse, TravelQueryRequest
from app.services.travel_planner import generate_travel_plan

router = APIRouter(prefix="/travel", tags=["Travel Planning"])


@router.post("/plan", response_model=TravelPlanResponse)
async def plan_trip(
    request: TravelQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    response = await generate_travel_plan(request)

    if current_user:
        try:
            plan = TravelPlan(
                user_id=current_user.id,
                origin=request.origin,
                destination=request.destination,
                departure_date=request.departure_date,
                return_date=request.return_date,
                duration_days=response.duration_days,
                travelers=request.travelers,
                budget_usd=request.budget_usd,
                budget_level=request.budget_level.value,
                trip_type=request.trip_type.value,
                extra_notes=request.extra_notes,
                plan_json=response.model_dump(),
                summary=response.summary,
                total_estimated_cost_usd=response.total_estimated_cost_usd,
                llm_used=response.llm_used,
            )
            db.add(plan)
            await db.flush()
            logger.info(f"[Travel] Plan auto-saved: {plan.id}")
        except Exception as exc:
            logger.warning(f"[Travel] Auto-save failed but response returned: {exc}")

    return response


@router.get("/plan/{plan_id}", response_model=TravelPlanDetail)
async def get_saved_plan(
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
