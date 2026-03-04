from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.core.config import get_settings
import uvicorn
import os
import logging

settings = get_settings()
logging.basicConfig(level=logging.INFO)

# FastAPI app
app = FastAPI(
    title="School Transport Management API",
    version="1.0.0",
    servers=[
        {"url": f"http://localhost:{settings.API_PORT}", "description": "New Test API Server"}
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Authentication", "description": "Login and authentication"},
        {"name": "Admins", "description": "System administrators"},
        {"name": "Parents", "description": "Parent/guardian management"},
        {"name": "Drivers", "description": "Bus driver management"},
        {"name": "Students", "description": "Student transport management"},
        {"name": "Buses", "description": "School bus management"},
        {"name": "Routes", "description": "Bus route management"},
        {"name": "Route Stops", "description": "Bus stop management"},
        {"name": "Classes", "description": "School class management"},
        {"name": "Trips", "description": "Daily bus trip management"},
        {"name": "Bus Tracking", "description": "Real-time bus tracking"},
        {"name": "Proximity Alerts", "description": "Advanced geofence-based notification logic"},
        {"name": "FCM Tokens", "description": "Push notifications"},
        {"name": "Error Handling", "description": "Error logs"}
    ],
    contact={
        "name": "API Support",
        "email": "admin@school.com",
    }
)

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as main_router
from app.api.notification_routes import router as notification_router

# Include routers
app.include_router(main_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")

# Create upload directory if it doesn't exist
if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR)

# Mount static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "School Transport Management API",
        "version": "1.0.0",
        "features": {
            "total_endpoints": "60+",
            "status_updates": "PUT /entity/{id}/status",
            "id_fields_first": "All responses show ID fields first",
            "authentication": "Password-based for all user types",
            "status_example": '{"status": "ACTIVE"}'
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    try:
        from app.core.database import get_db
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"}
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    import traceback
    
    # Log the actual error for debugging
    logging.error(f"Unhandled exception: {exc}")
    logging.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred",
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
