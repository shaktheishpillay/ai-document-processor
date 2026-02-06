"""
Pydantic schemas for request/response validation
COMPLETE VERSION - All schemas included
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# Enums
class DocumentType(str, Enum):
    """Document type enumeration"""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    FORM = "form"
    CONTRACT = "contract"
    BANK_STATEMENT = "bank_statement"
    ID_DOCUMENT = "id_document"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Data Models
class ExtractedField(BaseModel):
    """Single extracted field"""
    field_name: str
    field_value: Any
    confidence: float = 0.0
    field_type: Optional[str] = None


class ExtractedData(BaseModel):
    """Complete extracted data structure"""
    fields: List[ExtractedField]
    raw_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None


# Request Models
class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    document_id: int
    filename: str
    file_size: int
    status: str
    message: str


class ProcessDocumentRequest(BaseModel):
    """Request model for document processing"""
    document_id: int
    extraction_type: Optional[str] = "auto"
    enable_validation: Optional[bool] = True


class ProcessDocumentResponse(BaseModel):
    """Response model for document processing"""
    document_id: int
    status: str
    document_type: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    validation_errors: Optional[List[Any]] = None
    message: str


class DocumentResponse(BaseModel):
    """Response model for document retrieval"""
    id: int
    filename: str
    original_filename: str
    file_type: str
    status: str
    document_type: Optional[str] = None
    confidence_score: Optional[float] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_errors: Optional[Dict[str, Any]] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ExportRequest(BaseModel):
    """Request model for data export"""
    document_ids: Optional[List[int]] = None
    export_format: str = "csv"
    include_validation_errors: bool = False
    include_confidence_scores: bool = True


class ExportResponse(BaseModel):
    """Response model for data export"""
    export_id: str
    filename: str
    format: str
    record_count: int
    download_url: str
    created_at: datetime
    message: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: datetime
    database: str
    storage: Dict[str, str]
    api_version: str


class BatchProcessRequest(BaseModel):
    """Request model for batch processing"""
    document_ids: List[int]
    extraction_type: Optional[str] = "auto"


class BatchProcessResponse(BaseModel):
    """Response model for batch processing"""
    total_documents: int
    successful: int
    failed: int
    processing_time: float
    results: List[ProcessDocumentResponse]


class DocumentDetail(BaseModel):
    """Detailed document information"""
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    document_type: Optional[str] = None
    confidence_score: Optional[float] = None
    extracted_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentList(BaseModel):
    """List of documents with pagination"""
    documents: List[DocumentDetail]
    total: int
    page: int
    page_size: int


class ProcessingStatistics(BaseModel):
    """Processing statistics"""
    total_documents: int
    pending: int
    processing: int
    completed: int
    failed: int
    average_processing_time: Optional[float] = None
    total_processing_time: Optional[float] = None
