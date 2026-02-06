"""
File upload endpoint
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
import aiofiles
import uuid
from pathlib import Path
from datetime import datetime
import logging

from database import get_db, Document, ProcessingLog
from config import settings
from schemas import DocumentUploadResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for processing
    
    - Validates file type and size
    - Saves file to upload directory
    - Creates database record
    """
    try:
        # Validate file extension
        if not settings.validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = Path(settings.UPLOAD_DIR) / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"File saved: {unique_filename} ({file_size} bytes)")
        
        # Determine file type
        file_type = "pdf" if file_extension.lower() == ".pdf" else "image"
        
        # Create database record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file_type,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Log upload event
        log_entry = ProcessingLog(
            document_id=document.id,
            event_type="upload",
            message=f"Document uploaded: {file.filename}",
            details={
                "filename": unique_filename,
                "size": file_size,
                "type": file_type
            },
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        await db.commit()
        
        logger.info(f"Document record created: ID={document.id}")
        
        return DocumentUploadResponse(
            document_id=document.id,
            filename=unique_filename,
            file_size=file_size,
            status="pending",
            message="Document uploaded successfully. Ready for processing."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )