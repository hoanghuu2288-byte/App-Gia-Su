# gemini_client.py
import base64
import io
import os
from typing import Optional

from PIL import Image
from openai import OpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4-mini")
DEFAULT_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-5.4-mini")


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "Chưa tìm thấy OPENAI_API_KEY. "
            "Hãy đặt biến môi trường OPENAI_API_KEY trước khi chạy app."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def _image_to_data_url(image: Image.Image) -> str:
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _extract_text(response) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    try:
        parts = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []):
                    if getattr(c, "type", None) == "output_text":
                        parts.append(getattr(c, "text", ""))
        return "\n".join(parts).strip()
    except Exception:
        return ""


def generate_text_response(
    system_prompt: str,
    user_input: str,
    model: Optional[str] = None,
) -> str:
    client = _get_client()
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

    return _extract_text(response)


def generate_multimodal_response(
    system_prompt: str,
    image: Image.Image,
    user_input: str,
    model: Optional[str] = None,
) -> str:
    client = _get_client()
    model_name = model or DEFAULT_VISION_MODEL
    image_data_url = _image_to_data_url(image)

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
                    },
                    {
                        "type": "input_image",
                        "image_url": image_data_url,
                    },
                ],
            },
        ],
    )

    return _extract_text(response)
