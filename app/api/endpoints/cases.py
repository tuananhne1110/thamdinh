from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.services.citizen_service import CitizenService
from app.schemas.citizen import CitizenVerificationCreate, CitizenVerificationUpdate, CitizenVerificationResponse

router = APIRouter()

@router.post("/{case_id}/verify-citizen", response_model=CitizenVerificationResponse)
def verify_citizen(
    case_id: int,
    verification_data: CitizenVerificationCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    Verify citizen information for a case
    """
    citizen_service = CitizenService(db)
    
    # Check if verification already exists
    existing_verification = citizen_service.get_verification_by_case(case_id)
    if existing_verification:
        raise HTTPException(status_code=400, detail="Verification already exists for this case")
    
    # Create verification
    verification = citizen_service.verify_citizen(
        case_id=case_id,
        citizen_id=verification_data.citizen_id,
        verification_data=verification_data.dict(exclude={'citizen_id'})
    )
    
    return verification

@router.put("/{case_id}/verify-citizen/{verification_id}", response_model=CitizenVerificationResponse)
def update_verification(
    case_id: int,
    verification_id: int,
    verification_data: CitizenVerificationUpdate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    Update citizen verification for a case
    """
    citizen_service = CitizenService(db)
    
    # Update verification
    verification = citizen_service.update_verification(
        verification_id=verification_id,
        update_data=verification_data.dict(exclude_unset=True)
    )
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    return verification

@router.get("/{case_id}/verify-citizen", response_model=CitizenVerificationResponse)
def get_verification(
    case_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    Get citizen verification for a case
    """
    citizen_service = CitizenService(db)
    verification = citizen_service.get_verification_by_case(case_id)
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    return verification 