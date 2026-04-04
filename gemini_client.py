import os
from typing import Optional

from PIL import Image

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Full Gemini 2.5 Pro cho cả text và vision
DEFAULT_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-pro")
DEFAULT_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-pro")


# =========================================================
# GEMINI SHARED
# =========================================================
def _ensure_gemini_ready() -> None:
    global genai
    if genai is None:
        try:
            import google.generativeai as _genai  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Thiếu thư viện google-generativeai. Hãy cài dependency rồi chạy lại app."
            ) from exc
        genai = _genai

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Chưa tìm thấy GEMINI_API_KEY. "
            "Hãy đặt biến môi trường GEMINI_API_KEY trước khi chạy app."
        )

    genai.configure(api_key=GEMINI_API_KEY)


def _prepare_image(image: Image.Image) -> Image.Image:
    if image.mode != "RGB":
        return image.convert("RGB")
    return image.copy()


def _extract_gemini_text(response) -> str:
    try:
        text = getattr(response, "text", None)
        if text:
            return text.strip()
    except Exception:
        pass

    try:
        parts = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                value = getattr(part, "text", "")
                if value:
                    parts.append(value)
        return "\n".join(parts).strip()
    except Exception:
        return ""


# =========================================================
# PUBLIC API
# =========================================================
def generate_text_response(
    system_prompt: str,
    user_input: str,
    model: Optional[str] = None,
) -> str:
    """
    Dùng Gemini cho phần text reasoning / tutoring.
    """
    _ensure_gemini_ready()
    model_name = model or DEFAULT_TEXT_MODEL

    model_client = genai.GenerativeModel(model_name)
    response = model_client.generate_content(
        [
            f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]",
            user_input,
        ],
        generation_config={
            "temperature": 0.2,
        },
    )

    text = _extract_gemini_text(response)
    if text:
        return text

    raise RuntimeError("Gemini trả về rỗng ở bước generate_text_response.")


def generate_multimodal_response(
    system_prompt: str,
    image: Image.Image,
    user_input: str,
    model: Optional[str] = None,
) -> str:
    """
    Dùng Gemini cho phần đọc ảnh / OCR / trích dữ kiện từ ảnh.
    """
    _ensure_gemini_ready()
    model_name = model or DEFAULT_VISION_MODEL
    safe_image = _prepare_image(image)

    model_client = genai.GenerativeModel(model_name)
    response = model_client.generate_content(
        [
            f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]",
            user_input,
            safe_image,
        ],
        generation_config={
            "temperature": 0.1,
        },
    )

    text = _extract_gemini_text(response)
    if text:
        return text

    raise RuntimeError("Gemini trả về rỗng ở bước generate_multimodal_response.")
