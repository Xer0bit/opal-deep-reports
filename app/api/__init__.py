# app/api/__init__.py

from fastapi import APIRouter

router = APIRouter()

from .endpoints import reports, analytics

router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])