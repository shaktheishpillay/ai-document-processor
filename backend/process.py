"""
Document processing endpoint
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import logging
import json

from database import get_db, Document, ProcessingLog
from schemas import ProcessDocumentResponse, ProcessingStatus
from document_processor import document_processor

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_document_task(document_id: int, db: AsyncSession):
    """
    Background task to process document
    """
    try:
        # Get document from database
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            logger.error(f"Document not found: {document_id}")
            return
        
        # Update status to processing
        document.status = "processing"
        await db.commit()
        
        # Process document
        result = await document_processor.process_document(
            document.file_path,
            document.file_type
        )
        
        if result["success"]:
            # Update document with results
            document.status = "completed"
            document.document_type = result["document_type"]
            document.extracted_data = result["extracted_data"]
            document.confidence_score = result["confidence_score"]
            document.processing_time = result["processing_time"]
            document.validation_errors = result.get("validation_errors", [])
            document.processed_at = datetime.utcnow()
            
            # Log success
            log_entry = ProcessingLog(
                document_id=document_id,
                event_type="extraction",
                message="Document processed successfully",
                details={
                    "document_type": result["document_type"],
                    "confidence": result["confidence_score"],
                    "processing_time": result["processing_time"]
                },
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            
            logger.info(
                f"Document {document_id} processed successfully "
                f"({result['processing_time']:.2f}s)"
            )
        else:
            # Update status to failed
            document.status = "failed"
            document.error_message = result.get("error", "Unknown error")
            document.retry_count += 1
            
            # Log error
            log_entry = ProcessingLog(
                document_id=document_id,
                event_type="error",
                message=f"Processing failed: {result.get('error')}",
                details={"error": result.get("error")},
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            
            logger.error(f"Document {document_id} processing failed: {result.get('error')}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Processing task failed for document {document_id}: {str(e)}", exc_info=True)
        # Update document status to failed
        try:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            if document:
                document.status = "failed"
                document.error_message = str(e)
                await db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update document status: {str(update_error)}")


@router.post("/process/{document_id}", response_model=ProcessDocumentResponse)
async def process_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start processing a document
    
    - Extracts data from document
    - Categorizes document type
    - Validates extracted data
    - Returns structured results
    """
    try:
        # Get document from database
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )
        
        if document.status == "processing":
            raise HTTPException(
                status_code=400,
                detail="Document is already being processed"
            )
        
        # Start background processing
        background_tasks.add_task(process_document_task, document_id, db)
        
        return ProcessDocumentResponse(
            document_id=document_id,
            status=ProcessingStatus.PROCESSING,
            document_type=None,
            extracted_data=None,
            processing_time=0.0,
            confidence_score=None,
            validation_errors=None,
            message="Document processing started. Check status for results."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process initiation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/process/{document_id}/status", response_model=ProcessDocumentResponse)
async def get_processing_status(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get processing status and results for a document
    """
    try:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Parse extracted data if available
        extracted_data = None
        if document.extracted_data and document.status == "completed":
            extracted_data = document.extracted_data
        
        return ProcessDocumentResponse(
            document_id=document.id,
            status=ProcessingStatus(document.status),
            document_type=document.document_type,
            extracted_data=extracted_data,
            processing_time=document.processing_time or 0.0,
            confidence_score=document.confidence_score,
            validation_errors=document.validation_errors or [],
            message=f"Status: {document.status}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )