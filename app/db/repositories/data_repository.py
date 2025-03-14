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
        try:
            db = await self.get_database()
            query = {}
            
            # Log connection details
            logger.debug(f"Fetching vehicle events from database: {db.name}")
            
            if time_range:
                # Try multiple timestamp field names
                query["$or"] = [
                    {"timestamp": time_range},
                    {"event_time": time_range},
                    {"created_at": time_range}
                ]
            if vehicle_uuid:
                query["$or"] = [
                    {"vehicle.uuid": vehicle_uuid},
                    {"vehicle_uuid": vehicle_uuid},
                    {"driver_uuid": vehicle_uuid}
                ]
                
            # Log query details
            logger.debug(f"Vehicle events query: {query}")
            logger.debug(f"Time range: {time_range}")
            
            try:
                # List all collections for debugging
                collections = await db.list_collection_names()
                logger.debug(f"Available collections: {collections}")
                
                if 'vehicleevents' not in collections:
                    # Try alternate collection names
                    alt_collections = ['vehicle_events', 'events', 'tracking']
                    for coll in alt_collections:
                        if coll in collections:
                            logger.info(f"Using alternate collection: {coll}")
                            result = await db[coll].find(query).limit(limit).to_list(length=limit)
                            if result:
                                return result
                    
                    logger.error("No suitable events collection found")
                    return []
                
                # Get sample document for field validation
                sample = await db.vehicleevents.find_one()
                if sample:
                    logger.debug(f"Sample document fields: {list(sample.keys())}")
                
                count = await db.vehicleevents.count_documents(query)
                logger.info(f"Found {count} matching vehicle events")
                
                results = await db.vehicleevents.find(query).limit(limit).to_list(length=limit)
                logger.debug(f"Retrieved {len(results)} vehicle events")
                return results
                
            except Exception as e:
                logger.error(f"Database query error: {str(e)}", exc_info=True)
                return []
                
        except Exception as e:
            logger.error(f"Error in get_vehicle_events: {str(e)}", exc_info=True)
            return []

    async def get_violations(self, start_date: datetime = None, end_date: datetime = None, 
                           time_range: Dict = None, filters: Dict = None, limit: int = 1000):
        try:
            db = await self.get_database()
            query = {}
            
            logger.debug(f"Connected to database: {db.name}")
            
            # Time range query
            if start_date and end_date:
                query["$or"] = [
                    {"timestamp": {"$gte": start_date, "$lte": end_date}},
                    {"event_time": {"$gte": start_date, "$lte": end_date}},
                    {"created_at": {"$gte": start_date, "$lte": end_date}}
                ]
            elif time_range:
                query["$or"] = [
                    {"timestamp": time_range},
                    {"event_time": time_range},
                    {"created_at": time_range}
                ]

            # Handle driver information lookup
            pipeline = [
                {"$match": query},
                {
                    "$lookup": {
                        "from": "drivers",
                        "localField": "driver_uuid",
                        "foreignField": "driver_id",
                        "as": "driver_info"
                    }
                },
                {
                    "$addFields": {
                        "driver_name": {
                            "$cond": [
                                {"$gt": [{"$size": "$driver_info"}, 0]},
                                {"$arrayElemAt": ["$driver_info.name", 0]},
                                {
                                    "$cond": [
                                        {"$eq": ["$driver_uuid", "unknown"]},
                                        "Unassigned Driver",
                                        {"$concat": ["Driver ", {"$toString": "$driver_uuid"}]}
                                    ]
                                }
                            ]
                        }
                    }
                }
            ]
            
            if filters:
                # Handle driver UUID filter
                if "driver_uuid" in filters:
                    query["$or"] = query.get("$or", []) + [
                        {"driver_uuid": filters["driver_uuid"]},
                        {"driver.uuid": filters["driver_uuid"]},
                        {"vehicle.driver_uuid": filters["driver_uuid"]}
                    ]
                    del filters["driver_uuid"]
                pipeline[0]["$match"].update(filters)
            
            logger.debug(f"Violations pipeline: {pipeline}")
            
            try:
                collections = await db.list_collection_names()
                logger.debug(f"Available collections: {collections}")
                
                # Try multiple collection names
                collection_names = ['violations', 'violation_events', 'driver_violations']
                
                for coll_name in collection_names:
                    if coll_name in collections:
                        logger.debug(f"Checking collection: {coll_name}")
                        count = await db[coll_name].count_documents(query)
                        if count > 0:
                            logger.info(f"Found {count} documents in {coll_name}")
                            results = await db[coll_name].aggregate(pipeline).to_list(length=limit)
                            return results
                
                logger.warning("No violations found in any collection")
                return []
                
            except Exception as e:
                logger.error(f"Database query error: {str(e)}", exc_info=True)
                return []
                
        except Exception as e:
            logger.error(f"Error in get_violations: {str(e)}", exc_info=True)
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