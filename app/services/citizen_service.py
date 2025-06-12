from sqlalchemy.orm import Session
from app.models import Citizen, CitizenVerification
from datetime import datetime
from typing import Optional, Dict, Any

class CitizenService:
    def __init__(self, db: Session):
        self.db = db

    def get_citizen_by_cccd(self, cccd: str) -> Optional[Citizen]:
        """Tìm công dân theo CCCD"""
        return self.db.query(Citizen).filter(Citizen.cccd == cccd).first()

    def create_citizen(self, citizen_data: Dict[str, Any]) -> Citizen:
        """Tạo mới một công dân"""
        citizen = Citizen(
            cccd=citizen_data.get('cccd'),
            ho_ten=citizen_data.get('ho_ten'),
            ngay_sinh=citizen_data.get('ngay_sinh'),
            gioi_tinh=citizen_data.get('gioi_tinh'),
            noi_thuong_tru=citizen_data.get('noi_thuong_tru'),
            noi_o_hien_tai=citizen_data.get('noi_o_hien_tai'),
            noi_tam_tru=citizen_data.get('noi_tam_tru')
        )
        self.db.add(citizen)
        self.db.commit()
        self.db.refresh(citizen)
        return citizen

    def verify_citizen(self, case_id: int, citizen_id: int, verification_data: Dict[str, Any]) -> CitizenVerification:
        verification = CitizenVerification(
            case_id=case_id,
            citizen_id=citizen_id,
            **verification_data
        )
        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)
        return verification

    def get_verification_by_case(self, case_id: str) -> Optional[CitizenVerification]:
        """Tìm xác minh theo case_id"""
        return self.db.query(CitizenVerification).filter(CitizenVerification.case_id == case_id).first()

    def update_verification(self, verification_id: int, update_data: Dict[str, Any]) -> Optional[CitizenVerification]:
        verification = self.db.query(CitizenVerification).filter(
            CitizenVerification.id == verification_id
        ).first()
        
        if verification:
            for key, value in update_data.items():
                setattr(verification, key, value)
            verification.verified_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(verification)
        
        return verification

    def create_verification(self, verification_data: Dict[str, Any]) -> CitizenVerification:
        """Tạo mới một xác minh công dân"""
        verification = CitizenVerification(
            case_id=verification_data.get('case_id'),
            citizen_id=verification_data.get('citizen_id'),
            verification_status=verification_data.get('verification_status'),
            verification_details=verification_data.get('verification_details'),
            verified_by=verification_data.get('verified_by'),
            notes=verification_data.get('notes')
        )
        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)
        return verification 