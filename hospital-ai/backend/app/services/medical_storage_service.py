"""Reusable Supabase Storage helper for medical documents."""

from typing import Optional
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client

logger = get_logger("hospital_ai.storage")

BUCKET = "medical-records"
MAX_BYTES = 20 * 1024 * 1024
ALLOWED_MIME = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }
)
ALLOWED_EXT = frozenset({"pdf", "png", "jpeg", "jpg", "webp"})


class MedicalStorageService:
    """Upload / signed URL / delete against the medical-records bucket."""

    def _headers(self, content_type: Optional[str] = None) -> dict[str, str]:
        settings = get_settings()
        settings.require_supabase()
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
            headers["x-upsert"] = "false"
        return headers

    def _object_url(self, storage_path: str) -> str:
        settings = get_settings()
        base = settings.supabase_url.rstrip("/")
        return f"{base}/storage/v1/object/{BUCKET}/{storage_path}"

    def _public_url(self, storage_path: str) -> str:
        settings = get_settings()
        base = settings.supabase_url.rstrip("/")
        return f"{base}/storage/v1/object/public/{BUCKET}/{storage_path}"

    def validate_file(self, *, filename: str, content_type: str, size: int) -> str:
        if size <= 0:
            raise HTTPException(status_code=400, detail="Empty file is not allowed")
        if size > MAX_BYTES:
            raise HTTPException(
                status_code=400, detail="File must be 20MB or smaller"
            )
        ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(
                status_code=400,
                detail="Allowed types: PDF, PNG, JPEG, JPG, WEBP",
            )
        mime = (content_type or "").split(";")[0].strip().lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime and mime not in ALLOWED_MIME and mime != "application/octet-stream":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {content_type}",
            )
        # Prefer extension-derived mime when browser sends octet-stream
        if not mime or mime == "application/octet-stream":
            mime = {
                "pdf": "application/pdf",
                "png": "image/png",
                "jpeg": "image/jpeg",
                "jpg": "image/jpeg",
                "webp": "image/webp",
            }[ext]
        return mime

    def build_storage_path(
        self,
        *,
        patient_id: str,
        appointment_id: Optional[str],
        filename: str,
    ) -> str:
        safe_name = filename.replace("\\", "_").replace("/", "_").strip()
        if not safe_name:
            safe_name = "file"
        folder = appointment_id or "general"
        return f"{patient_id}/{folder}/{uuid4().hex}_{safe_name}"

    def upload_bytes(
        self,
        *,
        storage_path: str,
        data: bytes,
        content_type: str,
    ) -> str:
        url = self._object_url(storage_path)
        try:
            response = get_http_client().post(
                url,
                headers=self._headers(content_type),
                content=data,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase Storage"
            ) from exc

        if response.status_code in (200, 201):
            return self._public_url(storage_path)

        if response.status_code == 409:
            raise HTTPException(
                status_code=409, detail="Duplicate upload path — file already exists"
            )

        logger.error(
            "Storage upload failed: %s %s", response.status_code, response.text
        )
        raise HTTPException(status_code=502, detail="Failed to upload file to storage")

    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        settings = get_settings()
        url = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/sign/"
            f"{BUCKET}/{storage_path}"
        )
        try:
            response = get_http_client().post(
                url,
                headers=self._headers("application/json"),
                json={"expiresIn": expires_in},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase Storage"
            ) from exc

        if response.status_code >= 400:
            logger.error(
                "Signed URL failed: %s %s", response.status_code, response.text
            )
            # Fallback to public-style URL (works if bucket later made public)
            return self._public_url(storage_path)

        body = response.json()
        signed = body.get("signedURL") or body.get("signedUrl") or ""
        if signed.startswith("http"):
            return signed
        base = settings.supabase_url.rstrip("/")
        return f"{base}/storage/v1{signed}"

    def delete_object(self, storage_path: str) -> None:
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{BUCKET}"
        try:
            response = get_http_client().request(
                "DELETE",
                url,
                headers=self._headers("application/json"),
                json={"prefixes": [storage_path]},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase Storage"
            ) from exc
        if response.status_code >= 400:
            logger.warning(
                "Storage delete soft-failed: %s %s",
                response.status_code,
                response.text,
            )


medical_storage_service = MedicalStorageService()
