from sqlalchemy.orm import Session
from app.models import Citizen, CitizenVerification
from datetime import datetime, date
from typing import Optional, Dict, Any

class CitizenService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def get_citizen_by_cccd(db: Session, cccd: str) -> Optional[Citizen]:
        """Get citizen by CCCD number"""
        return db.query(Citizen).filter(Citizen.cccd == cccd).first()

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

    @staticmethod
    def get_citizen_by_id(db: Session, id_number: str) -> Optional[Dict[str, Any]]:
        """Get citizen information by ID number"""
        try:
            # Thay thế bằng câu query thực tế của bạn
            citizen = db.execute(
                "SELECT * FROM citizens WHERE id_number = :id_number",
                {"id_number": id_number}
            ).first()
            
            if citizen:
                return dict(citizen)
            return None
        except Exception as e:
            print(f"Error getting citizen: {str(e)}")
            return None

    @staticmethod
    def verify_citizen_info(db: Session, citizen_data: Dict[str, Any]) -> Dict[str, Any]:
        print("[DEBUG] Starting citizen verification with data:", citizen_data)
        
        # Lấy thông tin công dân từ database
        cccd = citizen_data.get("cccd")
        print(f"[DEBUG] Looking up citizen with CCCD: {cccd}")
        
        db_citizen = CitizenService.get_citizen_by_cccd(db, cccd)
        print(f"[DEBUG] Database lookup result: {db_citizen}")

        verification_result = {
            "is_valid": True,
            "mismatches": []
        }

        if not db_citizen:
            print("[DEBUG] No citizen found in database")
            verification_result["is_valid"] = False
            verification_result["mismatches"].append("Không tìm thấy thông tin công dân trong cơ sở dữ liệu")
            return verification_result

        # Các trường cần kiểm tra
        fields_to_check = {
            "ho_ten": "Họ tên",
            "ngay_sinh": "Ngày sinh",
            "gioi_tinh": "Giới tính",
            "cccd": "Số định danh cá nhân"
        }

        # Chuẩn hóa dữ liệu để so sánh
        def normalize_value(value, field=None):
            if field == "ngay_sinh":
                if isinstance(value, (datetime, date)):
                    return value.strftime("%d/%m/%Y")
                if isinstance(value, str):
                    s = value.strip().replace(" ", "")  # Thêm .replace(" ", "") để loại bỏ dấu cách thừa
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
                        try:
                            dt = datetime.strptime(s, fmt)
                            return dt.strftime("%d/%m/%Y")
                        except Exception:
                            continue
                    # Nếu không parse được, thử tách chuỗi theo dấu '-' hoặc '/'
                    if '-' in s or '/' in s:
                        parts = s.replace('/', '-').split('-')
                        if len(parts) == 3:
                            # Nếu là dạng YYYY-MM-DD
                            if len(parts[0]) == 4:
                                try:
                                    dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                                    return dt.strftime("%d/%m/%Y")
                                except Exception:
                                    pass
                            # Nếu là dạng DD-MM-YYYY
                            if len(parts[2]) == 4:
                                try:
                                    dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                                    return dt.strftime("%d/%m/%Y")
                                except Exception:
                                    pass
                    return s
            if isinstance(value, datetime):
                return value.strftime("%d/%m/%Y")
            return str(value).lower().strip()

        for field, display_name in fields_to_check.items():
            db_value = getattr(db_citizen, field, None)
            input_value = citizen_data.get(field, "")
            
            print(f"[DEBUG] Comparing {display_name}:")
            print(f"[DEBUG] - Database value: {db_value} (type: {type(db_value)})")
            print(f"[DEBUG] - Input value: {input_value} (type: {type(input_value)})")
            
            if db_value is not None and input_value:
                normalized_db = normalize_value(db_value, field)
                normalized_input = normalize_value(input_value, field)
                print(f"[DEBUG] - Normalized DB value: {normalized_db} (type: {type(normalized_db)})")
                print(f"[DEBUG] - Normalized input value: {normalized_input} (type: {type(normalized_input)})")
                
                if normalized_db != normalized_input:
                    print(f"[DEBUG] - Mismatch found for {display_name}")
                    verification_result["is_valid"] = False
                    verification_result["mismatches"].append(
                        f"{display_name} không khớp với cơ sở dữ liệu"
                    )

        print(f"[DEBUG] Final verification result: {verification_result}")
        return verification_result 