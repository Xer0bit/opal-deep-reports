import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.db.repositories.data_repository import DataRepository
from app.core.logger import get_logger

# Initialize repository
data_repository = DataRepository()
logger = get_logger(__name__)

class PredictiveAnalyticsService:
    def __init__(self, data_repository: DataRepository):
        self.data_repository = data_repository

    def calculate_risk_score(self, vehicle_data: Dict) -> float:
        # Implement risk score calculation logic based on vehicle data
        risk_score = 0.0
        # Example logic (to be replaced with actual calculation)
        if vehicle_data.get("violation_count", 0) > 5:
            risk_score += 10.0
        if vehicle_data.get("accident_history", False):
            risk_score += 15.0
        return risk_score

    def generate_report(self, vehicle_id: str) -> Dict:
        # Fetch real-time data from the repository
        vehicle_data = self.data_repository.get_vehicle_data(vehicle_id)
        risk_score = self.calculate_risk_score(vehicle_data)
        
        report = {
            "vehicle_id": vehicle_id,
            "risk_score": risk_score,
            "data": vehicle_data
        }
        return report

    def get_violation_trends(self, start_date: str, end_date: str) -> List[Dict]:
        # Fetch violation trends from the repository
        trends = self.data_repository.get_violation_trends(start_date, end_date)
        return trends

    def analyze_real_time_data(self) -> Dict:
        # Implement logic to analyze real-time data
        real_time_data = self.data_repository.get_real_time_data()
        analysis_results = {
            "total_vehicles": len(real_time_data),
            "average_risk_score": sum(self.calculate_risk_score(data) for data in real_time_data) / len(real_time_data)
        }
        return analysis_results

async def analyze_violation_trends(group_by: str = "day", days: int = 30, 
                                 start_date: datetime = None, end_date: datetime = None,
                                 driver_uuid: str = None):
    """
    Analyze violation trends over time with optional driver filter
    """
    try:
        if not start_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        
        logger.info(f"Analyzing violation trends from {start_date} to {end_date}"
                   f"{' for driver ' + driver_uuid if driver_uuid else ''}")
        
        trend_data = await data_repository.get_violation_trends(
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            driver_uuid=driver_uuid
        )
        
        # Process time-based trends with driver information
        time_periods = {}
        
        for item in trend_data:
            try:
                period_info = item["_id"]
                time_period = period_info["time_period"]
                driver_uuid = period_info["driver_uuid"]
                driver_name = period_info["driver_name"]
                violation_type = period_info["violation_type"]
                count = item["count"]
                high_severity = item.get("high_severity_count", 0)
                
                period_key = f"{time_period}_{driver_uuid}"
                
                if period_key not in time_periods:
                    time_periods[period_key] = {
                        "time_period": time_period,
                        "driver_uuid": driver_uuid,
                        "driver_name": driver_name,
                        "total_violations": 0,
                        "violation_types": {},
                        "top_type": "",
                        "insight": "",
                        "action": "",
                        "high_severity_count": 0
                    }
                
                current = time_periods[period_key]
                current["total_violations"] += count
                current["violation_types"][violation_type] = count
                current["high_severity_count"] += high_severity
                
                if not current["top_type"] or count > current["violation_types"].get(current["top_type"], 0):
                    current["top_type"] = violation_type
                    
            except Exception as e:
                logger.error(f"Error processing trend item: {str(e)}")
                continue
        
        result = list(time_periods.values())
        
        # Generate insights and recommendations
        for data in result:
            total = data["total_violations"]
            high_severity = data.get("high_severity_count", 0)
            
            if high_severity > 0:
                data["insight"] = f"High severity violations detected ({high_severity})"
            elif total > 10:
                data["insight"] = f"High violation frequency ({total})"
            elif total > 5:
                data["insight"] = "Moderate violation frequency"
            else:
                data["insight"] = "Low violation frequency"
            
            if high_severity > 0:
                data["action"] = "Immediate safety review required"
            elif total > 10:
                data["action"] = "Investigate driving patterns"
            elif total > 5:
                data["action"] = "Monitor situation"
            else:
                data["action"] = "No action needed"
        
        logger.info(f"Processed {len(result)} time period-driver combinations")
        return sorted(result, key=lambda x: (x["time_period"], x.get("driver_name", "")))
        
    except Exception as e:
        logger.error(f"Error analyzing violation trends: {str(e)}", exc_info=True)
        raise

