from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProcedureBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProcedureCreate(ProcedureBase):
    pass

class Procedure(ProcedureBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    procedure_id: int

class CaseCreate(CaseBase):
    pass

class Case(CaseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str
    file_type: str
    content: Optional[str] = None
    doc_class: str
    fields: Optional[Dict[str, Any]] = None
    case_id: int

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 