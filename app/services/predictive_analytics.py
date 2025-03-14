import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.db.repositories.data_repository import DataRepository
from app.core.logger import get_logger
import re

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
        if vehicle_data.get("violation_count", 0) > 60:
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

async def analyze_violation_trends(group_by: str = "day",
                                 start_date: datetime = None, end_date: datetime = None,
                                 driver_uuid: str = None):
    """
    Analyze violation trends over time with optional driver filter
    """
    try:
        if not start_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # Default to 30 days if dates not provided
        
        logger.info(f"Analyzing violation trends from {start_date} to {end_date}"
                   f"{' for driver ' + driver_uuid if driver_uuid else ' for all drivers'}")
        
        trend_data = await data_repository.get_violation_trends(
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            driver_uuid=driver_uuid  # If None, repository should return data for all drivers
        )
        
        # Process time-based trends with driver information
        time_periods = {}
        
        for item in trend_data:
            try:
                period_info = item["_id"]
                time_period = period_info["time_period"]
                curr_driver_uuid = period_info["driver_uuid"]
                driver_name = period_info["driver_name"]
                violation_type = period_info["violation_type"]
                count = item["count"]
                high_severity = item.get("high_severity_count", 0)
                
                period_key = f"{time_period}_{curr_driver_uuid}"
                
                if (period_key) not in time_periods:
                    time_periods[period_key] = {
                        "time_period": time_period,
                        "driver_uuid": curr_driver_uuid,
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
    """Predict driver risk scores based on historical data"""
    # Updated violation weights and configuration
    VIOLATION_CONFIG = {
        "SPEED_LOW": {"base_weight": 15.0, "severity": 2.0, "multiplier": 1.5},
        "SPEED_MEDIUM": {"base_weight": 25.0, "severity": 3.0, "multiplier": 2.0},
        "SPEED_HIGH": {"base_weight": 35.0, "severity": 4.0, "multiplier": 2.5},
        "HARSH_ACCELERATION": {"base_weight": 20.0, "severity": 2.5, "multiplier": 1.8},
        "HARD_BRAKING": {"base_weight": 20.0, "severity": 2.5, "multiplier": 1.8},
        "CRASH_DETECTION": {"base_weight": 40.0, "severity": 5.0, "multiplier": 3.0},
        "UNKNOWN": {"base_weight": 10.0, "severity": 1.0, "multiplier": 1.0}
    }

    try:
        logger.info(f"Starting driver risk prediction for last {days_history} days")
        
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
                # Basic validation
                violation_count = max(0, driver.get("violation_count", 0))
                violation_types = driver.get("violation_types", [])
                last_violation = driver.get("last_violation")
                
                # Convert last_violation to datetime if needed
                if isinstance(last_violation, str):
                    last_violation = datetime.fromisoformat(last_violation.replace('Z', '+00:00'))

                # 1. Calculate Time-Based Components
                hours_since_last = float('inf')
                if last_violation:
                    hours_since_last = (datetime.now() - last_violation).total_seconds() / 3600
                
                time_factor = 1.0
                if hours_since_last < 1:  # Last hour
                    time_factor = 2.0
                elif hours_since_last < 24:  # Last day
                    time_factor = 1.5
                elif hours_since_last < 72:  # Last 3 days
                    time_factor = 1.2

                # 2. Violation Frequency Score
                days_active = min(days_history, 3)  # Focus on recent activity
                daily_rate = violation_count / days_active
                frequency_score = min(50, daily_rate * 0.5)  # Base frequency score

                # Progressive scaling for high frequencies
                if daily_rate > 50:
                    frequency_score *= 1.5
                elif daily_rate > 30:
                    frequency_score *= 1.3
                elif daily_rate > 20:
                    frequency_score *= 1.2

                # 3. Violation Type Scoring
                type_scores = {}
                violation_weights = 0
                total_severity = 0
                
                for v_type in violation_types:
                    config = VIOLATION_CONFIG.get(v_type, VIOLATION_CONFIG["UNKNOWN"])
                    count = violation_types.count(v_type)
                    
                    # Calculate progressive weight increase
                    weight = config["base_weight"] * (1 + (count - 1) * 0.1)  # 10% increase per violation
                    severity = config["severity"] * config["multiplier"]
                    
                    type_scores[v_type] = {
                        "count": count,
                        "weight": weight,
                        "severity": severity,
                        "score": weight * severity * count
                    }
                    
                    violation_weights += weight * count
                    total_severity += severity * count

                # 4. Calculate Weighted Severity Score
                avg_severity = total_severity / max(1, len(violation_types))
                severity_score = min(30, avg_severity * 2)  # Cap at 30

                # 5. Speed Violation Impact
                speed_violations = sum(1 for v in violation_types if v.startswith("SPEED_"))
                speed_ratio = speed_violations / max(1, len(violation_types))
                speed_impact = speed_ratio * 20  # Up to 20 points for speed violations

                # 6. Final Score Calculation
                base_score = (
                    frequency_score * 0.35 +    # Frequency component (35%)
                    severity_score * 0.25 +     # Severity component (25%)
                    speed_impact * 0.20 +       # Speed violation impact (20%)
                    violation_weights * 0.20    # Violation weights (20%)
                ) * time_factor

                # 7. Apply Thresholds and Caps
                if violation_count > 200:
                    base_score = max(base_score, 85)
                elif violation_count > 150:
                    base_score = max(base_score, 75)
                elif violation_count > 100:
                    base_score = max(base_score, 65)
                elif violation_count > 50:
                    base_score = max(base_score, 45)

                # Final score with bounds
                risk_score = min(95, max(20, base_score))
                
                # Calculate key factors based on risk components and patterns
                key_factors = []
                
                # Add violation count factor
                key_factors.append(f"{violation_count} violations in {days_active} days")
                
                # Add speed violation factor if present
                if speed_ratio > 0:
                    speed_types = [v_type for v_type in violation_types if v_type.startswith("SPEED_")]
                    speed_str = ", ".join(sorted(set(speed_types)))
                    key_factors.append(f"Violation types: {speed_str}")
                
                # Add recency factor
                if hours_since_last != float('inf'):
                    if hours_since_last < 1:
                        key_factors.append("Recent violation (less than 1 hour ago)")
                    elif hours_since_last < 24:
                        key_factors.append("Recent violation (less than 24 hours ago)")
                    elif hours_since_last < 72:
                        key_factors.append(f"Recent violation ({int(hours_since_last/24)} days ago)")
                
                # Add frequency pattern factor
                if daily_rate > 50:
                    key_factors.append("Extremely high violation frequency")
                elif daily_rate > 30:
                    key_factors.append("Very high violation frequency")
                elif daily_rate > 20:
                    key_factors.append("High violation frequency")
                
                # Add severity factor
                if avg_severity > 2.5:
                    key_factors.append("High severity violations")
                elif avg_severity > 1.5:
                    key_factors.append("Moderate severity violations")

                # Update driver data with key factors and risk information
                driver.update({
                    "risk_score": round(risk_score, 1),
                    "key_factors": key_factors,
                    "risk_components": {
                        "frequency_score": round(frequency_score, 2),
                        "severity_score": round(severity_score, 2),
                        "speed_impact": round(speed_impact, 2),
                        "time_factor": round(time_factor, 2),
                        "daily_violation_rate": round(daily_rate, 2)
                    },
                    "recommendation": (
                        "Critical - Immediate Intervention Required" if risk_score >= 75
                        else "High Risk - Urgent Review Needed" if risk_score >= 60
                        else "Moderate Risk - Schedule Review" if risk_score >= 45
                        else "Low Risk - Regular Monitoring"
                    )
                })

                processed_drivers.append(driver)

            except Exception as e:
                logger.error(f"Error processing driver {driver.get('_id')}: {str(e)}")
                continue

        logger.info(f"Successfully processed {len(processed_drivers)} drivers")
        return sorted(processed_drivers, key=lambda x: x["risk_score"], reverse=True)
        
    except Exception as e:
        logger.error(f"Error in predict_driver_risk: {str(e)}", exc_info=True)
        raise

def calculate_time_window(timeframe: str) -> tuple[datetime, datetime]:
    """Calculate start and end time based on timeframe"""
    pattern = re.compile(r'^(\d+)([mhd])$')
    match = pattern.match(timeframe)
    if not match:
        raise ValueError("Invalid timeframe format")
    
    value, unit = int(match.group(1)), match.group(2)
    end_time = datetime.now()
    
    if unit == 'm':
        start_time = end_time - timedelta(minutes=value)
    elif unit == 'h':
        start_time = end_time - timedelta(hours=value)
    else:
        start_time = end_time - timedelta(days=value)
        
    return start_time, end_time

async def perform_real_time_analysis(timeframe: str = "1h", driver_uuid: str = None) -> Dict[str, Any]:
    """
    Perform real-time analysis of vehicle and violation data
    Args:
        timeframe: Time window for analysis (e.g., "30m", "2h", "3d")
        driver_uuid: Optional driver UUID to filter results
    """
    try:
        start_time, end_time = calculate_time_window(timeframe)
        logger.debug(f"Analyzing time window from {start_time} to {end_time}")
        
        # Calculate time difference once for use throughout the function
        time_diff = end_time - start_time
        hours = time_diff.total_seconds() / 3600
        logger.debug(f"Time window: {hours} hours")
        
        # Get violations with expanded query
        violations = await data_repository.get_violations(
            time_range={"$gte": start_time, "$lte": end_time},
            filters={"driver_uuid": driver_uuid} if driver_uuid else None
        )
        
        # Get vehicle events
        vehicle_events = await data_repository.get_vehicle_events(
            time_range={"$gte": start_time, "$lte": end_time},
            vehicle_uuid=driver_uuid
        )
        
        # Convert cursors to lists
        violations_list = list(violations) if violations else []
        events_list = list(vehicle_events) if vehicle_events else []
        
        # Group violations by driver when no specific driver is requested
        drivers_data = {}
        if not driver_uuid and violations_list:
            for violation in violations_list:
                curr_driver_uuid = violation.get("driver_uuid")
                if curr_driver_uuid:
                    if curr_driver_uuid not in drivers_data:
                        # Enhanced driver name handling
                        driver_name = violation.get("driver_name")
                        if not driver_name or driver_name == "Unknown Driver":
                            driver_name = f"Driver {curr_driver_uuid}"
                        if curr_driver_uuid == "unknown":
                            driver_name = "Unassigned Driver"
                            
                        drivers_data[curr_driver_uuid] = {
                            "uuid": curr_driver_uuid,
                            "name": driver_name,
                            "violations": [],
                            "events": [],
                            "violation_types": {},
                            "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                            "last_event_time": None
                        }
                    drivers_data[curr_driver_uuid]["violations"].append(violation)
        
        # Create analysis dict with enhanced defaults
        analysis = {
            "timeframe": timeframe,
            "total_violations": len(violations_list),
            "total_events": len(events_list),
            "analysis_timestamp": datetime.now(),
            "violation_types": {},
            "risk_level": "LOW",
            "time_range": {
                "start": start_time,
                "end": end_time
            },
            "stats": {
                "hourly_rate": 0.0,
                "has_data": bool(violations_list or events_list),
                "last_event_time": None,
                "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "data_summary": {
                    "violations_processed": len(violations_list),
                    "events_processed": len(events_list),
                    "time_window_hours": round(hours, 2),
                    "time_window_display": (
                        f"{time_diff.days}d" if time_diff.days > 0
                        else f"{time_diff.seconds // 3600}h" if time_diff.seconds // 3600 > 0
                        else f"{time_diff.seconds // 60}m"
                    ),
                    "data_available": bool(violations_list or events_list),
                    "total_drivers": len(drivers_data) if not driver_uuid else 1
                }
            }
        }

        # Add drivers array when no specific driver is requested
        if not driver_uuid:
            analysis["drivers"] = []
            for d_uuid, d_data in drivers_data.items():
                driver_violations = d_data["violations"]
                driver_summary = {
                    "uuid": d_uuid,
                    "name": d_data["name"],
                    "total_violations": len(driver_violations),
                    "violation_types": {},
                    "severity_counts": d_data["severity_counts"],
                    "risk_level": "LOW"
                }
                
                # Process violations for this driver
                hourly_rate = len(driver_violations) / (1 if timeframe == "1h" else 24)
                for violation in driver_violations:
                    v_type = violation.get("violation_type", "UNKNOWN")
                    severity = violation.get("severity", "LOW")
                    driver_summary["violation_types"][v_type] = (
                        driver_summary["violation_types"].get(v_type, 0) + 1
                    )
                    driver_summary["severity_counts"][severity] += 1
                
                # Set driver risk level
                if (driver_summary["severity_counts"]["HIGH"] > 0 or 
                    hourly_rate > 10):
                    driver_summary["risk_level"] = "HIGH"
                elif (driver_summary["severity_counts"]["MEDIUM"] > 3 or 
                      hourly_rate > 5):
                    driver_summary["risk_level"] = "MEDIUM"
                
                analysis["drivers"].append(driver_summary)
            
            # Sort drivers by violation count
            analysis["drivers"].sort(
                key=lambda x: (
                    x["severity_counts"]["HIGH"],
                    x["severity_counts"]["MEDIUM"],
                    x["total_violations"]
                ),
                reverse=True
            )
        else:
            # Single driver processing (existing logic)
            driver_info = next((v.get("driver_info", {}) for v in violations_list if v.get("driver_info")), {})
            analysis["driver_info"] = {
                "uuid": driver_uuid,
                "name": driver_info.get("name", "Unknown Driver"),
                "status": driver_info.get("status", "ACTIVE"),
                "last_known_activity": driver_info.get("last_activity", start_time.isoformat()),
                "data_status": "Active" if violations_list or events_list else "No Recent Activity"
            }

        # Process all violations for statistics
        if violations_list:
            for violation in violations_list:
                v_type = violation.get("violation_type", "UNKNOWN")
                analysis["violation_types"][v_type] = (
                    analysis["violation_types"].get(v_type, 0) + 1
                )
                
                severity = violation.get("severity", "LOW")
                analysis["stats"]["severity_counts"][severity] += 1
                
                event_time = violation.get("event_time")
                if event_time:
                    if not analysis["stats"]["last_event_time"] or event_time > analysis["stats"]["last_event_time"]:
                        analysis["stats"]["last_event_time"] = event_time
            
            # Calculate hourly rate
            hourly_rate = len(violations_list) / hours
            analysis["stats"]["hourly_rate"] = round(hourly_rate, 2)
            
            # Overall risk level
            high_severity = analysis["stats"]["severity_counts"]["HIGH"]
            medium_severity = analysis["stats"]["severity_counts"]["MEDIUM"]
            
            if high_severity > 0 or hourly_rate > 10:
                analysis["risk_level"] = "HIGH"
            elif medium_severity > 3 or hourly_rate > 5:
                analysis["risk_level"] = "MEDIUM"
        else:
            analysis["stats"]["data_summary"]["reason"] = "No violations found in specified timeframe"
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in perform_real_time_analysis: {str(e)}", exc_info=True)
        raise