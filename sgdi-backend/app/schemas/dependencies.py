from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DependencyBase(BaseModel):
    name: str
    code: str

class DependencyCreate(DependencyBase):
    pass

class DependencyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class DependencyResponse(DependencyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class DependencyList(BaseModel):
    items: List[DependencyResponse]
    total: int
