from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class TimeRangeRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    group_by: str = Field(default="day", description="Group by: hour, day, week, month")
    days: Optional[int] = Field(default=30, description="Number of days to look back")
    driver_uuid: Optional[str] = Field(default=None, description="Filter by specific driver UUID")

class ViolationTrend(BaseModel):
    time_period: str
    driver_uuid: Optional[str]
    driver_name: Optional[str]
    total_violations: int
    violation_types: Dict[str, int]
    top_type: str
    insight: str
    action: str

class ViolationTrendsResponse(BaseModel):
    trends: List[ViolationTrend]
    total_count: int
    date_range: Dict[str, datetime]

class DriverRiskFactor(BaseModel):
    factor: str
    impact: float

class DriverRiskProfile(BaseModel):
    driver_uuid: str = Field(..., alias="_id")
    name: str
    violation_count: int
    risk_score: float
    key_factors: List[str]
    recommendation: str
    last_violation: datetime
    violation_types: List[str]

class DriverRiskResponse(BaseModel):
    drivers: List[DriverRiskProfile]
    total_drivers: int
    high_risk_count: int
    average_risk_score: float

class VehicleEvent(BaseModel):
    event_id: str
    vehicle_id: str
    timestamp: str
    event_type: str
    location: str
    details: Optional[dict] = None

class Violation(BaseModel):
    violation_id: str
    vehicle_id: str
    violation_type: str
    timestamp: str
    fine_amount: float
    status: str

class PredictiveReport(BaseModel):
    report_id: str
    vehicle_id: str
    risk_score: float
    analysis_date: str
    violations: List[Violation]
    events: List[VehicleEvent]