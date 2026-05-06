# app/api/v1/router.py
# ============================================================
#  V1 API Router — registers all route modules
# ============================================================

from fastapi import APIRouter
from app.api.v1.routes import files, health, search
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.chat_db import router as chat_router
from app.api.v1.routes.plans import router as plans_router
from app.api.v1.routes.travel_db import router as travel_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(travel_router)
api_router.include_router(chat_router)
api_router.include_router(plans_router)
api_router.include_router(search.router)
api_router.include_router(files.router)
