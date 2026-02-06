"""
Documents listing and management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
import logging

from database import get_db, Document
from schemas import DocumentDetail, DocumentList, ProcessingStatistics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/documents", response_model=DocumentList)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all documents with pagination and filtering
    """
    try:
        # Build query
        query = select(Document)
        
        # Apply filters
        if status:
            query = query.where(Document.status == status)
        if document_type:
            query = query.where(Document.document_type == document_type)
        
        # Order by created_at descending
        query = query.order_by(Document.created_at.desc())
        
        # Get total count
        count_query = select(func.count()).select_from(Document)
        if status:
            count_query = count_query.where(Document.status == status)
        if document_type:
            count_query = count_query.where(Document.document_type == document_type)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return DocumentList(
            total=total,
            documents=[DocumentDetail.model_validate(doc) for doc in documents],
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"List documents failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific document
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
        
        return DocumentDetail.model_validate(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document: {str(e)}"
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document and its associated files
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
        
        # Delete from database
        await db.execute(
            delete(Document).where(Document.id == document_id)
        )
        await db.commit()
        
        # TODO: Delete physical file
        # Path(document.file_path).unlink(missing_ok=True)
        
        logger.info(f"Document {document_id} deleted")
        
        return {"message": "Document deleted successfully", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/statistics", response_model=ProcessingStatistics)
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get processing statistics and metrics
    """
    try:
        # Total documents
        total_result = await db.execute(select(func.count()).select_from(Document))
        total_documents = total_result.scalar()
        
        # Documents by status
        processed_result = await db.execute(
            select(func.count()).select_from(Document).where(Document.status == "completed")
        )
        processed_documents = processed_result.scalar()
        
        failed_result = await db.execute(
            select(func.count()).select_from(Document).where(Document.status == "failed")
        )
        failed_documents = failed_result.scalar()
        
        pending_result = await db.execute(
            select(func.count()).select_from(Document).where(Document.status == "pending")
        )
        pending_documents = pending_result.scalar()
        
        # Average processing time
        avg_time_result = await db.execute(
            select(func.avg(Document.processing_time)).where(
                Document.processing_time.isnot(None)
            )
        )
        avg_processing_time = avg_time_result.scalar() or 0.0
        
        # Average confidence score
        avg_confidence_result = await db.execute(
            select(func.avg(Document.confidence_score)).where(
                Document.confidence_score.isnot(None)
            )
        )
        avg_confidence_score = avg_confidence_result.scalar() or 0.0
        
        # Documents by type
        type_result = await db.execute(
            select(Document.document_type, func.count()).
            where(Document.document_type.isnot(None)).
            group_by(Document.document_type)
        )
        documents_by_type = {row[0]: row[1] for row in type_result.all()}
        
        # Estimate time saved (assuming 5 minutes manual entry per document)
        total_time_saved = processed_documents * 5 / 60  # hours
        
        return ProcessingStatistics(
            total_documents=total_documents,
            processed_documents=processed_documents,
            failed_documents=failed_documents,
            pending_documents=pending_documents,
            average_processing_time=round(avg_processing_time, 2),
            average_confidence_score=round(avg_confidence_score, 3),
            documents_by_type=documents_by_type,
            total_time_saved=round(total_time_saved, 2)
        )
        
    except Exception as e:
        logger.error(f"Get statistics failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )