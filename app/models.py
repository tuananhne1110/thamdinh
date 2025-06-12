from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cases = relationship("Case", back_populates="procedure")

class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, index=True)
    procedure_id = Column(String, ForeignKey("procedures.id"))
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    ma_ho_so = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    procedure = relationship("Procedure", back_populates="cases")
    documents = relationship("Document", back_populates="case")
    citizen_verifications = relationship("CitizenVerification", back_populates="case")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.id"))
    filename = Column(String)
    file_type = Column(String)
    content = Column(Text, nullable=True)
    doc_class = Column(String)
    fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = relationship("Case", back_populates="documents") 


class Citizen(Base):
    __tablename__ = "citizens"
    
    id = Column(Integer, primary_key=True, index=True)
    cccd = Column(String(12), unique=True, index=True)
    ho_ten = Column(String(100))
    ngay_sinh = Column(Date)
    gioi_tinh = Column(String(10))
    noi_thuong_tru = Column(Text)
    noi_o_hien_tai = Column(Text)
    noi_tam_tru = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    verifications = relationship("CitizenVerification", back_populates="citizen")

class CitizenVerification(Base):
    __tablename__ = "citizen_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.id"))
    citizen_id = Column(Integer, ForeignKey("citizens.id"))
    verification_status = Column(String(20))  # matched, mismatched, not_found
    verification_details = Column(JSON)  # Store mismatch details
    verified_at = Column(DateTime, default=datetime.utcnow)
    verified_by = Column(String(50))
    notes = Column(Text)

    # Relationships
    case = relationship("Case", back_populates="citizen_verifications")
    citizen = relationship("Citizen", back_populates="verifications") 