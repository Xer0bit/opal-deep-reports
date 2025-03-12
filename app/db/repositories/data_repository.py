from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.models.schemas import VehicleEvent, Violation
from ..mongodb import get_database
from app.core.logger import get_logger

logger = get_logger(__name__)

class DataRepository:
    def __init__(self, db_url: str = None, db_name: str = None):
        self.db_url = db_url
        self.db_name = db_name
        self.db = None
        self.client = None

    async def get_database(self):
        if self.db is None:
            if self.db_url and self.db_name:
                self.client = AsyncIOMotorClient(self.db_url)
                self.db = self.client[self.db_name]
            else:
                self.db = await get_database()
        return self.db

    async def get_vehicle_events(self, time_range: Dict = None, vehicle_uuid: str = None, limit: int = 1000):
        db = await self.get_database()
        query = {}
        if time_range:
            query["timestamp"] = time_range
        if vehicle_uuid:
            query["vehicle.uuid"] = vehicle_uuid
        try:
            cursor = db.vehicleevents.find(query).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error fetching vehicle events: {str(e)}")
            return []

    async def get_violations(self, start_date: datetime = None, end_date: datetime = None, 
                           time_range: Dict = None, filters: Dict = None, limit: int = 1000):
        db = await self.get_database()
        query = {}
        
        if start_date and end_date:
            query["timestamp"] = {"$gte": start_date, "$lte": end_date}
        elif time_range:
            query["timestamp"] = time_range
        if filters:
            query.update(filters)
            
        try:
            cursor = db.violations.find(query).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error fetching violations: {str(e)}")
            return []

    async def get_violation_trends(self, group_by: str = "hour", start_date: datetime = None, 
                                 end_date: datetime = None, driver_uuid: str = None):
        """
        Get violation trends grouped by time period with optional driver filter
        """
        try:
            db = await self.get_database()
            if db is None:
                logger.error("Database connection not established")
                return []
            
            # Ensure proper datetime objects
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Base match condition
            match_condition = {
                "event_time": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            
            # Add driver filter if provided
            if driver_uuid:
                match_condition["driver_uuid"] = driver_uuid
                
            logger.info(f"Querying violations from {start_date} to {end_date}"
                       f"{' for driver ' + driver_uuid if driver_uuid else ''}")

            # Time-based grouping
            time_formats = {
                "hour": {"$dateToString": {"format": "%Y-%m-%d %H:00", "date": "$event_time"}},
                "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$event_time"}},
                "week": {"$dateToString": {"format": "%Y-%U", "date": "$event_time"}},
                "month": {"$dateToString": {"format": "%Y-%m", "date": "$event_time"}}
            }
            
            time_format = time_formats.get(group_by, time_formats["day"])
            
            pipeline = [
                {"$match": match_condition},
                {"$group": {
                    "_id": {
                        "time_period": time_format,
                        "violation_type": "$violation_type",
                        "driver_uuid": "$driver_uuid",
                        "driver_name": "$driver_name"
                    },
                    "count": {"$sum": 1},
                    "high_severity_count": {
                        "$sum": {"$cond": [{"$eq": ["$severity", "HIGH"]}, 1, 0]}
                    }
                }},
                {"$sort": {
                    "_id.time_period": 1,
                    "_id.driver_name": 1
                }}
            ]
            
            logger.debug(f"Executing pipeline: {pipeline}")
            results = await db.violations.aggregate(pipeline).to_list(length=None)
            logger.info(f"Found {len(results)} trend records")
            
            return results

        except Exception as e:
            logger.error(f"Error in get_violation_trends: {str(e)}", exc_info=True)
            raise

    async def get_driver_risk_data(self, driver_uuid: str = None, days: int = 90):
        """
        Get data needed for driver risk assessment
        """
        try:
            logger.info(f"Fetching driver risk data for past {days} days")
            
            db = await self.get_database()
            start_date = datetime.now() - timedelta(days=days)
            
            query = {"event_time": {"$gte": start_date}}
            if driver_uuid:
                query["driver_uuid"] = driver_uuid
            
            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$driver_uuid",
                    "name": {"$first": "$driver_name"},
                    "violation_count": {"$sum": 1},
                    "violation_types": {"$addToSet": "$violation_type"},
                    "avg_severity": {"$avg": {"$switch": {
                        "branches": [
                            {"case": {"$eq": ["$severity", "HIGH"]}, "then": 3},
                            {"case": {"$eq": ["$severity", "MEDIUM"]}, "then": 2}
                        ],
                        "default": 1
                    }}},
                    "last_violation": {"$max": "$event_time"},
                    "max_speed": {"$max": "$telemetry.speed"},
                    "vehicle_license": {"$first": "$vehicle_license"}
                }},
                {"$sort": {"violation_count": -1}}
            ]
            
            logger.debug(f"Executing pipeline: {pipeline}")
            driver_stats = await db.violations.aggregate(pipeline).to_list(length=None)
            logger.info(f"Retrieved stats for {len(driver_stats)} drivers")
            
            return driver_stats
            
        except Exception as e:
            logger.error(f"Error in get_driver_risk_data: {str(e)}", exc_info=True)
            raise

    async def get_violation_statistics(self) -> Dict[str, Any]:
        db = await self.get_database()
        pipeline = [
            {
                "$group": {
                    "_id": "$violation_type",
                    "count": {"$sum": 1},
                    "average_risk": {"$avg": "$risk_score"}
                }
            }
        ]
        result = await db.violations.aggregate(pipeline).to_list(length=None)
        return {doc["_id"]: {"count": doc["count"], "average_risk": doc["average_risk"]} 
                for doc in result}

    async def save_violation(self, violation_data: Dict[str, Any]) -> str:
        db = await self.get_database()
        result = await db.violations.insert_one(violation_data)
        return str(result.inserted_id)

    def close(self):
        if self.client:
            self.client.close()