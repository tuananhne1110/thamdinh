from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Dict, Any

class CitizenBase(BaseModel):
    cccd: str
    ho_ten: str
    ngay_sinh: date
    gioi_tinh: str
    noi_thuong_tru: str
    noi_o_hien_tai: str
    noi_tam_tru: str

class CitizenCreate(CitizenBase):
    pass

class CitizenResponse(CitizenBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class CitizenVerificationBase(BaseModel):
    verification_status: str
    verification_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class CitizenVerificationCreate(CitizenVerificationBase):
    citizen_id: int

class CitizenVerificationUpdate(CitizenVerificationBase):
    pass

class CitizenVerificationResponse(CitizenVerificationBase):
    id: int
    case_id: int
    citizen_id: int
    verified_at: datetime
    verified_by: str

    class Config:
        orm_mode = True 