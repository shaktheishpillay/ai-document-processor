"""
AI-Powered Document Processing System
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from config import settings
from database import init_db
import upload, process, export, documents, health

# Ensure log directory exists before configuring logging
Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(settings.LOG_DIR) / 'app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application"""
    # Startup
    logger.info("Starting AI Document Processor...")
    await init_db()
    
    # Create necessary directories
    for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, 
                      settings.EXPORT_DIR, settings.LOG_DIR]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    logger.info("Application started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title="AI Document Processor",
    description="Automated document data extraction and processing system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "error_type": type(exc).__name__
        }
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(process.router, prefix="/api", tags=["Process"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])


# Create directories for static files before mounting
for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.EXPORT_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Mount static files for uploads (if needed for download)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/exports", StaticFiles(directory=settings.EXPORT_DIR), name="exports")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Document Processor API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
