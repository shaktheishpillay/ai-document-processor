"""
Health check endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from pathlib import Path

from database import get_db
from config import settings
from schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint
    Returns system status and availability
    """
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # Check storage directories
    storage_status = {}
    for name, path in [
        ("uploads", settings.UPLOAD_DIR),
        ("processed", settings.PROCESSED_DIR),
        ("exports", settings.EXPORT_DIR),
        ("logs", settings.LOG_DIR)
    ]:
        storage_status[name] = "available" if Path(path).exists() else "unavailable"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.utcnow(),
        database=db_status,
        storage=storage_status,
        api_version="1.0.0"
    )