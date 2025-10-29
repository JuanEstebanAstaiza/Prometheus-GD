from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FolderBase(BaseModel):
    name: str
    dependency_id: str

class FolderCreate(FolderBase):
    parent_id: Optional[str] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    path: str
    parent_id: Optional[str]
    dependency_id: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class FolderTreeNode(FolderResponse):
    children: List['FolderTreeNode'] = []

    model_config = {
        "from_attributes": True
    }

# Forward reference resolved automatically in Pydantic v2

class FolderDeleteRequest(BaseModel):
    force: bool = False

class FolderDeleteResponse(BaseModel):
    deleted: bool
    items_deleted: Optional[dict] = None
    message: str
