from pydantic_settings import BaseSettings
from pydantic import validator
from typing import List
import os
from pathlib import Path

class Settings(BaseSettings):
    # Database Configuration
    database_url: str = "postgresql://user:password@localhost:5432/sgdi_db"
    db_schema: str = "sgdi"

    # JWT Configuration
    jwt_secret_key: str = "your-super-secret-jwt-key-here-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Storage Configuration
    storage_path: str = "/app/storage"
    backup_path: str = "/app/backups"

    # Upload Configuration
    max_upload_size_mb: int = 200  # Aumentado a 200MB
    allowed_mime_types: str = "application/pdf,text/csv,text/plain,application/msword,application/vnd.ms-excel,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.presentationml.presentation,image/jpeg,image/jpg,image/png,image/gif,image/webp,image/bmp,application/zip,application/x-rar-compressed,application/x-7z-compressed,application/json,application/xml,text/xml"

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes"""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_mime_types_list(self) -> List[str]:
        """Get allowed MIME types as a list"""
        # Fallback to hardcoded list if string is incomplete
        default_types = [
            "application/pdf",
            "text/csv",
            "text/plain",
            "application/msword",
            "application/vnd.ms-excel",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
            "application/zip",
            "application/x-rar-compressed",
            "application/x-7z-compressed",
            "application/json",
            "application/xml",
            "text/xml"
        ]
        
        if self.allowed_mime_types:
            parsed = [mime.strip() for mime in self.allowed_mime_types.split(',') if mime.strip()]
            # If parsed list is too short, use default
            if len(parsed) < 10:
                return default_types
            return parsed
        return default_types

    # System Configuration
    system_user_id: str = "00000000-0000-0000-0000-000000000000"

    # Scheduler Configuration
    scheduler_enabled: bool = True
    scheduler_cron: str = "0 0 1 * *"  # First day of every month at midnight

    # Logging Configuration
    log_level: str = "INFO"

    # Rate Limiting Configuration
    login_attempt_limit: int = 5  # Max login attempts per IP
    lockout_minutes: int = 15  # Lockout duration in minutes
    disable_rate_limiting: bool = False  # Disable rate limiting for testing

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "validate_assignment": True
    }

    @validator('storage_path', 'backup_path')
    def validate_paths(cls, v):
        """Ensure storage and backup paths exist"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)


# Create global settings instance
settings = Settings()
