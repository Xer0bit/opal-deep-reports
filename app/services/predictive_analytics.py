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
    # Update violation config with default values
    VIOLATION_CONFIG = {
        "SPEED_LOW": {"weight": 1.0, "severity": 1.0, "priority": 1, "decay_days": 30},
        "SPEED_MEDIUM": {"weight": 2.5, "severity": 2.0, "priority": 2, "decay_days": 45},
        "SPEED_HIGH": {"weight": 4.0, "severity": 3.0, "priority": 3, "decay_days": 60},
        "HARSH_ACCELERATION": {"weight": 2.0, "severity": 2.0, "priority": 2, "decay_days": 30},
        "SUDDEN_TURN": {"weight": 2.5, "severity": 2.0, "priority": 2, "decay_days": 30},
        "GPS_QUALITY": {"weight": 0.5, "severity": 1.0, "priority": 1, "decay_days": 15},
        "BATTERY_WARNING": {"weight": 0.5, "severity": 1.0, "priority": 1, "decay_days": 15},
        "HARD_BRAKING": {"weight": 3.5, "severity": 3.0, "priority": 3, "decay_days": 45},
        "EXTREME_ACCELERATION": {"weight": 4.0, "severity": 3.0, "priority": 3, "decay_days": 45},
        "CRASH_DETECTION": {"weight": 5.0, "severity": 4.0, "priority": 4, "decay_days": 90},
        "UNKNOWN": {
            "weight": 1.0, 
            "severity": 1.0, 
            "priority": 1, 
            "decay_days": 30,
            "default_score": 20  # Base score for unknown violations
        }
    }

    logger.info(f"Starting driver risk prediction for last {days_history} days")
    
    try:
        # Get driver data from the repository
        driver_data = await data_repository.get_driver_risk_data(days=days_history)
        logger.info(f"Retrieved {len(driver_data) if driver_data else 0} driver records")
        
        if not driver_data:
            logger.warning("No driver data found")
            return []

        # Filter out unknown drivers before processing
        driver_data = [d for d in driver_data if d.get("_id") != "unknown" and d.get("name") != "Unknown"]
        
        processed_drivers = []
        for driver in driver_data:
            try:
                # Validate and set default values for missing data
                violation_count = max(0, driver.get("violation_count", 0))
                violation_types = driver.get("violation_types", [])
                if not violation_types and violation_count > 0:
                    violation_types = ["UNKNOWN"] * violation_count
                
                name = driver.get("name", "").strip() or "Unknown Driver"
                driver_id = driver.get("_id", "").strip()
                
                if not driver_id:
                    logger.warning(f"Missing driver ID for {name}")
                    continue
                
                # Calculate weighted score with data validation
                weighted_score = 0
                max_severity = 0
                violation_counts = {}
                
                for v_type in violation_types:
                    config = VIOLATION_CONFIG.get(v_type, VIOLATION_CONFIG["UNKNOWN"])
                    count = violation_counts.get(v_type, 0) + 1
                    violation_counts[v_type] = count
                    
                    # Apply more weight to known violation types
                    type_weight = config["weight"] if v_type != "UNKNOWN" else config["weight"] * 0.5
                    weighted_score += type_weight * count
                    max_severity = max(max_severity, config["severity"])

                # Adjust scoring for incomplete data
                daily_rate = violation_count / max(days_history/30, 1)
                count_score = min(100, daily_rate * 15)  # Reduced multiplier for more gradual scaling
                severity_score = max_severity * 20  # Adjusted severity impact
                
                # Enhanced recency calculation
                last_violation = driver.get("last_violation")
                if isinstance(last_violation, str):
                    try:
                        last_violation = datetime.fromisoformat(last_violation.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        last_violation = None
                
                # Calculate recency with validation
                days_since_last = None
                if last_violation:
                    days_since_last = (datetime.now() - last_violation).days
                    recency_factor = 1.3 if days_since_last == 0 else (
                        1.2 if days_since_last <= 3 else (
                        1.1 if days_since_last <= 7 else (
                        0.9 if days_since_last <= 14 else 0.8)))
                else:
                    days_since_last = days_history  # Assume oldest possible violation
                    recency_factor = 0.8
                
                # Calculate final risk score with balanced components
                base_score = (
                    count_score * 0.35 +
                    weighted_score * 0.35 +
                    severity_score * 0.3
                )
                
                # Apply recency and data completeness adjustments
                data_completeness = 1.0
                if not violation_types or "UNKNOWN" in violation_types:
                    data_completeness = 0.9
                
                risk_score = min(100, max(20, base_score * recency_factor * data_completeness))
                driver["risk_score"] = round(risk_score, 1)
                
                # Update risk factors with data quality indicators
                risk_factors = []
                if violation_count > 0:
                    risk_factors.append(f"{violation_count} violations in {days_history} days")
                    if "UNKNOWN" in violation_types:
                        risk_factors.append("Some violation types unknown")
                
                # Add known violation types
                known_violations = [v for v in violation_types if v != "UNKNOWN"]
                if known_violations:
                    risk_factors.append(f"Violation types: {', '.join(set(known_violations))}")
                
                if days_since_last is not None and days_since_last < 7:
                    risk_factors.append(f"Recent violation ({days_since_last} days ago)")
                
                driver["key_factors"] = risk_factors if risk_factors else ["Insufficient violation data"]
                
                # Adjust recommendations based on data completeness
                if risk_score > 70 and data_completeness > 0.9:
                    driver["recommendation"] = "Immediate safety review required"
                elif risk_score > 50:
                    driver["recommendation"] = "Schedule training session"
                elif risk_score > 30:
                    driver["recommendation"] = "Monitor closely"
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

async def perform_real_time_analysis(timeframe: str = "1h", driver_uuid: str = None) -> Dict[str, Any]:
    """
    Perform real-time analysis of vehicle and violation data
    Args:
        timeframe: Time window for analysis ("1h" or "24h")
        driver_uuid: Optional driver UUID to filter results
    """
    try:
        repo = DataRepository()
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1 if timeframe == "1h" else 24)
        
        # Get recent violations with proper time range
        time_range = {"$gte": start_time, "$lte": end_time}
        violations = await repo.get_violations(
            time_range=time_range,
            filters={"driver_uuid": driver_uuid} if driver_uuid else None
        )
        
        # Ensure violations is a list
        violations = list(violations) if violations else []
        
        # Get vehicle events with consistent time range
        vehicle_events = await repo.get_vehicle_events(
            time_range=time_range,
            vehicle_uuid=driver_uuid
        )
        
        # Ensure vehicle_events is a list
        vehicle_events = list(vehicle_events) if vehicle_events else []
        
        # Create analysis dict with serializable values
        analysis = {
            "timeframe": timeframe,
            "total_violations": len(violations),
            "total_events": len(vehicle_events),
            "analysis_timestamp": datetime.now().isoformat(),
            "violation_types": {},
            "risk_level": "LOW",
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
        
        if driver_uuid:
            analysis["driver_uuid"] = driver_uuid
            # Get driver details if available
            driver_info = next((v.get("driver_info", {}) for v in violations if v.get("driver_info")), {})
            if driver_info:
                analysis["driver_name"] = driver_info.get("name", "Unknown")
        
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
        
    except Exception as e:
        logger.error(f"Error in perform_real_time_analysis: {str(e)}", exc_info=True)
        raise