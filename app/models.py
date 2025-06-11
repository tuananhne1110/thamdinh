from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
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