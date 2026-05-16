import asyncio
import base64
import io
import logging
from typing import Optional

import numpy as np

from api.models import ChatResponse

logger = logging.getLogger(__name__)


def _numpy_to_base64(img_data) -> Optional[str]:
    """
    Chuyển numpy array hoặc bytes từ StorePipeline sang base64 PNG data URI.

    StorePipeline.create_chart() trả về:
      - numpy.ndarray (BGR uint8) nếu cv2 available
      - numpy.ndarray (RGB uint8) nếu chỉ có PIL
      - bytes (PNG raw) nếu không có cả hai
    """
    if img_data is None:
        return None

    try:
        if isinstance(img_data, bytes):
            encoded = base64.b64encode(img_data).decode("utf-8")
            return f"data:image/png;base64,{encoded}"

        if isinstance(img_data, np.ndarray):
            from PIL import Image as PILImage

            arr = img_data.astype(np.uint8) if img_data.dtype != np.uint8 else img_data

            # cv2 trả về BGR → chuyển sang RGB; PIL trả về RGB giữ nguyên
            try:
                import cv2 as _cv2  # noqa: F401
                arr = arr[:, :, ::-1]
            except ImportError:
                pass

            pil_img = PILImage.fromarray(arr)
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"

    except Exception as exc:
        logger.error("Lỗi chuyển đổi ảnh sang base64: %s", exc)

    return None


class ChatService:
    """
    Singleton wrapper quanh RouterPipeline.
    Được khởi tạo một lần trong lifespan của FastAPI và gắn vào app.state.
    """

    def __init__(self):
        # Import ở đây để .env đã được load trước khi RouterPipeline import các submodule
        from query.router_pipeline import RouterPipeline

        logger.info("Đang khởi tạo RouterPipeline (có thể mất 5-15 giây)...")
        self._pipeline = RouterPipeline(max_retries=3)
        logger.info("RouterPipeline đã sẵn sàng.")

    def _call_pipeline_sync(self, message: str) -> dict:
        return self._pipeline.process_query_unified(message)

    async def process_message(self, message: str) -> ChatResponse:
        """
        Gọi pipeline đồng bộ trong thread executor để không block event loop của FastAPI.
        """
        loop = asyncio.get_running_loop()
        result: dict = await loop.run_in_executor(
            None, self._call_pipeline_sync, message
        )

        is_image: bool = result.get("is_image", False)
        raw_image = result.get("image", None)

        image_b64: Optional[str] = None
        if is_image and raw_image is not None:
            image_b64 = _numpy_to_base64(raw_image)
            if image_b64 is None:
                is_image = False

        return ChatResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            is_image=is_image,
            image=image_b64,
        )
