import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Configuración de la aplicación usando variables de entorno
    """

    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SERVER_NAME: str = "SGDI Backend"
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    PROJECT_NAME: str = "SGDI"

    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # React
        "http://localhost:8080",  # Vue.js
        "http://localhost:4200",  # Angular
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "fovis_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme123")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sgdi")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        return f"postgresql+psycopg2://{info.data.get('POSTGRES_USER')}:{info.data.get('POSTGRES_PASSWORD')}@{info.data.get('POSTGRES_HOST')}:{info.data.get('POSTGRES_PORT')}/{info.data.get('POSTGRES_DB')}"

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # File Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "/data/storage")
    BACKUP_PATH: str = os.getenv("BACKUP_PATH", "/data/backups")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "200"))
    ALLOWED_MIME_TYPES_STR: str = os.getenv("ALLOWED_MIME_TYPES", "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    @property
    def ALLOWED_MIME_TYPES(self) -> List[str]:
        """Parse ALLOWED_MIME_TYPES_STR into a list"""
        return [mime.strip() for mime in self.ALLOWED_MIME_TYPES_STR.split(",")]

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    # For Docker deployment, try to load from docker.env if .env doesn't exist
    if not os.path.exists(".env") and os.path.exists("docker.env"):
        import shutil
        shutil.copy("docker.env", ".env")

# Create settings instance
settings = Settings()
