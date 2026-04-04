import json
import os
import re

import streamlit as st
from PIL import Image

from prompts import get_system_prompt
from gemini_client import (
    generate_text_response,
    generate_multimodal_response,
)
from logic import (
    init_app_state,
    reset_session,
    build_initial_context,
    classify_user_reply,
    build_followup_context,
    update_step_and_error,
    update_presentation_retry,
    build_summary_context,
    looks_like_new_problem,
    start_new_problem,
    should_require_full_presentation,
    is_small_error,
    update_stuck_ui,
    detect_finished_response,
    normalize_user_input,
    responses_too_similar,
    should_mark_finished_after_child_help,
    generate_opening_tutoring_response,
    generate_followup_tutoring_response,
)

st.set_page_config(
    page_title="Trợ lý học Toán lớp 3",
    page_icon="🎓",
    layout="centered",
)

init_app_state(st)

APP_PASSWORD = os.getenv("APP_PASSWORD", "vip123").strip() or "vip123"


# =========================================================
# IMAGE / OCR / STRUCTURED EXTRACTION
# =========================================================
def ensure_image_state():
    defaults = {
        "image_raw_ocr_text": "",
        "image_structured_data": {},
        "image_question_text": "",
        "image_data_text": "",
        "image_options_text": "",
        "image_missing_text": "",
        "confirm_problem_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_image_state():
    st.session_state.pending_image = None
    st.session_state.image_raw_ocr_text = ""
    st.session_state.image_structured_data = {}
    st.session_state.image_question_text = ""
    st.session_state.image_data_text = ""
    st.session_state.image_options_text = ""
    st.session_state.image_missing_text = ""
    st.session_state.confirm_problem_text = ""


ensure_image_state()

OCR_ONLY_PROMPT = """
Nhiệm vụ của bạn là OCR THUẦN cho ảnh đề toán.

Luật bắt buộc:
1. Chỉ chép lại đúng chữ, số, ký hiệu NHÌN THẤY TRONG ẢNH.
2. Không được suy luận thêm nội dung không có trong ảnh.
3. Không được tự thêm:
   - câu hỏi
   - đáp án A/B/C/D
   - dữ kiện
   - lời giải
   - diễn giải
4. Nếu ảnh chỉ có hình, sơ đồ, nhãn, số đo, thì chỉ trả về đúng các chữ và số nhìn thấy.
5. Giữ line break hợp lý để dễ đọc.
6. Nếu chỗ nào mờ hoặc không chắc, ghi [KHÔNG ĐỌC RÕ].
7. Không giải bài.
8. Không giải thích thêm.
9. Không tóm tắt.
10. Không viết câu mở đầu.

Chỉ trả về phần OCR thô.
"""


def build_structured_extraction_prompt(raw_ocr_text: str) -> str:
    return f"""
Bạn đang làm nhiệm vụ TRÍCH XUẤT DỮ KIỆN TOÁN LỚP 3 TỪ ẢNH theo JSON.

Rất quan trọng:
- Chỉ dùng những gì thực sự NHÌN THẤY trong ảnh.
- Có thể tham khảo OCR thô bên dưới để đối chiếu.
- Không được bịa thêm câu hỏi, đáp án, dữ kiện.
- Nếu ảnh không có đủ câu hỏi thì để question_text rỗng.
- Nếu ảnh không có lựa chọn A/B/C/D thì options phải là [].
- Nếu chỗ nào không chắc, ghi vào missing_or_unclear.
- Không giải bài.
- Không mô tả lan man.
- Chỉ trả về 1 JSON object hợp lệ.
- Không dùng markdown, không có ```json.

Schema bắt buộc:
{{
  "image_type": "text_only | diagram | geometry | mixed | unknown",
  "visible_text": ["..."],
  "question_text": "...",
  "options": ["A. ...", "B. ..."],
  "diagram_entities": [
    {{
      "name": "...",
      "value": "...",
      "unit": "...",
      "relation": "..."
    }}
  ],
  "geometry_labels": [
    {{
      "object": "...",
      "label": "...",
      "value": "...",
      "unit": "..."
    }}
  ],
  "missing_or_unclear": ["..."],
  "confidence": 0.0
}}

OCR thô để đối chiếu:
{raw_ocr_text}
"""


def _clean_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str):
    cleaned = _clean_json_text(text)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


