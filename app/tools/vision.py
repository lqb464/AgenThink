"""
Vision tool for AgenThink to call the external VisionLens service.

Triggers:
- "OCR hình ảnh <path>"
- "Mô tả hình ảnh <path>"
- "Tìm vật thể trong <path>"
"""

import os
import re
import httpx
import logging

logger = logging.getLogger(__name__)

VISION_SERVICE_URL = "http://localhost:8002"


def _call_vision_api(endpoint: str, file_path: str, params: dict = None) -> str:
    """Helper to send a local file to the VisionLens API."""
    if not os.path.exists(file_path):
        return f"Lỗi: Không tìm thấy tệp tin hình ảnh tại đường dẫn '{file_path}'"

    url = f"{VISION_SERVICE_URL.rstrip('/')}/api/vision/{endpoint}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "image/jpeg")}
            data = params or {}
            
            response = httpx.post(url, files=files, data=data, timeout=30.0)
            response.raise_for_status()
            res_data = response.json()
            
            if endpoint == "ocr":
                return f"[Trích xuất văn bản từ {os.path.basename(file_path)}]:\n{res_data.get('text', '')}"
            elif endpoint == "describe":
                return f"[Mô tả hình ảnh {os.path.basename(file_path)}]:\n{res_data.get('description', '')}"
            elif endpoint == "detect":
                objects = res_data.get("objects", [])
                if not objects:
                    return f"[Phân tích vật thể trong {os.path.basename(file_path)}]: Không phát hiện vật thể nào."
                lines = [f"- {obj['label']} (độ tin cậy: {int(obj['confidence'] * 100)}%)" for obj in objects]
                return f"[Vật thể phát hiện được trong {os.path.basename(file_path)}]:\n" + "\n".join(lines)
            
            return str(res_data)
            
    except httpx.ConnectError:
        return f"Lỗi: Không kết nối được tới dịch vụ VisionLens tại {VISION_SERVICE_URL}. Vui lòng bật service trước."
    except Exception as exc:
        logger.error("VisionLens tool failed: %s", exc)
        return f"Lỗi xử lý hình ảnh: {exc}"


def match_vision(message: str) -> str | None:
    message = message.strip()
    
    # 1. OCR trigger
    ocr_match = re.match(r"(?:OCR\s+hình\s+ảnh|Nhận\s+diện\s+chữ\s+trong)\s+(.+)", message, flags=re.IGNORECASE)
    if ocr_match:
        file_path = ocr_match.group(1).strip().strip('"').strip("'")
        return _call_vision_api("ocr", file_path)

    # 2. Describe trigger
    desc_match = re.match(r"(?:Mô\s+tả\s+hình\s+ảnh|Phân\s+tích\s+hình\s+ảnh)\s+(.+)", message, flags=re.IGNORECASE)
    if desc_match:
        file_path = desc_match.group(1).strip().strip('"').strip("'")
        return _call_vision_api("describe", file_path)

    # 3. Detect trigger
    detect_match = re.match(r"(?:Tìm\s+vật\s+thể\s+trong|Phát\s+hiện\s+vật\s+thể\s+trong)\s+(.+)", message, flags=re.IGNORECASE)
    if detect_match:
        file_path = detect_match.group(1).strip().strip('"').strip("'")
        return _call_vision_api("detect", file_path)

    return None
