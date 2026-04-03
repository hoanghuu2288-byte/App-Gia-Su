import os
from typing import Optional

import google.generativeai as genai
from PIL import Image
from openai import OpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4-mini")
DEFAULT_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-pro")


# =========================================================
# OPENAI (TEXT / TUTORING)
# =========================================================
def _get_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "Chưa tìm thấy OPENAI_API_KEY. "
            "Hãy đặt biến môi trường OPENAI_API_KEY trước khi chạy app."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def _extract_openai_text(response) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    try:
        parts = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []):
                    if getattr(content, "type", None) == "output_text":
                        value = getattr(content, "text", "")
                        if value:
                            parts.append(value)
        return "\n".join(parts).strip()
    except Exception:
        return ""


# =========================================================
# GEMINI (VISION / IMAGE READING)
# =========================================================
def _ensure_gemini_ready() -> None:
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
    Dùng OpenAI cho phần text reasoning / tutoring.
    """
    client = _get_openai_client()
    model_name = model or DEFAULT_TEXT_MODEL

    response = client.responses.create(
        model=model_name,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_input,
                    }
                ],
            },
        ],
    )

    text = _extract_openai_text(response)
    if text:
        return text

    raise RuntimeError("OpenAI trả về rỗng ở bước generate_text_response.")


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
