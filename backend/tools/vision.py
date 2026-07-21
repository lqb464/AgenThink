"""
OCR via Gemini multimodal (in-process — no dOCRead microservice).

Triggers (legacy matcher):
- "OCR hình ảnh <path>"
- "Nhận diện chữ trong <path>"
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re

from backend.core.config import settings

logger = logging.getLogger(__name__)

_OCR_PROMPT = (
    "Extract ALL readable text from this image. "
    "Preserve line breaks where helpful. "
    "If little or no text is visible, say so briefly. "
    "Output plain text only — no commentary."
)


def _guess_mime(path_or_name: str) -> str:
    mime, _ = mimetypes.guess_type(path_or_name)
    if mime and mime.startswith("image/"):
        return mime
    return "image/jpeg"


def ocr_image_bytes(data: bytes, *, filename: str = "image.jpg") -> str:
    """Run Gemini vision OCR on raw image bytes; return extracted text."""
    if not data:
        raise ValueError("Empty image bytes")
    mime = _guess_mime(filename)
    b64 = base64.b64encode(data).decode("ascii")
    from openai import OpenAI

    keys = settings.get_gemini_api_keys()
    if not keys:
        raise RuntimeError("No Gemini API key configured for OCR")
    client = OpenAI(api_key=keys[0], base_url=settings.GEMINI_BASE_URL)
    response = client.chat.completions.create(
        model=settings.GEMINI_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    return text


def _call_ocr_api(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Lỗi: Không tìm thấy tệp tin hình ảnh tại đường dẫn '{file_path}'"
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        text = ocr_image_bytes(data, filename=os.path.basename(file_path))
        return f"[OCR — {os.path.basename(file_path)}]:\n{text}"
    except Exception as exc:
        logger.error("Local Gemini OCR failed: %s", exc)
        return f"Lỗi xử lý hình ảnh: {exc}"


def match_vision(message: str) -> str | None:
    message = message.strip()

    ocr_match = re.match(
        r"(?:OCR\s+hình\s+ảnh|Nhận\s+diện\s+chữ\s+trong)\s+(.+)",
        message,
        flags=re.IGNORECASE,
    )
    if ocr_match:
        file_path = ocr_match.group(1).strip().strip('"').strip("'")
        return _call_ocr_api(file_path)

    return None
