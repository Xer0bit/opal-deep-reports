from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
from datetime import datetime
from app.db.mongodb import get_database
from app.services.predictive_analytics import perform_real_time_analysis

router = APIRouter()

@router.get("/analytics")
async def get_analytics():
    db = get_database()
    try:
        data = await perform_real_time_analysis(db)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/real-time", response_model=Dict[str, Any])
async def get_real_time_analysis(
    timeframe: str = Query("1h", description="Analysis timeframe: 1h or 24h")
):
    """
    Get real-time analysis of vehicle and violation data
    """
    return await perform_real_time_analysis(timeframe)