def _to_str_list(value):
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                if item:
                    out.append(item)
            elif item is not None:
                item = str(item).strip()
                if item:
                    out.append(item)
        return out
    return []


def _normalize_options(options):
    normalized = []
    if not isinstance(options, list):
        return normalized

    for opt in options:
        if isinstance(opt, str):
            text = opt.strip()
            if text:
                normalized.append(text)
        elif isinstance(opt, dict):
            label = str(opt.get("label", "")).strip()
            text = str(opt.get("text", "")).strip()
            if label and text:
                normalized.append(f"{label}. {text}")
            elif text:
                normalized.append(text)

    return normalized


def _normalize_entity_list(items, keys):
    normalized = []
    if not isinstance(items, list):
        return normalized

    for item in items:
        if not isinstance(item, dict):
            continue

        row = {}
        for key in keys:
            row[key] = str(item.get(key, "")).strip()

        if any(v for v in row.values()):
            normalized.append(row)

    return normalized


def _safe_confidence_value(raw_value):
    try:
        value = float(raw_value)
        if value < 0:
            return 0.0
        if value > 1:
            return 1.0
        return value
    except Exception:
        return None


def infer_image_type(data: dict) -> str:
    raw_type = str(data.get("image_type", "")).strip().lower()

    if data.get("geometry_labels"):
        return "geometry"

    if data.get("diagram_entities") and (data.get("question_text") or data.get("visible_text")):
        return "mixed_text_diagram"

    if data.get("diagram_entities"):
        return "diagram"

    if data.get("question_text") or data.get("visible_text"):
        return "text_only"

    if raw_type:
        return raw_type

    return "unknown"


def image_type_label(image_type: str) -> str:
    mapping = {
        "text_only": "Ảnh chữ",
        "diagram": "Ảnh sơ đồ",
        "geometry": "Ảnh hình học",
        "mixed": "Ảnh hỗn hợp",
        "mixed_text_diagram": "Ảnh chữ + sơ đồ",
        "unknown": "Chưa rõ",
    }
    return mapping.get(image_type, image_type)


def confidence_label(conf_value):
    if conf_value is None:
        return "Chưa rõ"
    if conf_value >= 0.85:
        return "Cao"
    if conf_value >= 0.60:
        return "Vừa"
    return "Thấp"


def normalize_structured_data(raw_data, raw_ocr_text):
    if not isinstance(raw_data, dict):
        return {
            "image_type": "unknown",
            "visible_text": [line.strip() for line in raw_ocr_text.splitlines() if line.strip()],
            "question_text": "",
            "options": [],
            "diagram_entities": [],
            "geometry_labels": [],
            "missing_or_unclear": ["Không đọc được JSON có cấu trúc từ model."],
            "confidence_value": None,
        }

    structured = {
        "image_type": str(raw_data.get("image_type", "unknown")).strip() or "unknown",
        "visible_text": _to_str_list(raw_data.get("visible_text", [])),
        "question_text": str(raw_data.get("question_text", "")).strip(),
        "options": _normalize_options(raw_data.get("options", [])),
        "diagram_entities": _normalize_entity_list(
            raw_data.get("diagram_entities", []),
            ["name", "value", "unit", "relation"],
        ),
        "geometry_labels": _normalize_entity_list(
            raw_data.get("geometry_labels", []),
            ["object", "label", "value", "unit"],
        ),
        "missing_or_unclear": _to_str_list(raw_data.get("missing_or_unclear", [])),
        "confidence_value": _safe_confidence_value(raw_data.get("confidence")),
    }

    structured["image_type"] = infer_image_type(structured)
    return structured


