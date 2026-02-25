from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    # Database Configuration
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "school_DB"
    
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "https://api.selvagam.com"]
    
    # FCM Configuration
    FCM_SERVER_KEY: str = "your-fcm-server-key"
    
    # Geofence Notification Configuration
    GEOFENCE_RADIUS: int = 500
    # Upload Configuration
    UPLOAD_DIR: str = "uploads"
    BASE_URL: str = "https://api.selvagam.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env without failing


@lru_cache()
def get_settings():
    return Settings()