async def predict_driver_risk(days_history: int = 90):
    """
    Predict driver risk scores based on historical data
    """
    logger.info(f"Starting driver risk prediction for last {days_history} days")
    
    try:
        # Get driver data from the repository
        driver_data = await data_repository.get_driver_risk_data(days=days_history)
        logger.info(f"Retrieved {len(driver_data) if driver_data else 0} driver records")
        
        if not driver_data:
            logger.warning("No driver data found")
            return []

        processed_drivers = []
        for driver in driver_data:
            try:
                # Calculate base risk from violation count and severity
                violation_count = driver["violation_count"]
                avg_severity = driver.get("avg_severity", 1.0)
                
                logger.debug(f"Processing driver {driver.get('_id')}: {violation_count} violations, {avg_severity} avg severity")
                
                # Calculate days since last violation
                days_since_last = (datetime.now() - driver["last_violation"]).days
                recency_factor = max(0.5, min(1.5, 10 / max(days_since_last, 1)))
                
                # Calculate risk score
                raw_score = (violation_count * avg_severity * recency_factor / days_history) * 100
                risk_score = min(100, max(0, raw_score))
                
                # Add risk information to driver
                driver["risk_score"] = round(risk_score, 1)
                
                # Determine key risk factors
                risk_factors = []
                if violation_count > 5:
                    risk_factors.append(f"{violation_count} violations in {days_history} days")
                if avg_severity > 2:
                    risk_factors.append("High severity violations")
                if days_since_last < 7 and violation_count > 0:
                    risk_factors.append(f"Recent violation ({days_since_last} days ago)")
                    
                driver["key_factors"] = risk_factors if risk_factors else ["No significant risk factors"]
                
                # Generate recommendations
                if risk_score > 75:
                    driver["recommendation"] = "Schedule immediate training session"
                elif risk_score > 50:
                    driver["recommendation"] = "Monitor closely and provide feedback"
                else:
                    driver["recommendation"] = "Routine monitoring"
                
                processed_drivers.append(driver)
            except Exception as e:
                logger.error(f"Error processing driver {driver.get('_id')}: {str(e)}")
                continue
        
        logger.info(f"Successfully processed {len(processed_drivers)} drivers")
        return sorted(processed_drivers, key=lambda x: x["risk_score"], reverse=True)
        
    except Exception as e:
        logger.error(f"Error in predict_driver_risk: {str(e)}", exc_info=True)
        raise

async def perform_real_time_analysis(timeframe: str = "1h") -> Dict[str, Any]:
    """
    Perform real-time analysis of vehicle and violation data
    """
    repo = DataRepository()
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1 if timeframe == "1h" else 24)
    
    # Get recent violations and events
    violations = await repo.get_violations(
        start_date=start_time,
        end_date=end_time
    )
    
    vehicle_events = await repo.get_vehicle_events(
        time_range={"$gte": start_time, "$lte": end_time}
    )
    
    analysis = {
        "timeframe": timeframe,
        "total_violations": len(violations),
        "total_events": len(vehicle_events),
        "analysis_timestamp": datetime.now(),
        "violation_types": {},
        "risk_level": "LOW"
    }
    
    # Count violation types
    for violation in violations:
        v_type = violation.get("violation_type", "UNKNOWN")
        analysis["violation_types"][v_type] = analysis["violation_types"].get(v_type, 0) + 1
    
    # Determine risk level based on violation frequency
    hourly_rate = len(violations) / (1 if timeframe == "1h" else 24)
    if hourly_rate > 10:
        analysis["risk_level"] = "HIGH"
    elif hourly_rate > 5:
        analysis["risk_level"] = "MEDIUM"
    
    return analysis