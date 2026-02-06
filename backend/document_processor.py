"""
Document processing service using OpenAI Vision API
Handles document extraction, OCR, and data structuring
"""
import base64
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from openai import AsyncOpenAI
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path

from config import settings
from schemas import DocumentType, ExtractedField, ExtractedData

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class DocumentProcessor:
    """Main document processing class"""
    
    def __init__(self):
        self.client = client
        
    async def process_document(
        self,
        file_path: str,
        file_type: str
    ) -> Dict[str, Any]:
        """
        Process a document and extract structured data
        
        Args:
            file_path: Path to the document file
            file_type: Type of file (pdf, image)
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        start_time = time.time()
        
        try:
            # Convert document to image if needed
            image_data = await self._prepare_image(file_path, file_type)
            
            # Extract data using Vision API
            extracted_data = await self._extract_with_vision(image_data)
            
            # Categorize document type
            document_type = self._categorize_document(extracted_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(extracted_data)
            
            # Validate extracted data
            validation_errors = self._validate_data(extracted_data, document_type)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "document_type": document_type,
                "extracted_data": extracted_data,
                "confidence_score": confidence_score,
                "processing_time": processing_time,
                "validation_errors": validation_errors
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _prepare_image(self, file_path: str, file_type: str) -> str:
        """
        Convert document to base64 encoded image
        
        Args:
            file_path: Path to document
            file_type: File type
            
        Returns:
            Base64 encoded image string
        """
        try:
            if file_type == "pdf":
                # Convert PDF first page to image
                images = convert_from_path(file_path, first_page=1, last_page=1, dpi=300)
                if images:
                    # Save temporarily
                    temp_path = file_path.replace('.pdf', '_temp.jpg')
                    images[0].save(temp_path, 'JPEG')
                    file_path = temp_path
                else:
                    raise ValueError("Could not convert PDF to image")
            
            # Read and encode image
            with open(file_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            return image_data
            
        except Exception as e:
            logger.error(f"Image preparation failed: {str(e)}")
            raise
    
    async def _extract_with_vision(self, image_data: str) -> Dict[str, Any]:
        """
        Extract data from image using OpenAI Vision API
        
        Args:
            image_data: Base64 encoded image
            
        Returns:
            Extracted structured data
        """
        try:
            prompt = """
You are an expert data extraction system. Analyze this document image and extract ALL relevant information in a structured format.

EXTRACTION REQUIREMENTS:
1. Identify the document type (invoice, receipt, purchase order, bill, statement, form, contract, or other)
2. Extract ALL text fields with their labels
3. For each field, determine:
   - Field name/label
   - Field value
   - Data type (text, number, date, currency, email, phone, address)
   - Your confidence in the extraction (0.0 to 1.0)

4. Common fields to look for:
   - Document identifiers: invoice number, order number, reference number
   - Dates: invoice date, due date, order date
   - Parties: vendor/seller name, customer/buyer name, addresses, contact info
   - Financial: amounts, subtotals, tax, total, currency
   - Items: line items with descriptions, quantities, unit prices, amounts
   - Payment: payment terms, methods, account numbers
   - Additional: notes, terms and conditions, signatures

5. For tables/line items, extract each row with all columns

RESPONSE FORMAT (JSON only, no markdown):
{
  "document_type": "invoice|receipt|purchase_order|bill|statement|form|contract|other",
  "confidence_score": 0.0-1.0,
  "fields": [
    {
      "field_name": "string",
      "value": "any",
      "confidence": 0.0-1.0,
      "data_type": "text|number|date|currency|email|phone|address"
    }
  ],
  "line_items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "amount": number,
      "confidence": 0.0-1.0
    }
  ],
  "raw_text": "complete extracted text for reference",
  "metadata": {
    "has_logo": boolean,
    "has_signature": boolean,
    "quality_score": 0.0-1.0,
    "language": "string"
  }
}

Extract as much information as possible. Be thorough and accurate.
"""
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            extracted_data = json.loads(content.strip())
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Vision API extraction failed: {str(e)}")
            raise
    
    def _categorize_document(self, extracted_data: Dict[str, Any]) -> str:
        """
        Categorize document type based on extracted data
        
        Args:
            extracted_data: Extracted document data
            
        Returns:
            Document type string
        """
        # First check if document_type was already identified
        if "document_type" in extracted_data:
            return extracted_data["document_type"]
        
        # Fallback categorization based on fields
        fields = extracted_data.get("fields", [])
        field_names = [f.get("field_name", "").lower() for f in fields]
        
        if any(term in " ".join(field_names) for term in ["invoice", "inv no", "invoice number"]):
            return "invoice"
        elif any(term in " ".join(field_names) for term in ["receipt", "transaction"]):
            return "receipt"
        elif any(term in " ".join(field_names) for term in ["purchase order", "po number"]):
            return "purchase_order"
        elif any(term in " ".join(field_names) for term in ["bill", "billing"]):
            return "bill"
        else:
            return "other"
    
    def _calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """
        Calculate overall confidence score
        
        Args:
            extracted_data: Extracted document data
            
        Returns:
            Confidence score between 0 and 1
        """
        if "confidence_score" in extracted_data:
            return float(extracted_data["confidence_score"])
        
        # Calculate from individual field confidences
        fields = extracted_data.get("fields", [])
        if not fields:
            return 0.5
        
        confidences = [f.get("confidence", 0.5) for f in fields]
        return sum(confidences) / len(confidences) if confidences else 0.5
    
    def _validate_data(
        self,
        extracted_data: Dict[str, Any],
        document_type: str
    ) -> List[Dict[str, str]]:
        """
        Validate extracted data based on document type
        
        Args:
            extracted_data: Extracted data
            document_type: Type of document
            
        Returns:
            List of validation errors
        """
        errors = []
        
        fields = extracted_data.get("fields", [])
        field_dict = {f.get("field_name", "").lower(): f for f in fields}
        
        # Common validations
        if document_type in ["invoice", "receipt", "bill"]:
            # Check for required financial fields
            if not any(key in field_dict for key in ["total", "amount", "total amount", "grand total"]):
                errors.append({
                    "field": "total",
                    "error": "Total amount not found",
                    "severity": "error"
                })
            
            # Check for date
            if not any(key in field_dict for key in ["date", "invoice date", "receipt date"]):
                errors.append({
                    "field": "date",
                    "error": "Date not found",
                    "severity": "warning"
                })
        
        # Check confidence scores
        low_confidence_fields = [
            f.get("field_name") for f in fields 
            if f.get("confidence", 1.0) < settings.CONFIDENCE_THRESHOLD
        ]
        
        if low_confidence_fields:
            errors.append({
                "field": "confidence",
                "error": f"Low confidence in fields: {', '.join(low_confidence_fields)}",
                "severity": "warning"
            })
        
        return errors


# Create singleton instance
document_processor = DocumentProcessor()