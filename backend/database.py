"""
Database configuration and initialization
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()


class Document(Base):
    """Document model for storing processed documents"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    file_type = Column(String)
    
    # Processing metadata
    status = Column(String, default="pending")  # pending, processing, completed, failed
    document_type = Column(String)  # invoice, receipt, form, etc.
    confidence_score = Column(Float)
    processing_time = Column(Float)  # in seconds
    
    # Extracted data
    extracted_data = Column(JSON)
    validation_errors = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Export tracking
    exported = Column(String, default="false")
    export_path = Column(String)
    
    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)


class ProcessingLog(Base):
    """Log table for tracking processing events"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer)
    event_type = Column(String)  # upload, extraction, validation, export, error
    message = Column(Text)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


async def get_db() -> AsyncSession:
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()