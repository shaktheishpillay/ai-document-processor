"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_VISION_MODEL: str = "gpt-4o"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/document_processor.db"
    
    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    EXPORT_DIR: str = "./data/exports"
    
    # Logging
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"
    
    # Application Settings
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg,tiff,bmp"
    MAX_CONCURRENT_PROCESSING: int = 5
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Processing Settings
    EXTRACTION_TIMEOUT: int = 120
    RETRY_ATTEMPTS: int = 3
    CONFIDENCE_THRESHOLD: float = 0.7
    
    # Export Settings
    DEFAULT_EXPORT_FORMAT: str = "csv"
    INCLUDE_CONFIDENCE_SCORES: bool = True
    
    # Feature Flags
    ENABLE_OCR: bool = True
    ENABLE_VALIDATION: bool = True
    ENABLE_AUTO_CATEGORIZATION: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get list of allowed file extensions"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    def validate_file_extension(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        extension = Path(filename).suffix.lower().lstrip('.')
        return extension in self.allowed_extensions_list


# Create global settings instance
settings = Settings()