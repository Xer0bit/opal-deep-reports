import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_PREFIX: str = "/api/v1"
    
    # MongoDB Settings
    MONGODB_URL: str = "mongodb://opal:4411opal%40stms%23%234411@3.144.134.141:27017/opal_server?authSource=admin"
    MONGODB_DB_NAME: str = "opal_server"
    DATABASE_URL: str = MONGODB_URL
    
    # Security Settings
    SECRET_KEY: str = "default_secret_key"
    
    # Application Settings
    PROJECT_NAME: str = "Predictive Analytics API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"
    
    # ML Model Settings
    PREDICTION_MODEL_PATH: str = "./models/risk_prediction"
    ML_MODEL_VERSION: str = "1.0"
    
    # Analysis Settings
    VIOLATION_TRENDS_ANALYSIS_INTERVAL: str = "daily"
    RISK_ASSESSMENT_THRESHOLD: int = 60
    CACHE_EXPIRY: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()