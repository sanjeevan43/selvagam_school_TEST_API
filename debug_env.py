from app.core.config import get_settings
settings = get_settings()
print(f"DB_HOST: {settings.DB_HOST}")
print(f"DB_NAME: {settings.DB_NAME}")
print(f"API_PORT: {settings.API_PORT}")