def build_default_data_text(data):
    lines = []

    if data.get("diagram_entities"):
        lines.append("Dữ kiện nhìn thấy trong hình:")
        for ent in data["diagram_entities"]:
            name = ent.get("name", "")
            value = ent.get("value", "")
            unit = ent.get("unit", "")
            relation = ent.get("relation", "")

            row = f"- {name}"
            if value:
                row += f": {value}"
            if unit:
                row += f" {unit}"
            if relation:
                row += f" ({relation})"
            lines.append(row)

    if data.get("geometry_labels"):
        if lines:
            lines.append("")
        lines.append("Nhãn hình học nhìn thấy:")
        for ent in data["geometry_labels"]:
            obj = ent.get("object", "")
            label = ent.get("label", "")
            value = ent.get("value", "")
            unit = ent.get("unit", "")

            row = f"- {obj}"
            if label:
                row += f" | {label}"
            if value:
                row += f": {value}"
            if unit:
                row += f" {unit}"
            lines.append(row)

    if not lines and data.get("visible_text"):
        lines.append("Chữ/số nhìn thấy trong ảnh:")
        for line in data["visible_text"]:
            lines.append(f"- {line}")

    return "\n".join(lines).strip()


def build_default_options_text(data):
    if not data.get("options"):
        return ""
    return "\n".join(data["options"]).strip()


def build_missing_text(data):
    missing = list(data.get("missing_or_unclear", []))
    if not missing:
        return ""
    return "\n".join(f"- {item}" for item in missing).strip()


def build_problem_text_from_image_fields(question_text, data_text, options_text, missing_text):
    parts = []

    question_text = (question_text or "").strip()
    data_text = (data_text or "").strip()
    options_text = (options_text or "").strip()
    missing_text = (missing_text or "").strip()

    if question_text:
        parts.append(question_text)
    else:
        parts.append("[Ảnh chưa có đủ câu hỏi rõ ràng. Ba mẹ nhập thêm câu hỏi vào phần này.]")

    if data_text:
        parts.append(data_text)

    if options_text:
        parts.append("Các lựa chọn:")
        parts.append(options_text)

    if missing_text:
        parts.append("Phần chưa rõ từ ảnh:")
        parts.append(missing_text)

    return "\n\n".join(parts).strip()


def validate_structured_problem(question_text, data_text, structured_data):
    warnings = []

    if not (question_text or "").strip():
        warnings.append("Ảnh chưa có đủ câu hỏi rõ ràng. Ba mẹ nên nhập thêm phần đề chữ trước khi bắt đầu.")

    if not (data_text or "").strip():
        warnings.append("App chưa trích được dữ kiện rõ ràng từ ảnh. Ba mẹ nên kiểm tra OCR thô hoặc nhập lại dữ kiện.")

    conf = structured_data.get("confidence_value")
    if conf is not None and conf < 0.60:
        warnings.append("Độ tự tin của phần đọc ảnh đang thấp. Ba mẹ nên kiểm tra kỹ trước khi dùng.")

    if structured_data.get("missing_or_unclear"):
        warnings.append("Có phần app chưa chắc hoặc chưa đọc rõ trong ảnh.")

    return warnings


def rebuild_confirm_text_from_fields():
    st.session_state.confirm_problem_text = build_problem_text_from_image_fields(
        question_text=st.session_state.image_question_text,
        data_text=st.session_state.image_data_text,
        options_text=st.session_state.image_options_text,
        missing_text=st.session_state.image_missing_text,
    )
    st.session_state.problem_text = st.session_state.confirm_problem_text


def process_uploaded_image(img, typed_problem):
    raw_ocr_text = generate_multimodal_response(
        system_prompt="Bạn là trợ lý OCR thuần, chỉ chép đúng nội dung nhìn thấy trong ảnh.",
        image=img,
        user_input=OCR_ONLY_PROMPT,
    ).strip()

    structured_prompt = build_structured_extraction_prompt(raw_ocr_text)
    structured_response = generate_multimodal_response(
        system_prompt="Bạn là trợ lý trích xuất dữ kiện toán lớp 3 từ ảnh sang JSON có cấu trúc.",
        image=img,
        user_input=structured_prompt,
    ).strip()

    parsed_json = _extract_json_object(structured_response)
    needs_retry = parsed_json is None

    if not needs_retry and isinstance(parsed_json, dict):
        has_question = bool(str(parsed_json.get("question_text", "")).strip())
        has_numbers = bool(parsed_json.get("diagram_entities") or parsed_json.get("geometry_labels"))
        needs_retry = not has_question and not typed_problem.strip() and has_numbers

    if needs_retry:
        retry_prompt = (
            structured_prompt
            + "\n\nNhắc lại thật nghiêm ngặt:\n"
            + "- Chỉ trả về đúng 1 JSON object hợp lệ.\n"
            + "- Không thêm giải thích, không markdown.\n"
            + "- Nếu chưa chắc, để trống question_text và ghi vào missing_or_unclear.\n"
        )
        retry_response = generate_multimodal_response(
            system_prompt="Bạn là trợ lý trích xuất dữ kiện toán lớp 3 từ ảnh sang JSON có cấu trúc.",
            image=img,
            user_input=retry_prompt,
        ).strip()
        retry_json = _extract_json_object(retry_response)
        if retry_json is not None:
            parsed_json = retry_json

    structured_data = normalize_structured_data(parsed_json, raw_ocr_text)

    question_text = typed_problem.strip() if typed_problem.strip() else structured_data.get("question_text", "")
    data_text = build_default_data_text(structured_data)
    options_text = build_default_options_text(structured_data)
    missing_text = build_missing_text(structured_data)

    st.session_state.pending_image = img.copy()
    st.session_state.image_raw_ocr_text = raw_ocr_text
    st.session_state.image_structured_data = structured_data
    st.session_state.image_question_text = question_text
    st.session_state.image_data_text = data_text
    st.session_state.image_options_text = options_text
    st.session_state.image_missing_text = missing_text

    rebuild_confirm_text_from_fields()
    st.session_state.problem_confirmed = False


