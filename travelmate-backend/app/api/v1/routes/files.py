# app/api/v1/routes/files.py
# ============================================================
#  /api/v1/files  — File upload and AI analysis
# ============================================================

from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.file_analyzer import analyze_uploaded_file
from app.schemas.travel import FileAnalysisResponse
from app.core.config import get_settings
from app.core.logging import logger

router = APIRouter(prefix="/files", tags=["File Analysis"])
settings = get_settings()


@router.post("/analyze", response_model=FileAnalysisResponse, summary="Upload and analyze a travel document")
async def analyze_file(file: UploadFile = File(...)):
    """
    Upload a PDF, DOCX, TXT, or image file.
    The backend extracts text and uses AI to identify:
    - Travel destinations mentioned
    - Dates and durations
    - Budget information
    - Travel tips and requirements

    Use cases: upload an existing itinerary, travel brochure, visa docs, etc.
    """
    # Validate file size
    contents = await file.read()
    size_mb  = len(contents) / (1024 * 1024)

    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max is {settings.max_file_size_mb} MB."
        )

    # Validate extension
    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"File type '.{ext}' not supported. Allowed: {', '.join(settings.allowed_extensions)}"
        )

    try:
        logger.info(f"[Route/files] Analyzing: {file.filename} ({size_mb:.2f} MB)")
        result = await analyze_uploaded_file(
            file_bytes=contents,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
        )
        return result
    except Exception as e:
        logger.error(f"[Route/files] Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
