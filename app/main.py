from fastapi import FastAPI
from app.api.router import api_router
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.core.config import settings
from app.utils.font_manager import ensure_fonts_exist
from app.utils.assets.logo_manager import ensure_logo_exists
import uvicorn

app = FastAPI(title="Predictive Analytics API", version="1.0")

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    ensure_fonts_exist()  # Ensure fonts are available
    ensure_logo_exists()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Predictive Analytics API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=7777, reload=True)