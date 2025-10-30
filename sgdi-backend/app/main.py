from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import logging
from pathlib import Path

from .core.config import settings
from .core.database import get_db
from .core.logging_config import setup_logging

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="SGDI - Sistema de Gestión Documental Integrado",
    description="API REST para gestión documental integrada",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False  # Deshabilitar redirecciones automáticas de /path a /path/
)

# Configure CORS
# Para desarrollo, usar "*" es más simple. En producción, especificar orígenes exactos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes en desarrollo
    allow_credentials=False,  # No usar credentials (usamos Authorization Bearer)
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Permitir todos los headers
    expose_headers=["Content-Disposition", "X-Checksum-Sha256", "X-File-Id", "X-Request-Id"],
)

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies:
    - Database connectivity
    - Storage writability
    """
    health_status = {
        "status": "healthy",
        "database": False,
        "storage_writable": False
    }

    # Check database connectivity
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        health_status["database"] = True
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        health_status["status"] = "unhealthy"

    # Check storage writability
    try:
        storage_path = Path(settings.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        # Test write access
        test_file = storage_path / ".health_check"
        test_file.write_text("health_check")
        test_file.unlink()

        health_status["storage_writable"] = True
    except Exception as e:
        logging.error(f"Storage health check failed: {e}")
        health_status["status"] = "unhealthy"

    return health_status

@app.get("/info")
async def info():
    """
    Application information endpoint
    """
    # Try to read version from file
    version = "1.0.0"
    try:
        version_file = Path(__file__).parent / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
    except Exception:
        pass

    # Get build time (approximated by startup time)
    import time
    build_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return {
        "name": "SGDI - Sistema de Gestión Documental Integrado",
        "version": version,
        "build_time": build_time,
        "description": "API REST para gestión documental integrada",
        "docs_url": "/docs",
        "health_url": "/health"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SGDI API", "version": "1.0.0", "docs": "/docs"}

# Include routers
from .routes import (
    admin_routes,
    auth_routes,
    users_routes,
    dependencies_routes,
    folders_routes,
    files_routes,
    audit_routes,
    backups_routes
)

# Initialize scheduler
from .services.scheduler_service import scheduler_service
from .tasks.monthly_folders import scheduled_monthly_folders

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and add jobs on startup"""
    scheduler_service.init_scheduler()
    scheduler_service.add_monthly_folders_job(scheduled_monthly_folders)
    scheduler_service.start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on app shutdown"""
    scheduler_service.shutdown_scheduler()

app.include_router(admin_routes.router, prefix="/admin", tags=["admin"])
app.include_router(auth_routes.router, prefix="/auth", tags=["authentication"])
app.include_router(users_routes.router, prefix="/users", tags=["users"])
app.include_router(dependencies_routes.router, prefix="/dependencies", tags=["dependencies"])
app.include_router(folders_routes.router, prefix="/folders", tags=["folders"])
app.include_router(files_routes.router, prefix="/files", tags=["files"])
app.include_router(audit_routes.router, prefix="/audit", tags=["audit"])
app.include_router(backups_routes.router, prefix="/admin/backups", tags=["backups"])