# =========================================================
# LEARNING FLOW
# =========================================================
def reset_learning_flow():
    st.session_state.chat_history = []
    st.session_state.summary = ""
    st.session_state.presentation_retry_count = 0
    st.session_state.stuck_count = 0
    st.session_state.show_help_buttons = False
    st.session_state.show_hint_button = False
    st.session_state.show_solution_button = False
    st.session_state.is_finished = False
    st.session_state.current_step = "start"
    st.session_state.last_error_type = ""
    st.session_state.hint_request_count = 0
    st.session_state.last_real_user_reply = ""
    st.session_state.last_assistant_response = ""


def append_chat_message(role: str, content: str, *, hidden: bool = False):
    st.session_state.chat_history.append(
        {"role": role, "content": content, "hidden": hidden}
    )


def get_recent_assistant_responses(limit: int = 3):
    responses = []
    for message in reversed(st.session_state.chat_history):
        if message.get("role") != "assistant":
            continue
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        responses.append(content)
        if len(responses) >= limit:
            break
    return responses


def build_child_hint_request_message(hint_count: int) -> str:
    if hint_count <= 1:
        return (
            "Con cần thêm một gợi ý ngắn. "
            "Hãy nhắc thật tự nhiên con nên nhìn vào đâu trước, rồi hỏi đúng 1 câu ngắn."
        )

    if hint_count == 2:
        return (
            "Con vẫn đang bí. "
            "Hãy nói rõ hơn bước cần làm hoặc phép tính cần nhìn, nhưng vẫn giữ giọng thầy giáo lớp 3 tự nhiên."
        )

    return (
        f"Con vẫn đang bí sau {hint_count} lần gợi ý. "
        "Có thể nói thẳng bước tính hoặc kết quả trung gian cần có, rồi mời con chốt tiếp. "
        "Không dùng giọng robot và không lặp nguyên câu trước."
    )


