"""
Virtual try-on tool for AgenThink to call the external VirtuaLook service.

Triggers:
- "Thử đồ: mặc <garment_id> lên người <photo_path>"
- "Thử trang phục <garment_id> lên người <photo_path>"
"""

import os
import re
import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

VTON_SERVICE_URL = "http://localhost:8004"


async def _execute_tryon_workflow(garment_id: str, photo_path: str) -> str:
    """Automates: upload photo -> start job -> poll -> download result."""
    if not os.path.exists(photo_path):
        return f"Lỗi: Không tìm thấy ảnh người tại đường dẫn '{photo_path}'"

    async with httpx.AsyncClient(timeout=45.0) as client:
        # Step 1: Upload person photo
        upload_url = f"{VTON_SERVICE_URL}/api/photos"
        try:
            with open(photo_path, "rb") as f:
                files = {"file": (os.path.basename(photo_path), f, "image/jpeg")}
                data = {"label": "agent_upload"}
                
                response = await client.post(upload_url, files=files, data=data)
                response.raise_for_status()
                photo_id = response.json().get("id")
        except httpx.ConnectError:
            return f"Lỗi: Không kết nối được tới dịch vụ VirtuaLook tại {VTON_SERVICE_URL}. Vui lòng bật service trước."
        except Exception as exc:
            return f"Lỗi tải ảnh người lên VirtuaLook: {exc}"

        # Step 2: Start try-on job
        tryon_url = f"{VTON_SERVICE_URL}/api/tryon"
        try:
            payload = {
                "garment_id": garment_id,
                "photo_id": photo_id
            }
            response = await client.post(tryon_url, json=payload)
            response.raise_for_status()
            job_id = response.json().get("id")
        except Exception as exc:
            return f"Lỗi khởi tạo job try-on: {exc}"

        # Step 3: Poll status
        status_url = f"{VTON_SERVICE_URL}/api/tryon/{job_id}"
        max_attempts = 15
        for attempt in range(max_attempts):
            await asyncio.sleep(2.0)
            try:
                response = await client.get(status_url)
                response.raise_for_status()
                job_data = response.json()
                status = job_data.get("status")
                
                if status == "done":
                    result_url = job_data.get("result_url")
                    break
                elif status == "failed":
                    return f"Lỗi: Try-on job thất bại: {job_data.get('error')}"
            except Exception as exc:
                return f"Lỗi kiểm tra trạng thái job try-on: {exc}"
        else:
            return "Lỗi: Quá thời gian chờ xử lý try-on (Timeout)."

        # Step 4: Download result image
        # result_url usually starts with /storage/
        full_res_url = f"{VTON_SERVICE_URL}{result_url}"
        try:
            response = await client.get(full_res_url)
            response.raise_for_status()
            
            output_dir = os.path.dirname(photo_path)
            output_filename = f"tryon_result_{garment_id}_{os.path.basename(photo_path)}"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, "wb") as f_out:
                f_out.write(response.content)
                
            return (
                f"[Thử đồ thành công!]\n"
                f"- Ảnh kết quả đã được lưu tại: {output_path}\n"
                f"- ID Trang phục: {garment_id}\n"
                f"- URL kết quả trên service: {full_res_url}"
            )
        except Exception as exc:
            return f"Lỗi tải ảnh kết quả: {exc}"


def match_tryon(message: str) -> str | None:
    message = message.strip()
    
    # Matches: Thử đồ: mặc <garment_id> lên người <photo_path>
    pattern = r"(?:Thử\s+đồ:\s+mặc|Thử\s+trang\s+phục)\s+(.+?)\s+lên\s+người\s+(.+)$"
    match = re.match(pattern, message, flags=re.IGNORECASE)
    
    if match:
        garment_id = match.group(1).strip().strip('"').strip("'")
        photo_path = match.group(2).strip().strip('"').strip("'")
        
        # Run async workflow inside sync tool thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If running in another event loop (FastAPI context)
            import nest_asyncio  # noqa: PLC0415
            nest_asyncio.apply()
            
        return loop.run_until_complete(_execute_tryon_workflow(garment_id, photo_path))
        
    return None
