from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    type: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    detail: str
    code: str = "VALIDATION_ERROR"
    errors: Optional[Dict[str, Any]] = None

class PermissionDeniedResponse(BaseModel):
    detail: str
    code: str = "PERMISSION_DENIED"
    required_role: Optional[str] = None

class NotFoundResponse(BaseModel):
    detail: str
    code: str = "NOT_FOUND"
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

class ConflictResponse(BaseModel):
    detail: str
    code: str = "CONFLICT"
    conflicting_resource: Optional[str] = None
