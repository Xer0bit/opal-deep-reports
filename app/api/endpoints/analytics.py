from fastapi import APIRouter, Query, HTTPException, status
from typing import Dict, Any
from datetime import datetime, timedelta
import re
from app.services.predictive_analytics import perform_real_time_analysis
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

def parse_timeframe(timeframe: str) -> timedelta:
    """Parse timeframe string into timedelta"""
    pattern = re.compile(r'^(\d+)([mhd])$')
    match = pattern.match(timeframe)
    if not match:
        raise ValueError("Invalid timeframe format. Use <number>[m|h|d] (e.g., 30m, 2h, 3d)")
    
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'm' and value > 60:
        raise ValueError("Minutes cannot exceed 60")
    if unit == 'h' and value > 24:
        raise ValueError("Hours cannot exceed 24")
    if unit == 'd' and value > 30:
        raise ValueError("Days cannot exceed 30")
        
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    else:
        return timedelta(days=value)

@router.get("/real-time")
async def get_real_time_analysis(
    timeframe: str = Query(
        "1h",
        description="Analysis timeframe: <number>[m|h|d] (e.g., 30m, 2h, 3d)",
        regex="^(\d+[mhd])$"
    ),
    driver_uuid: str = Query(None, description="Optional driver UUID to filter results")
) -> Dict[str, Any]:
    """Get real-time analysis of vehicle and violation data"""
    try:
        start_time = datetime.now()
        data = await perform_real_time_analysis(timeframe=timeframe, driver_uuid=driver_uuid)
        
        # Simplified response structure
        response = {
            "data": {
                "timeframe": timeframe,
                "time_range": data["time_range"],
                "violations": {
                    "total": data["total_violations"],
                    "by_type": data["violation_types"]
                },
                "risk_level": data["risk_level"],
                "metrics": {
                    "hourly_rate": data["stats"]["hourly_rate"],
                    "has_data": data["stats"]["has_data"]
                }
            },
            "meta": {
                "duration_ms": round((datetime.now() - start_time).total_seconds() * 1000),
                "driver_filter": driver_uuid,
                "driver_name": data.get("driver_name", None)
            }
        }

        if not data["stats"]["has_data"]:
            response["data"]["status"] = "No violations found in specified timeframe"
            
        return response
        
    except Exception as e:
        logger.error(f"Error performing real-time analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing real-time analysis: {str(e)}"
        )