def maybe_retry_non_repeating_response(
    *,
    response: str,
    system_prompt: str,
    followup_context: str,
    reply_type: str,
    support_level_for_response: str,
    allow_full_solution_for_response: bool,
):
    if st.session_state.mode != "child":
        return response, False

    if reply_type != "student_dont_know":
        return response, False

    recent_responses = get_recent_assistant_responses(limit=3)
    is_repetitive = any(responses_too_similar(previous, response) for previous in recent_responses)
    if not is_repetitive:
        return response, False

    hint_count = st.session_state.hint_request_count
    stronger_support_level = support_level_for_response
    stronger_allow_full_solution = allow_full_solution_for_response

    if support_level_for_response == "goi_y":
        stronger_support_level = "tung_buoc"
    elif support_level_for_response == "tung_buoc" and hint_count >= 3:
        stronger_support_level = "cach_giai"
        stronger_allow_full_solution = True

    retry_instruction = (
        f"Con vừa nghe một gợi ý hơi giống câu trước. Hãy nói lại theo cách tự nhiên hơn, "
        f"đổi góc gợi ý, ngắn gọn hơn, hợp giọng thầy giáo lớp 3. "
        f"Không lặp nguyên câu cũ. {build_child_hint_request_message(max(1, hint_count))}"
    )

    stronger_context = build_followup_context(
        problem_text=st.session_state.problem_text,
        mode=st.session_state.mode,
        support_level=stronger_support_level,
        chat_history=st.session_state.chat_history,
        current_step=st.session_state.current_step,
        last_error_type=st.session_state.last_error_type,
        user_input=retry_instruction,
        reply_type=reply_type,
        allow_full_solution=stronger_allow_full_solution,
        require_full_presentation=False,
        small_error=False,
        stuck_count=st.session_state.stuck_count,
        is_finished=st.session_state.is_finished,
    )

    retry_response = generate_text_response(
        system_prompt=system_prompt,
        user_input=stronger_context,
    )

    retry_repetitive = any(responses_too_similar(previous, retry_response) for previous in recent_responses)
    if not retry_repetitive:
        return retry_response, False

    if hint_count < 4:
        return retry_response, False

    forced_final_context = build_followup_context(
        problem_text=st.session_state.problem_text,
        mode=st.session_state.mode,
        support_level="cach_giai",
        chat_history=st.session_state.chat_history,
        current_step=st.session_state.current_step,
        last_error_type=st.session_state.last_error_type,
        user_input=(
            "Con vẫn đang bí sau rất nhiều lượt gợi ý. "
            "Giữ giọng tự nhiên như thầy giáo lớp 3. "
            "Hãy nói thẳng bước tính hoặc kết quả trung gian cần có, rồi chốt ngắn gọn nếu cần."
        ),
        reply_type=reply_type,
        allow_full_solution=True,
        require_full_presentation=False,
        small_error=False,
        stuck_count=max(st.session_state.stuck_count, 4),
        is_finished=False,
    )

    forced_final_response = generate_text_response(
        system_prompt=system_prompt,
        user_input=forced_final_context,
    )
    return forced_final_response, True


def start_problem_session():
    reset_learning_flow()

    response = generate_opening_tutoring_response(
        problem_text=st.session_state.problem_text,
        mode=st.session_state.mode,
        support_level=st.session_state.support_level,
    )

    if response is None:
        initial_context = build_initial_context(
            problem_text=st.session_state.problem_text,
            mode=st.session_state.mode,
            support_level=st.session_state.support_level,
        )
        response = generate_text_response(
            system_prompt=get_system_prompt(st.session_state.mode),
            user_input=initial_context,
        )

    st.session_state.is_finished = detect_finished_response(response)
    append_chat_message("assistant", response)
    st.session_state.last_assistant_response = response


def run_followup_turn(
    user_reply: str,
    *,
    reply_type_override=None,
    support_level_override=None,
    allow_full_solution_override=None,
    append_user_message=True,
    user_message_hidden=False,
):
    normalized_user_reply = normalize_user_input(user_reply)

    if append_user_message:
        append_chat_message(
            "user",
            normalized_user_reply,
            hidden=user_message_hidden,
        )

    reply_type = reply_type_override or classify_user_reply(normalized_user_reply)

    update_step_and_error(st, reply_type)
    update_stuck_ui(st, reply_type)

    if reply_type_override == "student_dont_know":
        require_full_presentation = False
        small_error = False
    else:
        require_full_presentation = should_require_full_presentation(st, normalized_user_reply)
        small_error = is_small_error(normalized_user_reply)

    update_presentation_retry(st, require_full_presentation)

    support_level_for_response = support_level_override or st.session_state.support_level
    allow_full_solution_for_response = (
        st.session_state.allow_full_solution
        if allow_full_solution_override is None
        else allow_full_solution_override
    )

    response = generate_followup_tutoring_response(
        problem_text=st.session_state.problem_text,
        mode=st.session_state.mode,
        support_level=support_level_for_response,
        chat_history=st.session_state.chat_history,
        user_input=normalized_user_reply,
        reply_type=reply_type,
        allow_full_solution=allow_full_solution_for_response,
        require_full_presentation=require_full_presentation,
        small_error=small_error,
        stuck_count=st.session_state.stuck_count,
        is_finished=st.session_state.is_finished,
        hint_request_count=st.session_state.hint_request_count if st.session_state.mode == "child" else 0,
    )

    forced_finished = False
    system_prompt = get_system_prompt(st.session_state.mode)

    if response is None:
        followup_context = build_followup_context(
            problem_text=st.session_state.problem_text,
            mode=st.session_state.mode,
            support_level=support_level_for_response,
            chat_history=st.session_state.chat_history,
            current_step=st.session_state.current_step,
            last_error_type=st.session_state.last_error_type,
            user_input=normalized_user_reply,
            reply_type=reply_type,
            allow_full_solution=allow_full_solution_for_response,
            require_full_presentation=require_full_presentation,
            small_error=small_error,
            stuck_count=st.session_state.stuck_count,
            is_finished=st.session_state.is_finished,
        )

        response = generate_text_response(
            system_prompt=system_prompt,
            user_input=followup_context,
        )

        response, forced_finished = maybe_retry_non_repeating_response(
            response=response,
            system_prompt=system_prompt,
            followup_context=followup_context,
            reply_type=reply_type,
            support_level_for_response=support_level_for_response,
            allow_full_solution_for_response=allow_full_solution_for_response,
        )

    st.session_state.is_finished = (
        forced_finished
        or should_mark_finished_after_child_help(
            response,
            st.session_state.hint_request_count if st.session_state.mode == "child" else 0,
        )
        or detect_finished_response(response)
    )
    if st.session_state.is_finished:
        st.session_state.show_help_buttons = False
        st.session_state.show_hint_button = False
        st.session_state.show_solution_button = False

    append_chat_message("assistant", response)
    st.session_state.last_assistant_response = response


