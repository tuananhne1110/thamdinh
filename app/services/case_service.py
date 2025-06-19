from sqlalchemy.orm import Session
from app.models import Procedure, Case, Document
from app.schemas import CaseCreate, DocumentCreate
from typing import List, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy import func

class CaseService:
    @staticmethod
    def generate_next_ma_ho_so(db: Session) -> str:
        # Lấy mã hồ sơ lớn nhất hiện có, tăng lên 1
        last_ma_ho_so = db.query(func.max(Case.ma_ho_so)).scalar()
        try:
            next_id = int(last_ma_ho_so) + 1 if last_ma_ho_so else 1
        except Exception:
            next_id = 1
        return f"{next_id:06d}"

    @staticmethod
    def save_case(db: Session, procedure_id: str, case_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> Case:
        print("[LOG] Gọi save_case với procedure_id:", procedure_id)
        print("[LOG] case_data:", case_data)
        print("[LOG] documents:", documents)
        # Sinh mã hồ sơ mới
        ma_ho_so = CaseService.generate_next_ma_ho_so(db)
        # Create case
        case = Case(
            id=str(uuid.uuid4()),
            procedure_id=procedure_id,
            name=f"Hồ sơ {datetime.now().strftime('%Y%m%d%H%M%S')}",
            description=case_data.get("Nội dung đề nghị", ""),
            ma_ho_so=ma_ho_so
        )
        db.add(case)
        db.flush()  # Get the case ID
        print("[LOG] Đã tạo case với id:", case.id)
        # Create documents
        for doc in documents:
            document = Document(
                id=str(uuid.uuid4()),
                case_id=case.id,
                filename=doc.get("filename", ""),
                file_type=doc.get("type", ""),
                content=doc.get("content", ""),
                doc_class=doc.get("doc_class", ""),
                fields=doc.get("fields", {})
            )
            db.add(document)
        db.commit()
        db.refresh(case)
        print("[LOG] Đã commit case:", case.id)
        return case

    @staticmethod
    def get_case_by_id(db: Session, case_id: int) -> Case:
        return db.query(Case).filter(Case.id == case_id).first()

    @staticmethod
    def get_cases_by_procedure(db: Session, procedure_id: int) -> List[Case]:
        return db.query(Case).filter(Case.procedure_id == procedure_id).all() 