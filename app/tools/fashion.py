"""
Fashion generation tool for AgenThink to call the external SketClothes service.

Triggers:
- "Tạo trang phục từ sketch <path> [với prompt '<style>']"
- "Sinh trang phục từ sketch <path> [với prompt '<style>']"
"""

import os
import re
import base64
import logging
import httpx

logger = logging.getLogger(__name__)

FASHION_SERVICE_URL = "http://localhost:8003"


def _pil_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_fashion_api(file_path: str, style_desc: str) -> str:
    """Send base64 sketch to SketClothes backend REST API."""
    if not os.path.exists(file_path):
        return f"Lỗi: Không tìm thấy file sketch hình ảnh tại '{file_path}'"

    url = f"{FASHION_SERVICE_URL.rstrip('/')}/api/generate"
    try:
        # Convert sketch to base64
        sketch_b64 = _pil_to_base64(file_path)
        
        # Call REST API
        payload = {
            "sketch": f"data:image/png;base64,{sketch_b64}",
            "category": "shirt",  # default category, can expand with prompts
            "style": style_desc
        }
        
        response = httpx.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        res_data = response.json()
        
        output_b64 = res_data.get("image", "")
        if not output_b64:
            return "Lỗi: Không nhận được ảnh kết quả từ dịch vụ tạo mẫu."
            
        # Write output image near the source sketch for user convenience
        output_dir = os.path.dirname(file_path)
        output_filename = f"generated_fashion_{os.path.basename(file_path)}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Decode and save
        img_bytes = base64.b64decode(output_b64)
        with open(output_path, "wb") as f_out:
            f_out.write(img_bytes)
            
        return (
            f"[Sinh ảnh thành công!]\n"
            f"- Đã lưu trang phục thiết kế tại: {output_path}\n"
            f"- Chế độ sử dụng: {res_data.get('mode', 'unknown')}\n"
            f"- Gợi ý phong cách: {style_desc}"
        )
            
    except httpx.ConnectError:
        return f"Lỗi: Không kết nối được tới dịch vụ SketClothes tại {FASHION_SERVICE_URL}. Vui lòng bật service trước."
    except Exception as exc:
        logger.error("SketClothes tool failed: %s", exc)
        return f"Lỗi xử lý sinh ảnh: {exc}"


def match_fashion(message: str) -> str | None:
    message = message.strip()
    
    # Matches "Tạo trang phục từ sketch <path> với prompt <style>" or similar
    pattern = r"(?:Tạo|Sinh)\s+trang\s+phục\s+từ\s+sketch\s+(.+?)(?:\s+với\s+prompt\s+['\"](.+?)['\"])?$"
    match = re.match(pattern, message, flags=re.IGNORECASE)
    
    if match:
        file_path = match.group(1).strip().strip('"').strip("'")
        style_desc = match.group(2) or "fashion design, high quality garment photo"
        return _call_fashion_api(file_path, style_desc)
        
    return None
