from fastapi import APIRouter
from app.api.endpoints.reports import router as reports_router
from app.api.endpoints.analytics import router as analytics_router

api_router = APIRouter()
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])