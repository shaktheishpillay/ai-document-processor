"""
Data export endpoint - FIXED for correct field names
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import csv
import json
from pathlib import Path
from datetime import datetime
import uuid
import logging

from database import get_db, Document
from config import settings
from schemas import ExportRequest, ExportResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/export", response_model=ExportResponse)
async def export_documents(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Export processed documents to clean CSV"""
    try:
        # Get documents
        query = select(Document).where(Document.status == "completed")
        if request.document_ids:
            query = query.where(Document.id.in_(request.document_ids))
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found")
        
        # Generate export
        export_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.csv"
        export_path = Path(settings.EXPORT_DIR) / filename
        
        # Create clean CSV with extracted fields
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Document ID',
                'Original Filename', 
                'Document Type',
                'Field Name',
                'Field Value',
                'Confidence Score',
                'Processing Date'
            ])
            
            # Write data - one row per extracted field
            for doc in documents:
                if doc.extracted_data and 'fields' in doc.extracted_data:
                    for field in doc.extracted_data['fields']:
                        writer.writerow([
                            doc.id,
                            doc.original_filename,
                            doc.document_type or 'Unknown',
                            field.get('field_name', ''),
                            field.get('value', ''),  # FIXED: was 'field_value', should be 'value'
                            field.get('confidence', 0),
                            doc.processed_at.strftime('%Y-%m-%d %H:%M:%S') if doc.processed_at else ''
                        ])
                else:
                    # If no extracted fields, just show document info
                    writer.writerow([
                        doc.id,
                        doc.original_filename,
                        doc.document_type or 'Unknown',
                        'No data',
                        'No data extracted',
                        doc.confidence_score or 0,
                        doc.processed_at.strftime('%Y-%m-%d %H:%M:%S') if doc.processed_at else ''
                    ])
        
        logger.info(f"Exported {len(documents)} documents to {filename}")
        
        return ExportResponse(
            export_id=export_id,
            filename=filename,
            format="csv",
            record_count=len(documents),
            download_url=f"/exports/{filename}",
            created_at=datetime.now(),
            message=f"Successfully exported {len(documents)} documents"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