def get_child_help_response_settings():
    hint_count = st.session_state.hint_request_count

    if st.session_state.support_level == "cach_giai":
        return "cach_giai", True

    if st.session_state.stuck_count >= 4 or hint_count >= 3:
        return "cach_giai", True

    if st.session_state.support_level == "tung_buoc" or st.session_state.stuck_count >= 2 or hint_count >= 2:
        return "tung_buoc", False

    return "goi_y", False


# =========================================================
# APP UI
# =========================================================
if "dang_nhap_thanh_cong" not in st.session_state:
    st.session_state.dang_nhap_thanh_cong = False

if not st.session_state.dang_nhap_thanh_cong:
    st.title("🔒 Cổng Đăng Nhập Gia Sư AI")
    st.info("Chào ba mẹ! Vui lòng nhập mã bản quyền để kích hoạt trợ lý học Toán cho con nhé.")

    mat_khau = st.text_input("Nhập mã bản quyền:", type="password")

    if st.button("Mở Khóa 🚀"):
        if mat_khau == APP_PASSWORD:
            st.session_state.dang_nhap_thanh_cong = True
            st.rerun()
        else:
            st.error("Mã bản quyền không chính xác!")

else:
    st.title("🎓 Trợ lý học Toán lớp 3 cho phụ huynh bận rộn")

    col_left, col_right = st.columns([4, 1])
    with col_right:
        if st.button("Đăng xuất 🚪"):
            st.session_state.dang_nhap_thanh_cong = False
            reset_session(st)
            clear_image_state()
            st.rerun()

    st.subheader("1) Chọn cách dùng")

    mode_label = st.radio(
        "Chế độ",
        options=["Con học cùng app", "Ba mẹ dạy con"],
        horizontal=True,
    )
    st.session_state.mode = "child" if mode_label == "Con học cùng app" else "parent"

    support_map = {
        "Gợi ý nhẹ": "goi_y",
        "Dẫn từng bước": "tung_buoc",
        "Xem cách giải": "cach_giai",
    }

    support_label = st.radio(
        "Mức hỗ trợ",
        options=list(support_map.keys()),
        index=0,
        horizontal=True,
    )

    st.session_state.support_level = support_map[support_label]
    st.session_state.allow_full_solution = st.session_state.support_level == "cach_giai"

    st.divider()

    st.subheader("2) Nhập đề bài")

    uploaded_file = st.file_uploader(
        "Tải ảnh đề bài (nếu có)",
        type=["png", "jpg", "jpeg"],
    )

    typed_problem = st.text_area(
        "Hoặc gõ đề bài vào đây",
        value="" if st.session_state.problem_confirmed else st.session_state.problem_text,
        height=140,
        placeholder="Ví dụ: Lan có 24 quyển vở, mẹ mua thêm cho Lan 8 quyển nữa. Hỏi Lan có tất cả bao nhiêu quyển vở?",
    )

    col_a, col_b, col_c_tools = st.columns(3)

    with col_a:
        if st.button("Bắt đầu bài này ✨"):
            if uploaded_file is not None:
                try:
                    img = Image.open(uploaded_file)
                    process_uploaded_image(img, typed_problem)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi đọc ảnh: {e}")

            elif typed_problem.strip():
                clear_image_state()
                st.session_state.problem_text = typed_problem.strip()
                st.session_state.problem_confirmed = True
                start_problem_session()
                st.rerun()

            else:
                st.warning("Bạn hãy gõ đề bài hoặc tải ảnh lên trước nhé.")

    with col_b:
        if st.button("Làm bài mới 🧹"):
            reset_session(st)
            clear_image_state()
            st.rerun()

    with col_c_tools:
        if st.button("Xóa ảnh hiện tại 🖼️"):
            clear_image_state()
            st.rerun()

    if st.session_state.problem_text and not st.session_state.problem_confirmed:
        st.divider()
        st.subheader("3) Xác nhận đề bài")

        if st.session_state.pending_image is not None:
            st.info("App đã đọc ảnh theo 2 bước: OCR thô + trích dữ kiện có cấu trúc. Ba mẹ kiểm tra và sửa lại trước khi bắt đầu.")

            structured = st.session_state.image_structured_data or {}
            warnings = validate_structured_problem(
                st.session_state.image_question_text,
                st.session_state.image_data_text,
                structured,
            )

            col_img, col_data = st.columns([1, 1])

            with col_img:
                _ = st.image(st.session_state.pending_image, caption="Ảnh gốc", use_container_width=True)

            with col_data:
                st.markdown("**Thông tin app đọc từ ảnh**")
                st.write(f"- Loại ảnh: `{image_type_label(structured.get('image_type', 'unknown'))}`")
                st.write(f"- Mức tin cậy: `{confidence_label(structured.get('confidence_value'))}`")
                st.write(f"- Số dữ kiện trích được: `{len(structured.get('diagram_entities', [])) + len(structured.get('geometry_labels', []))}`")
                st.write(f"- Có lựa chọn A/B/C/D: `{'Có' if structured.get('options') else 'Không'}`")

                with st.expander("Xem OCR thô"):
                    st.text_area(
                        "OCR thô",
                        value=st.session_state.image_raw_ocr_text,
                        height=180,
                        disabled=True,
                        key="raw_ocr_view",
                    )

            if warnings:
                for warning in warnings:
                    st.warning(warning)

            st.markdown("### Sửa dữ kiện đã đọc")

            st.session_state.image_question_text = st.text_area(
                "Câu hỏi / phần đề chữ",
                value=st.session_state.image_question_text,
                height=120,
                key="image_question_text_editor",
            )

            st.session_state.image_data_text = st.text_area(
                "Dữ kiện / nhãn / số đo đọc từ ảnh",
                value=st.session_state.image_data_text,
                height=180,
                key="image_data_text_editor",
            )

            st.session_state.image_options_text = st.text_area(
                "Các lựa chọn A/B/C/D (nếu có)",
                value=st.session_state.image_options_text,
                height=120,
                key="image_options_text_editor",
            )

            st.session_state.image_missing_text = st.text_area(
                "Phần chưa rõ từ ảnh (có thể để trống)",
                value=st.session_state.image_missing_text,
                height=80,
                key="image_missing_text_editor",
            )

            col_merge, col_keep = st.columns(2)
            with col_merge:
                if st.button("Ghép lại đề từ dữ kiện ảnh 🔄"):
                    rebuild_confirm_text_from_fields()
                    st.rerun()

            with col_keep:
                st.caption("Sau khi sửa các ô bên trên, bấm nút ghép lại để cập nhật đề cuối cùng.")

        else:
            st.info("Ba mẹ kiểm tra lại đề bài trước khi bắt đầu.")

        st.text_area(
            "Đề bài cuối cùng sẽ dùng để dạy",
            value=st.session_state.confirm_problem_text,
            height=240,
            key="confirm_problem_text",
        )

        col_c, col_d = st.columns(2)

        with col_c:
            if st.button("Đúng rồi ✅"):
                final_text = st.session_state.confirm_problem_text.strip()
                if "[Ảnh chưa có đủ câu hỏi rõ ràng." in final_text:
                    st.error("Ảnh chưa có đủ câu hỏi rõ ràng. Ba mẹ hãy nhập thêm phần đề chữ trước khi bắt đầu.")
                elif not final_text:
                    st.error("Đề bài đang trống. Ba mẹ kiểm tra lại trước khi bắt đầu.")
                else:
                    st.session_state.problem_text = final_text
                    st.session_state.problem_confirmed = True
                    start_problem_session()
                    st.rerun()

        with col_d:
            if st.button("Lưu đề đã sửa ✏️"):
                st.session_state.problem_text = st.session_state.confirm_problem_text.strip()
                st.success("Đã cập nhật đề bài. Nếu đúng rồi, bấm 'Đúng rồi ✅'.")

    if st.session_state.problem_confirmed:
        st.divider()
        st.subheader("4) Học cùng app")

        st.caption(f"Đề bài hiện tại: {st.session_state.problem_text}")

        if st.session_state.pending_image is not None:
            with st.expander("Xem lại ảnh gốc của bài này"):
                _ = st.image(st.session_state.pending_image, caption="Ảnh gốc", use_container_width=True)

        col_retry, col_clear_chat = st.columns(2)
        with col_retry:
            if st.button("Làm lại bài này 🔁"):
                start_problem_session()
                st.rerun()
        with col_clear_chat:
            if st.button("Xóa cuộc hội thoại bài này 🧼"):
                reset_learning_flow()
                st.rerun()

        for message in st.session_state.chat_history:
            if message.get("hidden"):
                continue
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if (
            st.session_state.mode == "child"
            and not st.session_state.is_finished
            and len(st.session_state.chat_history) > 0
        ):
            st.markdown("**Hỗ trợ thêm:**")
            st.caption('Con bí thì bấm **Gợi ý thêm**, không cần gõ "không biết".')

            if st.button("Gợi ý thêm", key="child_help_button"):
                if should_mark_finished_after_child_help(
                    st.session_state.last_assistant_response,
                    st.session_state.hint_request_count,
                ):
                    st.session_state.is_finished = True
                    st.session_state.show_help_buttons = False
                    st.session_state.show_hint_button = False
                    st.session_state.show_solution_button = False
                    st.rerun()

                st.session_state.hint_request_count += 1
                support_level_for_response, allow_full_solution_for_response = get_child_help_response_settings()

                run_followup_turn(
                    user_reply=build_child_hint_request_message(st.session_state.hint_request_count),
                    reply_type_override="student_dont_know",
                    support_level_override=support_level_for_response,
                    allow_full_solution_override=allow_full_solution_for_response,
                    append_user_message=True,
                    user_message_hidden=True,
                )
                st.rerun()

        placeholder_text = (
            "Con trả lời ở đây nhé..."
            if st.session_state.mode == "child"
            else "Ba mẹ nhập câu hỏi hoặc tình huống của con ở đây..."
        )

        user_reply = st.chat_input(placeholder_text)

        if user_reply:
            st.session_state.hint_request_count = 0
            st.session_state.last_real_user_reply = user_reply

            if looks_like_new_problem(user_reply):
                start_new_problem(st, user_reply)
                clear_image_state()
                start_problem_session()
                st.rerun()

            try:
                run_followup_turn(user_reply=user_reply)
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi tạo phản hồi: {e}")

        st.divider()
        if st.button("Tạo tóm tắt cho ba mẹ 📘"):
            try:
                summary_context = build_summary_context(
                    problem_text=st.session_state.problem_text,
                    chat_history=st.session_state.chat_history,
                )

                summary_text = generate_text_response(
                    system_prompt="Bạn là trợ lý tóm tắt buổi học Toán lớp 3 cho phụ huynh.",
                    user_input=summary_context,
                )

                st.session_state.summary = summary_text
                st.rerun()

            except Exception as e:
                st.error(f"Lỗi khi tạo tóm tắt: {e}")

        if st.session_state.summary:
            st.subheader("Tóm tắt cho ba mẹ")
            st.markdown(st.session_state.summary)
