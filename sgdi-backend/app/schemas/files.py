from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class FileMetadata(BaseModel):
    doc_number: Optional[str] = None
    tags: Optional[List[str]] = None
    has_annexes: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "doc_number": "DOC-2024-001",
                "tags": ["contrato", "legal", "confidencial"],
                "has_annexes": True
            }
        }
    }

class FileBase(BaseModel):
    original_name: str
    stored_name: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str

class FileCreate(BaseModel):
    folder_id: str
    metadata: Optional[FileMetadata] = None
    create_annex_folder: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "folder_id": "folder-uuid-123",
                "metadata": {
                    "doc_number": "DOC-2024-001",
                    "tags": ["contrato", "legal"],
                    "has_annexes": True
                },
                "create_annex_folder": True
            }
        }
    }

class FileResponse(FileBase):
    id: str
    folder_id: str
    dependency_id: str
    uploaded_by: Optional[str]
    uploaded_by_name: Optional[str] = None  # Nombre del usuario que subió el archivo
    version: int
    is_deleted: bool
    main_file_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": "file-uuid-123",
                "original_name": "contrato_servicios.pdf",
                "stored_name": "file-uuid-123.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 245760,
                "checksum_sha256": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                "folder_id": "folder-uuid-123",
                "dependency_id": "dep-uuid-123",
                "uploaded_by": "user-uuid-456",
                "version": 1,
                "is_deleted": False,
                "main_file_id": None,
                "created_at": "2024-12-01T10:30:00Z",
                "updated_at": "2024-12-01T10:30:00Z"
            }
        }
    }

class FileUpdate(BaseModel):
    metadata: Optional[FileMetadata] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "metadata": {
                    "doc_number": "DOC-2024-001-REV1",
                    "tags": ["contrato", "legal", "revisado"]
                }
            }
        }
    }

class FileUploadResponse(BaseModel):
    main_file: FileResponse
    annex_folder: Optional[Dict[str, Any]] = None
    annex_files: Optional[List[FileResponse]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "main_file": {
                    "id": "file-uuid-123",
                    "original_name": "contrato_servicios.pdf",
                    "stored_name": "file-uuid-123.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 245760,
                    "checksum_sha256": "a665a459...",
                    "folder_id": "folder-uuid-123",
                    "dependency_id": "dep-uuid-123",
                    "uploaded_by": "user-uuid-456",
                    "version": 1,
                    "is_deleted": False,
                    "main_file_id": None,
                    "created_at": "2024-12-01T10:30:00Z",
                    "updated_at": "2024-12-01T10:30:00Z"
                },
                "annex_folder": {
                    "id": "folder-uuid-annex",
                    "name": "Anexos-contrato_servicios-20241201",
                    "path": "Legal/Anexos-contrato_servicios-20241201"
                },
                "annex_files": [
                    {
                        "id": "file-uuid-annex1",
                        "original_name": "anexo_a.pdf",
                        "stored_name": "file-uuid-annex1.pdf",
                        "mime_type": "application/pdf",
                        "size_bytes": 102400,
                        "checksum_sha256": "b665a459...",
                        "folder_id": "folder-uuid-annex",
                        "dependency_id": "dep-uuid-123",
                        "uploaded_by": "user-uuid-456",
                        "version": 1,
                        "is_deleted": False,
                        "main_file_id": "file-uuid-123",
                        "created_at": "2024-12-01T10:30:05Z",
                        "updated_at": "2024-12-01T10:30:05Z"
                    }
                ]
            }
        }
    }

class FileDownloadResponse(BaseModel):
    download_url: str
    filename: str
    checksum: str
    size_bytes: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "download_url": "/files/file-uuid-123/download",
                "filename": "contrato_servicios.pdf",
                "checksum": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                "size_bytes": 245760
            }
        }
    }

class FileVersion(BaseModel):
    version: int
    filename: str
    created_at: datetime
    size_bytes: int
    checksum: str

class FileVersionsResponse(BaseModel):
    file_id: str
    current_version: int
    versions: List[FileVersion]

class FileDeleteRequest(BaseModel):
    hard: bool = False
    cascade: bool = False

class FileDeleteResponse(BaseModel):
    deleted: bool
    deleted_files: Optional[List[str]] = None
    message: str

class FileList(BaseModel):
    items: List[FileResponse]
    total: int

class FileFilters(BaseModel):
    folder_id: Optional[str] = None
    dependency_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    mime_type: Optional[str] = None
    is_deleted: Optional[bool] = None
