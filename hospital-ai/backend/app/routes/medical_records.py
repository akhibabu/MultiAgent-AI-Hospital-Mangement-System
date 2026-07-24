"""Medical records REST API."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.auth.dependencies import CurrentUser
from app.schemas.medical_record import (
    MedicalDocumentResponse,
    MedicalRecordAuditListResponse,
    MedicalRecordCreate,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordType,
    MedicalRecordUpdate,
    MessageResponse,
)
from app.services.medical_record_service import medical_record_service

router = APIRouter(prefix="/medical-records", tags=["medical-records"])


@router.get("", response_model=MedicalRecordListResponse)
def list_medical_records(
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    patient_id: Optional[UUID] = Query(None),
    doctor_id: Optional[UUID] = Query(None),
    appointment_id: Optional[UUID] = Query(None),
    record_type: Optional[MedicalRecordType] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> MedicalRecordListResponse:
    return medical_record_service.list_records(
        page=page,
        page_size=page_size,
        search=search,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        record_type=record_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/upload", response_model=MedicalDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_medical_document(
    current_user: CurrentUser,
    medical_record_id: UUID = Form(...),
    file: UploadFile = File(...),
) -> MedicalDocumentResponse:
    data = await file.read()
    return medical_record_service.upload_document(
        medical_record_id=medical_record_id,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "",
        data=data,
        uploaded_by=current_user.id,
    )


@router.post(
    "/upload-many",
    response_model=List[MedicalDocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_many_medical_documents(
    current_user: CurrentUser,
    medical_record_id: UUID = Form(...),
    files: List[UploadFile] = File(...),
) -> List[MedicalDocumentResponse]:
    results: List[MedicalDocumentResponse] = []
    for file in files:
        data = await file.read()
        results.append(
            medical_record_service.upload_document(
                medical_record_id=medical_record_id,
                filename=file.filename or "upload.bin",
                content_type=file.content_type or "",
                data=data,
                uploaded_by=current_user.id,
            )
        )
    return results


@router.get("/files/{document_id}", response_model=MedicalDocumentResponse)
def get_medical_document(
    document_id: UUID, _current_user: CurrentUser
) -> MedicalDocumentResponse:
    return medical_record_service.get_document(document_id)


@router.delete("/files/{document_id}", response_model=MessageResponse)
def delete_medical_document(
    document_id: UUID, current_user: CurrentUser
) -> MessageResponse:
    medical_record_service.delete_document(document_id, deleted_by=current_user.id)
    return MessageResponse(message="Document deleted successfully")


@router.get("/{record_id}/audit", response_model=MedicalRecordAuditListResponse)
def list_record_audit(
    record_id: UUID, _current_user: CurrentUser
) -> MedicalRecordAuditListResponse:
    return medical_record_service.list_audit(record_id)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_medical_record(
    record_id: UUID, _current_user: CurrentUser
) -> MedicalRecordResponse:
    return medical_record_service.get_record(record_id)


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_medical_record(
    body: MedicalRecordCreate, current_user: CurrentUser
) -> MedicalRecordResponse:
    return medical_record_service.create_record(body, created_by=current_user.id)


@router.put("/{record_id}", response_model=MedicalRecordResponse)
def update_medical_record(
    record_id: UUID, body: MedicalRecordUpdate, current_user: CurrentUser
) -> MedicalRecordResponse:
    return medical_record_service.update_record(
        record_id, body, updated_by=current_user.id
    )


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_medical_record(
    record_id: UUID, current_user: CurrentUser
) -> MessageResponse:
    medical_record_service.delete_record(record_id, deleted_by=current_user.id)
    return MessageResponse(message="Medical record deleted successfully")
