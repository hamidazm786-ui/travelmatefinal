# app/api/v1/routes/travel_db.py
# ============================================================
#  /api/v1/travel  — Travel plan generation + DB auto-save
#  Wraps the existing travel_planner service with DB persistence
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.db.database import get_db
from app.models.models import User, TravelPlan
from app.schemas.travel import TravelRequest, TravelResponse
from app.schemas.plans import SavePlanRequest, TravelPlanDetail
from app.services.travel_planner import generate_travel_plan
from app.core.dependencies import get_current_user, get_optional_user
from app.core.logging import logger

router = APIRouter(prefix="/travel", tags=["Travel Planning"])


# ── POST /api/v1/travel/plan  — Generate + auto-save ─────────

@router.post("/plan", response_model=TravelResponse)
async def plan_trip(
    request: TravelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Generate a travel plan using the LLM service.
    If user is authenticated, the plan is automatically saved to DB.
    If not authenticated, plan is returned but not saved.
    """
    logger.info(
        f"[Travel] Plan request: {request.origin} → {request.destination} "
        f"| user={'anonymous' if not current_user else current_user.id}"
    )

    # Generate the plan using existing travel_planner service
    response: TravelResponse = await generate_travel_plan(request)

    # Auto-save to DB if user is authenticated
    if current_user and response.plan:
        try:
            plan = TravelPlan(
                user_id=current_user.id,
                origin=request.origin,
                destination=request.destination,
                departure_date=request.departure_date,
                return_date=request.return_date,
                duration_days=request.duration_days,
                travelers=request.travelers,
                budget_usd=float(request.budget),
                budget_level=request.budget_level,
                trip_type=request.trip_type,
                extra_notes=request.extra_notes,
                plan_json=response.plan if isinstance(response.plan, dict)
                          else response.plan.model_dump(),
                summary=_extract_summary(response.plan),
                total_estimated_cost_usd=_extract_cost(response.plan, request.budget),
                llm_used=response.llm_used,
            )
            db.add(plan)
            await db.flush()

            # Attach DB plan id to response so frontend can reference it
            response.plan_id = plan.id
            logger.info(f"[Travel] Plan auto-saved: {plan.id}")

        except Exception as e:
            # Save failure must NOT block the response
            logger.warning(f"[Travel] Auto-save failed (plan still returned): {e}")

    return response


# ── GET /api/v1/travel/plan/{plan_id}  — Retrieve saved plan ─

@router.get("/plan/{plan_id}", response_model=TravelPlanDetail)
async def get_saved_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a previously saved travel plan by ID."""
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


# ── POST /api/v1/travel/plan/upload  — Plan from file ────────

@router.post("/plan/upload", response_model=TravelResponse)
async def plan_from_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document (PDF, DOCX, TXT) and generate a travel plan from it.
    The plan is auto-saved to DB.
    """
    from app.services.file_service import extract_text_from_file
    from app.schemas.travel import TravelRequest

    content = await file.read()
    text = await extract_text_from_file(file.filename, content)

    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from file.")

    # Build a request from extracted text
    synthetic_request = TravelRequest(
        origin="From uploaded document",
        destination="As specified in document",
        departure_date="As specified",
        return_date="As specified",
        duration_days=7,
        travelers=1,
        budget="5000",
        budget_level="moderate",
        trip_type="leisure",
        extra_notes=text[:4000],  # first 4000 chars as context
    )

    response = await generate_travel_plan(synthetic_request)

    if response.plan:
        plan = TravelPlan(
            user_id=current_user.id,
            origin="Uploaded document",
            destination=response.plan.get("destination", "Various") if isinstance(response.plan, dict) else "Various",
            departure_date="See plan",
            return_date="See plan",
            duration_days=7,
            travelers=1,
            budget_usd=5000,
            budget_level="moderate",
            trip_type="leisure",
            extra_notes=f"Generated from uploaded file: {file.filename}",
            plan_json=response.plan if isinstance(response.plan, dict) else response.plan.model_dump(),
            summary=_extract_summary(response.plan),
            llm_used=response.llm_used,
        )
        db.add(plan)
        await db.flush()
        response.plan_id = plan.id

    return response


# ── Helper functions ──────────────────────────────────────────

def _extract_summary(plan) -> Optional[str]:
    """Extract a short summary from the plan for list views."""
    if not plan:
        return None
    if isinstance(plan, dict):
        return plan.get("summary") or plan.get("overview") or None
    try:
        return getattr(plan, "summary", None) or getattr(plan, "overview", None)
    except Exception:
        return None


def _extract_cost(plan, fallback_budget) -> Optional[float]:
    """Extract estimated cost from the plan."""
    if not plan:
        return float(fallback_budget) if fallback_budget else None
    if isinstance(plan, dict):
        cost = (
            plan.get("total_estimated_cost")
            or plan.get("estimated_cost")
            or plan.get("budget", {}).get("total")
            if isinstance(plan.get("budget"), dict) else None
        )
        if cost:
            return float(str(cost).replace("$", "").replace(",", "").strip())
    return float(fallback_budget) if fallback_budget else None
