# app/services/file_analyzer.py
# ============================================================
#  File Analyzer Service
#  Extracts text from uploaded files and runs LLM analysis.
#  Supported: PDF, TXT, DOCX, PNG/JPG (basic)
# ============================================================

import io
import base64
from pathlib import Path
from typing import Optional
from app.schemas.travel import FileAnalysisResponse
from app.services.llm_groq import analyze_document
from app.services.llm_router import route_llm
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


async def analyze_uploaded_file(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> FileAnalysisResponse:
    """
    Main entry: extract text from file, then send to LLM for travel insights.
    """
    ext = Path(filename).suffix.lower().lstrip(".")
    logger.info(f"[FileAnalyzer] Processing '{filename}' type={ext}")

    if ext not in settings.allowed_extensions:
        raise ValueError(f"File type '{ext}' is not allowed.")

    # ── Extract text by file type ────────────────────────────
    extracted_text = ""
    if ext == "pdf":
        extracted_text = _extract_pdf(file_bytes)
    elif ext == "txt":
        extracted_text = file_bytes.decode("utf-8", errors="replace")
    elif ext == "docx":
        extracted_text = _extract_docx(file_bytes)
    elif ext in ("png", "jpg", "jpeg"):
        extracted_text = "[Image file — content described by vision model]"

    if not extracted_text.strip():
        extracted_text = "No readable text found in this file."

    # ── Run LLM analysis ────────────────────────────────────
    system_msg = "You are a travel document analyst. Extract all travel-related information."
    user_msg = f"""Analyze '{filename}' and extract travel info.

Document content:
{extracted_text[:5000]}

Return ONLY valid JSON:
{{
  "travel_insights": "detailed paragraph about travel relevance",
  "detected_destinations": ["city1", "country1"],
  "detected_dates": ["2025-06-15", "July 2025"],
  "summary": "one sentence summary"
}}"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_msg},
    ]

    import re, json
    raw, llm_used = await route_llm(messages, temperature=0.3, max_tokens=1024)

    # Parse JSON
    clean = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    try:
        data = json.loads(clean)
    except Exception:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        data = json.loads(match.group()) if match else {}

    return FileAnalysisResponse(
        filename=filename,
        file_type=ext,
        extracted_text=extracted_text[:2000],  # cap for response size
        travel_insights=data.get("travel_insights", "No travel insights found."),
        detected_destinations=data.get("detected_destinations", []),
        detected_dates=data.get("detected_dates", []),
        llm_used=llm_used,
    )


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except ImportError:
        logger.warning("[FileAnalyzer] pypdf not installed — install with: pip install pypdf")
        return "PDF extraction requires pypdf. Run: pip install pypdf"
    except Exception as e:
        logger.error(f"[FileAnalyzer] PDF error: {e}")
        return f"Could not extract PDF text: {e}"


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except ImportError:
        logger.warning("[FileAnalyzer] python-docx not installed — install with: pip install python-docx")
        return "DOCX extraction requires python-docx. Run: pip install python-docx"
    except Exception as e:
        logger.error(f"[FileAnalyzer] DOCX error: {e}")
        return f"Could not extract DOCX text: {e}"
