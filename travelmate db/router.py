# app/api/v1/router.py
# ============================================================
#  Main API v1 router — registers all route groups
# ============================================================

from fastapi import APIRouter

from app.api.v1.routes.auth     import router as auth_router
from app.api.v1.routes.plans    import router as plans_router
from app.api.v1.routes.chat_db  import router as chat_router
from app.api.v1.routes.travel_db import router as travel_router

# Keep these if your original backend had them
try:
    from app.api.v1.routes.search import router as search_router
    _has_search = True
except ImportError:
    _has_search = False

try:
    from app.api.v1.routes.files import router as files_router
    _has_files = True
except ImportError:
    _has_files = False


api_router = APIRouter(prefix="/api/v1")

# ── Authentication (register / login / profile) ───────────────
api_router.include_router(auth_router)

# ── Travel planning (generate + save itineraries) ─────────────
api_router.include_router(travel_router)

# ── Saved plans (CRUD on DB-stored plans) ─────────────────────
api_router.include_router(plans_router)

# ── Chat (sessions + messages, DB-persisted) ──────────────────
api_router.include_router(chat_router)

# ── Optional: search & file upload ───────────────────────────
if _has_search:
    api_router.include_router(search_router)

if _has_files:
    api_router.include_router(files_router)
