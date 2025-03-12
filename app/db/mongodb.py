from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..core.config import settings
from fastapi import HTTPException
import os

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None

async def connect_to_mongo():
    global client, db
    try:
        client = AsyncIOMotorClient(settings.DATABASE_URL)
        db = client["opal_server"]  # Use the correct database name
        await db.command('ping')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to database: {str(e)}")

async def close_mongo_connection():
    global client
    if client is not None:
        client.close()

async def get_database() -> AsyncIOMotorDatabase:
    if db is None:
        await connect_to_mongo()
    return db