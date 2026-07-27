"""Intake Agent API — unified stages 1–6 (Registration → Knowledge Graph)."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.auth.dependencies import CurrentUser
from app.repositories.intake_repositories import DocumentProcessingJobRepository
from app.schemas.knowledge_graph import (
    KnowledgeGraphOut,
    KnowledgeGraphStartRequest,
    KnowledgeGraphStartResponse,
    KnowledgeGraphStatusResponse,
)
from app.schemas.medical_history import (
    MedicalHistoryExtractRequest,
    MedicalHistoryResponse,
)
from app.schemas.ner import (
    MedicalEntityOut,
    NERResultOut,
    NERStartRequest,
    NERStartResponse,
    NERStatusResponse,
)
from app.schemas.ocr import (
    OCRResultOut,
    OCRReportOut,
    OCRStartRequest,
    OCRStartResponse,
    OCRStatusResponse,
    PatientContextResponse,
)
from app.schemas.registration import (
    PatientRegistrationResponse,
    ProcessingJobOut,
)
from app.schemas.risk import (
    RiskProfileOut,
    RiskStartRequest,
    RiskStartResponse,
    RiskStatusResponse,
)
from app.services.knowledge_graph_service import (
    KnowledgeGraphService,
    get_intake_knowledge_graph_service,
)
from app.services.medical_history_extraction_service import (
    MedicalHistoryExtractionService,
    get_medical_history_extraction_service,
)
from app.services.ner_service import NERService, get_intake_ner_service
from app.services.ocr_service import OCRService, get_intake_ocr_service
from app.services.patient_registration_service import (
    PatientRegistrationService,
    get_patient_registration_service,
)
from app.services.risk_service import RiskService, get_intake_risk_service

router = APIRouter(prefix="/ai/intake", tags=["intake-agent"])


# ---------------------------------------------------------------------------
# Stage 1 — Patient Registration
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=PatientRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Patient Registration (Intake stage 1)",
)
async def register_for_processing(
    current_user: CurrentUser,
    patient_id: Annotated[UUID, Form(...)],
    appointment_id: Annotated[UUID, Form(...)],
    doctor_id: Annotated[UUID, Form(...)],
    uploaded_document: Annotated[UploadFile, File(...)],
    service: Annotated[
        PatientRegistrationService, Depends(get_patient_registration_service)
    ],
) -> PatientRegistrationResponse:
    return await service.register(
        patient_id=patient_id,
        appointment_id=appointment_id,
        doctor_id=doctor_id,
        uploaded_document=uploaded_document,
        created_by=current_user.id,
    )


# ---------------------------------------------------------------------------
# Stage 2 — Medical History Extraction
# ---------------------------------------------------------------------------


@router.post(
    "/history/extract",
    response_model=MedicalHistoryResponse,
    summary="Medical History Extraction (Intake stage 2)",
)
def extract_medical_history(
    body: MedicalHistoryExtractRequest,
    _current_user: CurrentUser,
    service: Annotated[
        MedicalHistoryExtractionService,
        Depends(get_medical_history_extraction_service),
    ],
) -> MedicalHistoryResponse:
    return service.extract_for_job(body.job_id)


@router.get("/history/{patient_id}", response_model=MedicalHistoryResponse)
def get_medical_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[
        MedicalHistoryExtractionService,
        Depends(get_medical_history_extraction_service),
    ],
    extract: bool = False,
    job_id: Optional[UUID] = None,
) -> MedicalHistoryResponse:
    if extract:
        jobs = DocumentProcessingJobRepository()
        target_job_id = job_id
        if not target_job_id:
            latest = jobs.latest_for_patient(patient_id)
            if not latest:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=404,
                    detail="No processing job found. Complete Patient Registration first.",
                )
            target_job_id = UUID(str(latest["id"]))
        return service.extract_for_job(target_job_id)
    return service.get_history(patient_id)


# ---------------------------------------------------------------------------
# Stage 3 — OCR on Reports
# ---------------------------------------------------------------------------


@router.post(
    "/ocr/start",
    response_model=OCRStartResponse,
    summary="OCR on Reports (Intake stage 3)",
)
def start_ocr(
    body: OCRStartRequest,
    _current_user: CurrentUser,
    service: Annotated[OCRService, Depends(get_intake_ocr_service)],
) -> OCRStartResponse:
    """
    Extract raw text / tables / image metadata from the registered upload.

    Does **not** identify diseases, medications, or symptoms.
    On success, sets current_stage to Medical Entity Recognition.
    """
    return service.start(body)


@router.get("/ocr/status/{job_id}", response_model=OCRStatusResponse)
def ocr_status(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[OCRService, Depends(get_intake_ocr_service)],
) -> OCRStatusResponse:
    return service.status(job_id)


@router.get("/ocr/result/{job_id}", response_model=OCRResultOut)
def ocr_result(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[OCRService, Depends(get_intake_ocr_service)],
) -> OCRResultOut:
    return service.result(job_id)


@router.get("/context/{patient_id}", response_model=PatientContextResponse)
def get_patient_context(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[OCRService, Depends(get_intake_ocr_service)],
) -> PatientContextResponse:
    return service.get_patient_context(patient_id)


@router.get("/report/{document_id}", response_model=OCRReportOut)
def get_ocr_report(
    document_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[OCRService, Depends(get_intake_ocr_service)],
) -> OCRReportOut:
    """Staff-facing OCR report preview (job id or OCR result id)."""
    return service.get_report(document_id)


# ---------------------------------------------------------------------------
# Stage 4 — Medical Entity Recognition
# ---------------------------------------------------------------------------


@router.post(
    "/ner/start",
    response_model=NERStartResponse,
    summary="Medical Entity Recognition (Intake stage 4)",
)
def start_ner(
    body: NERStartRequest,
    _current_user: CurrentUser,
    service: Annotated[NERService, Depends(get_intake_ner_service)],
) -> NERStartResponse:
    """
    Recognize medical entities from cleaned document text.

    Does **not** diagnose, estimate severity, or recommend treatment.
    On success, sets current_stage to Patient Risk Profiling (not executed).
    """
    return service.start(body)


@router.get("/ner/status/{job_id}", response_model=NERStatusResponse)
def ner_status(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[NERService, Depends(get_intake_ner_service)],
) -> NERStatusResponse:
    return service.status(job_id)


@router.get("/ner/result/{job_id}", response_model=NERResultOut)
def ner_result(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[NERService, Depends(get_intake_ner_service)],
) -> NERResultOut:
    return service.result(job_id)


@router.get("/ner/entities/{job_id}", response_model=list[MedicalEntityOut])
def ner_entities(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[NERService, Depends(get_intake_ner_service)],
) -> list[MedicalEntityOut]:
    return service.entities(job_id)


# ---------------------------------------------------------------------------
# Stage 5 — Patient Risk Profiling
# ---------------------------------------------------------------------------


@router.post(
    "/risk/start",
    response_model=RiskStartResponse,
    summary="Patient Risk Profiling (Intake stage 5)",
)
def start_risk(
    body: RiskStartRequest,
    _current_user: CurrentUser,
    service: Annotated[RiskService, Depends(get_intake_risk_service)],
) -> RiskStartResponse:
    """
    Estimate patient risk from recognized entities and history.

    Clinical decision-support only — does **not** diagnose or prescribe.
    On success, sets current_stage to Patient Knowledge Graph (not executed).
    """
    return service.start(body)


@router.get("/risk/status/{job_id}", response_model=RiskStatusResponse)
def risk_status(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[RiskService, Depends(get_intake_risk_service)],
) -> RiskStatusResponse:
    return service.status(job_id)


@router.get("/risk/result/{job_id}", response_model=RiskProfileOut)
def risk_result(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[RiskService, Depends(get_intake_risk_service)],
) -> RiskProfileOut:
    return service.result(job_id)


# ---------------------------------------------------------------------------
# Stage 6 — Patient Knowledge Graph (final)
# ---------------------------------------------------------------------------


@router.post(
    "/kg/start",
    response_model=KnowledgeGraphStartResponse,
    summary="Patient Knowledge Graph (Intake stage 6 — final)",
)
def start_knowledge_graph(
    body: KnowledgeGraphStartRequest,
    _current_user: CurrentUser,
    service: Annotated[
        KnowledgeGraphService, Depends(get_intake_knowledge_graph_service)
    ],
) -> KnowledgeGraphStartResponse:
    """
    Build the patient knowledge graph from NER + risk + history.

    On success, marks the Intake Agent workflow as Completed.
    """
    return service.start(body)


@router.get("/kg/status/{job_id}", response_model=KnowledgeGraphStatusResponse)
def knowledge_graph_status(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[
        KnowledgeGraphService, Depends(get_intake_knowledge_graph_service)
    ],
) -> KnowledgeGraphStatusResponse:
    return service.status(job_id)


@router.get("/kg/result/{job_id}", response_model=KnowledgeGraphOut)
def knowledge_graph_result(
    job_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[
        KnowledgeGraphService, Depends(get_intake_knowledge_graph_service)
    ],
) -> KnowledgeGraphOut:
    return service.result(job_id)


@router.get(
    "/patients/{patient_id}/knowledge-graph",
    response_model=KnowledgeGraphOut,
)
def knowledge_graph_for_patient(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[
        KnowledgeGraphService, Depends(get_intake_knowledge_graph_service)
    ],
) -> KnowledgeGraphOut:
    return service.result_for_patient(patient_id)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}", response_model=ProcessingJobOut)
def get_processing_job(
    job_id: UUID,
    _current_user: CurrentUser,
) -> ProcessingJobOut:
    repo = DocumentProcessingJobRepository()
    row = repo.get_by_id(job_id)
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Processing job not found")
    return ProcessingJobOut.model_validate(row)


@router.get("/jobs", response_model=list[ProcessingJobOut])
def list_processing_jobs(
    _current_user: CurrentUser,
    patient_id: Optional[UUID] = None,
    limit: int = 20,
) -> list[ProcessingJobOut]:
    repo = DocumentProcessingJobRepository()
    params: list[tuple[str, str]] = [
        ("select", "*"),
        ("order", "created_at.desc"),
        ("limit", str(min(max(limit, 1), 100))),
    ]
    if patient_id:
        params.append(("patient_id", f"eq.{patient_id}"))
    rows = repo.select(params)
    return [ProcessingJobOut.model_validate(r) for r in rows]
