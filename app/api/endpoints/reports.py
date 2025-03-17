from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.core.logger import get_logger

logger = get_logger(__name__)

from app.models.schemas import (
    TimeRangeRequest,
    ViolationTrendsResponse,
    DriverRiskResponse,
    ViolationTrend,
    DriverRiskProfile
)
from app.services.predictive_analytics import (
    analyze_violation_trends,
    predict_driver_risk
)
from app.utils.report_generator import generate_driver_report, generate_fleet_report

router = APIRouter()

@router.post("/violation-trends", response_model=ViolationTrendsResponse)
async def get_violation_trends(params: TimeRangeRequest, generate_pdf: bool = False):
    """
    Get violation trends over time with insights and recommendations
    """
    try:
        logger.info(f"Processing violation trends request: {params}")
        
        # Parse dates if they're strings
        start_date = params.start_date
        end_date = params.end_date
        
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        trends = await analyze_violation_trends(
            group_by=params.group_by,
            start_date=start_date,
            end_date=end_date,
            driver_uuid=params.driver_uuid
        )
        
        if not trends:
            logger.info("No violation trends found for the specified period")
            if generate_pdf:
                # Generate empty report with period information
                pdf_path = generate_driver_report([], 
                    period_info={
                        'start_date': start_date,
                        'end_date': end_date,
                        'driver_uuid': params.driver_uuid
                    }
                )
                return FileResponse(
                    pdf_path,
                    filename=f"driver_violations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    media_type="application/pdf"
                )
            return {
                "trends": [],
                "total_count": 0,
                "date_range": {"start_date": start_date, "end_date": end_date}
            }
        
        response_data = {
            "trends": trends,
            "total_count": sum(t["total_violations"] for t in trends) if trends else 0,
            "date_range": {"start_date": start_date, "end_date": end_date}
        }

        if generate_pdf:
            try:
                pdf_path = generate_driver_report(trends)
                return FileResponse(
                    pdf_path,
                    filename=f"driver_violations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    media_type="application/pdf"
                )
            except Exception as e:
                logger.error(f"Error generating PDF report: {str(e)}", exc_info=True)
                # Fall back to JSON response if PDF generation fails
                return response_data
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error analyzing violation trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/driver-risk", response_model=DriverRiskResponse)
async def get_driver_risk(days: int = Query(90, description="Historical data period in days")):
    """
    Get predictive risk assessment for drivers
    """
    try:
        drivers = await predict_driver_risk(days_history=days)
        
        # Calculate summary statistics
        high_risk_count = sum(1 for d in drivers if d["risk_score"] > 75)
        avg_risk = sum(d["risk_score"] for d in drivers) / len(drivers) if drivers else 0
        
        return {
            "drivers": drivers,
            "total_drivers": len(drivers),
            "high_risk_count": high_risk_count,
            "average_risk_score": round(avg_risk, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting driver risk: {str(e)}")