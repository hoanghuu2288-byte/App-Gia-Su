from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from prompts import (
    get_first_response_guide,
    get_summary_prompt,
    get_support_guide,
    get_system_prompt,
)
from grade3_math_master import GRADE3_MATH_MASTER, get_problem_blueprint


CHOICE_LETTERS = ["A", "B", "C", "D"]


# =========================================================
# STATE
# =========================================================
def _set_state_value(session_state, key: str, value: Any) -> None:
    try:
        session_state[key] = value
    except Exception:
        setattr(session_state, key, value)


def _get_state_value(session_state, key: str, default: Any = None) -> Any:
    try:
        return session_state[key]
    except Exception:
        return getattr(session_state, key, default)


def init_app_state(st):
    defaults = {
        "mode": "child",
        "support_level": "goi_y",
        "problem_text": "",
        "problem_confirmed": False,
        "problem_type": "",
        "problem_blueprint": {},
        "current_step": "start",
        "last_error_type": "",
        "allow_full_solution": False,
        "chat_history": [],
        "summary": "",
        "pending_image": None,
        "presentation_retry_count": 0,
        "stuck_count": 0,
        "show_help_buttons": False,
        "show_hint_button": False,
        "show_solution_button": False,
        "is_finished": False,
        "hint_request_count": 0,
        "last_assistant_response": "",
        "last_real_user_reply": "",
    }

    for key, value in defaults.items():
        if _get_state_value(st.session_state, key, None) is None:
            _set_state_value(st.session_state, key, value)


def reset_session(st):
    defaults = {
        "problem_text": "",
        "problem_confirmed": False,
        "problem_type": "",
        "problem_blueprint": {},
        "current_step": "start",
        "last_error_type": "",
        "allow_full_solution": False,
        "chat_history": [],
        "summary": "",
        "pending_image": None,
        "presentation_retry_count": 0,
        "stuck_count": 0,
        "show_help_buttons": False,
        "show_hint_button": False,
        "show_solution_button": False,
        "is_finished": False,
        "hint_request_count": 0,
        "last_assistant_response": "",
        "last_real_user_reply": "",
    }
    for key, value in defaults.items():
        _set_state_value(st.session_state, key, value)


# =========================================================
# BASIC NORMALIZATION / DETECTION
# =========================================================
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def normalize_user_input(user_input: str) -> str:
    text = normalize_text(user_input)
    compact = text.replace(" ", "")

    choice_patterns = [
        r"^([abcd])$",
        r"^đápán([abcd])$",
        r"^dapan([abcd])$",
        r"^chon([abcd])$",
        r"^chọn([abcd])$",
    ]
    for pattern in choice_patterns:
        match = re.match(pattern, compact, flags=re.IGNORECASE)
        if match:
            return f"Chọn đáp án {match.group(1).upper()}"

    return (user_input or "").strip()


def looks_like_new_problem(user_input: str) -> bool:
    raw = (user_input or "").strip()
    text = normalize_text(raw)

    if len(text) < 18:
        return False

    if any(text.startswith(prefix) for prefix in ["con nghĩ", "theo con", "em nghĩ", "vì", "chắc là", "hình như"]):
        return False

    question_signals = [
        "hỏi",
        "tính",
        "tìm",
        "bao nhiêu",
        "còn lại",
        "còn phải",
        "chia đều",
        "chu vi",
        "số liền trước",
        "số liền sau",
        "khẳng định đúng",
        "đáp án đúng",
        "ô trống",
    ]
    structure_signals = [
        "mỗi lần",
        "mỗi khay",
        "mỗi hộp",
        "chiều dài",
        "chiều rộng",
        "hình vuông",
        "hình chữ nhật",
        "hình tròn",
        "->",
    ]
    numeric_count = len(re.findall(r"\d[\d .]*", raw))

    has_math_question = any(signal in text for signal in question_signals)
    has_structure = any(signal in text for signal in structure_signals) or numeric_count >= 2

    return has_math_question and has_structure


def _matches_keywords(text: str, keywords: list[str]) -> int:
    score = 0
    for keyword in keywords:
        kw = normalize_text(keyword)
        if kw and kw in text:
            score += 1
    return score


def detect_problem_type(problem_text: str) -> str:
    text = normalize_text(problem_text)

    if "số liền trước" in text:
        return "number_predecessor"
    if "số liền sau" in text:
        return "number_successor"
    if "chu vi hình vuông" in text or ("hình vuông" in text and "cạnh" in text and "đoạn dây" in text):
        return "perimeter_square"
    if "chu vi hình chữ nhật" in text or ("hình chữ nhật" in text and "chiều dài" in text and "chiều rộng" in text):
        return "perimeter_rectangle"
    if "bị trừ đi" in text and "tìm số" in text:
        return "find_unknown_minuend"
    if "->" in text and "ô trống" in text:
        return "operation_chain"
    if "gấp" in text and any(k in text for k in ["tặng", "cho đi", "bớt đi", "còn lại"]):
        return "multi_step_give_away"
    if "chia đều" in text and any(k in text for k in ["mỗi khay", "mỗi hộp", "mỗi phần", "mỗi chồng"]):
        return "one_step_division_word"

    if any(k in text for k in ["chọn khẳng định đúng", "chọn đáp án đúng", "câu nào đúng", "phương án đúng"]):
        if any(k in text for k in ["tâm hình tròn", "bán kính", "đường kính", "hình tròn", "oq", "op", "mn"]):
            return "multiple_choice_geometry_circle"
        return "multiple_choice_general"

    if any(k in text for k in ["tâm", "bán kính", "đường kính", "hình tròn"]):
        return "geometry_identification_circle_parts"

    best_type = None
    best_score = -1
    for problem_type, config in GRADE3_MATH_MASTER.items():
        score = _matches_keywords(text, config.get("keywords", []))
        if score > best_score:
            best_type = problem_type
            best_score = score

    if best_type and best_score > 0:
        return best_type

    if any(k in text for k in ["gấp", "mỗi lần", "sau đó", "rồi", "còn lại", "còn phải", "còn thiếu"]):
        return "multi_step_find_missing"
    if any(k in text for k in [" m ", " cm", " kg", " g", "xăng-ti-mét", "ki-lô-gam", "đổi"]):
        return "unit_conversion_then_calculate"
    return "multi_step_find_missing"


def start_new_problem(st, new_problem_text: str):
    detected_type = detect_problem_type(new_problem_text)
    blueprint = get_problem_blueprint(detected_type)

    _set_state_value(st.session_state, "problem_text", new_problem_text.strip())
    _set_state_value(st.session_state, "problem_confirmed", True)
    _set_state_value(st.session_state, "problem_type", detected_type)
    _set_state_value(st.session_state, "problem_blueprint", blueprint)
    _set_state_value(st.session_state, "current_step", "start")
    _set_state_value(st.session_state, "last_error_type", "")
    _set_state_value(st.session_state, "chat_history", [])
    _set_state_value(st.session_state, "summary", "")
    _set_state_value(st.session_state, "presentation_retry_count", 0)
    _set_state_value(st.session_state, "stuck_count", 0)
    _set_state_value(st.session_state, "show_help_buttons", False)
    _set_state_value(st.session_state, "show_hint_button", False)
    _set_state_value(st.session_state, "show_solution_button", False)
    _set_state_value(st.session_state, "is_finished", False)
    _set_state_value(st.session_state, "hint_request_count", 0)
    _set_state_value(st.session_state, "last_assistant_response", "")
    _set_state_value(st.session_state, "last_real_user_reply", "")


def detect_problem_complexity(problem_text: str) -> str:
    text = normalize_text(problem_text)
    multi_step_signals = [
        "mỗi lần",
        "lần",
        "sau đó",
        "rồi",
        "còn phải",
        "còn lại",
        "đổi đơn vị",
        " cm",
        " kg",
        " g",
        "1/2",
        "1/3",
        "1/4",
        "1/5",
        "chọn khẳng định đúng",
        "chọn đáp án đúng",
        "mấy hộp",
        "mấy khay",
        "mấy gói",
        "mấy chồng",
    ]
    count = sum(1 for s in multi_step_signals if s in text)
    return "medium_or_hard" if count >= 2 else "easy"


# ... trimmed? no, continue below

def build_plan_block(problem_blueprint: dict) -> str:
    if not problem_blueprint or not problem_blueprint.get("show_plan_steps"):
        return ""

    plan_steps = problem_blueprint.get("plan_steps", [])
    if not plan_steps:
        return ""

    lines = [f"- Mình đi {len(plan_steps)} bước:"]
    for idx, step in enumerate(plan_steps, start=1):
        lines.append(f"  - Bước {idx}: {step}")
    return "\n".join(lines)


def build_multiple_choice_rule(problem_blueprint: dict) -> str:
    if not problem_blueprint:
        return ""

    if problem_blueprint.get("multiple_choice_strategy") == "check_each_option":
        return """
- Đây là bài trắc nghiệm.
- Phải ưu tiên xét từng đáp án một.
- Không được tự loại hết A, B, C, D quá sớm.
- Opening phải hiện rõ:
  - Cách làm: mình xét từng đáp án một
  - Mình xét A trước nhé...
"""
    return ""


def build_initial_context(problem_text: str, mode: str, support_level: str) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    first_response_guide = get_first_response_guide()
    complexity = detect_problem_complexity(problem_text)
    problem_type = detect_problem_type(problem_text)
    blueprint = get_problem_blueprint(problem_type)
    plan_block = build_plan_block(blueprint)
    mc_rule = build_multiple_choice_rule(blueprint)

    flow_type = blueprint.get("flow_type", "")
    label = blueprint.get("label", "")
    knowledge_used = blueprint.get("knowledge_used", "")

    context = f"""
{system_prompt}

{support_guide}

{first_response_guide}

Đề bài đã xác nhận:
{problem_text}

Dạng bài nội bộ:
- problem_type: {problem_type}
- label: {label}
- flow_type: {flow_type}
- knowledge_used: {knowledge_used}

Mức độ bài:
{complexity}

{plan_block}

{mc_rule}

Yêu cầu mở đầu cực quan trọng:
- Ở mode child, lượt đầu phải cho thấy đúng 3 ý:
  - Dạng bài
  - Kiến thức dùng
  - Cách nghĩ nhanh
- Với mode child, tối đa 4 dòng ngắn + 1 câu hỏi.
- Với mode child, không viết thêm các câu xã giao.
- Nếu bài nhiều bước / đổi đơn vị / rút về đơn vị:
  - opening phải hiện ra ngoài bằng chữ thật, không chỉ nghĩ nội bộ.
  - phải có đúng dạng:
    - Mình đi 2 bước
    - Bước 1: ...
    - Bước 2: ...
- Nếu flow_type là unit_conversion:
  - Nếu bài có dấu hiệu khác đơn vị, phải nhắc chú ý đổi về cùng đơn vị.
- Nếu flow_type là multiple_choice:
  - opening phải hiện:
    - Cách làm: mình xét từng đáp án một
    - Mình xét A trước nhé...
  - không được giải hết rồi chốt ngay.
- Nếu flow_type là multi_step:
  - không hiện phép tính ở opening.
- Nếu support_level là goi_y:
  - không được giải hộ sớm.
  - không được cho kết quả trung gian quá sớm.
"""
    return context.strip()


def _is_choice_only(text: str) -> bool:
    compact = normalize_text(text).replace(" ", "")
    return bool(
        re.match(r"^([abcd])$", compact, flags=re.IGNORECASE)
        or re.match(r"^(đápán|dapan)([abcd])$", compact, flags=re.IGNORECASE)
        or re.match(r"^(chọn|chon)([abcd])$", compact, flags=re.IGNORECASE)
    )


def classify_user_reply(user_input: str) -> str:
    text = normalize_text(user_input)
    if not text:
        return "empty"

    dont_know_signals = [
        "không biết",
        "ko biết",
        "k biết",
        "con không biết",
        "khó quá",
        "bí",
        "con bí",
        "không hiểu",
        "ko hiểu",
        "là sao",
    ]
    if any(signal in text for signal in dont_know_signals):
        return "student_dont_know"

    ask_answer_signals = [
        "đáp án",
        "giải luôn",
        "cho con đáp án",
        "cho đáp án",
        "giải hộ",
        "làm hộ",
        "cho con kết quả",
    ]
    if any(signal in text for signal in ask_answer_signals) and not _is_choice_only(text):
        return "student_asks_answer"

    if _is_choice_only(text):
        return "student_choice_only"

    cleaned = re.sub(r"[\s,\.]+", "", text)
    if cleaned.isdigit():
        return "student_number_only"

    return "normal_reply"


def is_small_error(user_input: str) -> bool:
    text = normalize_text(user_input)
    has_number = any(ch.isdigit() for ch in text)
    has_equal = "=" in text
    has_unit = any(
        unit in text
        for unit in [
            "bao",
            "cm",
            "kg",
            "g",
            "quyển",
            "chai",
            "khay",
            "mét",
            "xi măng",
            "quả",
            "cái",
            "m",
            "viên",
            "gạch",
            "hộp",
            "bút",
        ]
    )
    return has_number and not has_equal and not has_unit


def should_require_full_presentation(st, user_input: str) -> bool:
    text = normalize_text(user_input)

    has_equal = "=" in text
    has_unit = any(
        unit in text
        for unit in [
            "bao",
            "cm",
            "kg",
            "g",
            "quyển",
            "chai",
            "khay",
            "mét",
            "xi măng",
            "quả",
            "cái",
            "m",
            "viên",
            "gạch",
            "hộp",
            "bút",
        ]
    )

    if has_equal or has_unit:
        return False

    if _get_state_value(st.session_state, "presentation_retry_count", 0) >= 1:
        return False

    return True


def update_stuck_ui(st, reply_type: str):
    current = _get_state_value(st.session_state, "stuck_count", 0)
    if reply_type == "student_dont_know":
        current += 1
    else:
        current = max(0, current - 1)
    _set_state_value(st.session_state, "stuck_count", current)

    if _get_state_value(st.session_state, "is_finished", False):
        _set_state_value(st.session_state, "show_help_buttons", False)
        _set_state_value(st.session_state, "show_hint_button", False)
        _set_state_value(st.session_state, "show_solution_button", False)
        return

    _set_state_value(st.session_state, "show_help_buttons", current >= 1)
    _set_state_value(st.session_state, "show_hint_button", current >= 2)
    _set_state_value(
        st.session_state,
        "show_solution_button",
        current >= 3 or _get_state_value(st.session_state, "allow_full_solution", False),
    )


def detect_finished_response(response_text: str) -> bool:
    text = normalize_text(response_text)
    finish_signals = [
        "đã hoàn thành bài toán này",
        "đã làm xong bài này",
        "đáp số",
        "vậy mình sẽ nói là",
        "con giỏi lắm! con đã hoàn thành",
        "con đã hoàn thành bài này rồi",
        "kiến thức cần nhớ",
    ]
    return any(s in text for s in finish_signals)


def build_followup_context(
    problem_text: str,
    mode: str,
    support_level: str,
    chat_history: list,
    current_step: str,
    last_error_type: str,
    user_input: str,
    reply_type: str,
    allow_full_solution: bool,
    require_full_presentation: bool,
    small_error: bool,
    stuck_count: int,
    is_finished: bool,
    hint_request_count: int = 0,
) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    problem_type = detect_problem_type(problem_text)
    blueprint = get_problem_blueprint(problem_type)
    mc_rule = build_multiple_choice_rule(blueprint)

    history_text = ""
    for msg in chat_history[-6:]:
        role = "Học sinh" if msg.get("role") == "user" else "Thầy"
        history_text += f"- {role}: {msg.get('content', '')}\n"

    full_solution_rule = (
        "Được phép trình bày cách giải theo từng bước."
        if allow_full_solution
        else "Không được đưa lời giải đầy đủ hoặc đáp án cuối cùng ngay."
    )

    error_rule = (
        """
- Đây là lỗi nhỏ.
- Nếu học sinh đã ra đúng kết quả số hoặc gần đúng ý chính:
  - công nhận điều đúng trước
  - nhắc lỗi nhỏ ngắn gọn
  - có thể tự chốt câu trả lời đầy đủ
  - không giữ học sinh quá lâu
"""
        if small_error
        else
        """
- Nếu đây là lỗi lớn:
  - chỉ ra đúng chỗ sai
  - dạy tiếp ngắn gọn
  - kéo học sinh làm tiếp bước đúng
"""
    )

    presentation_rule = (
        "Có thể yêu cầu học sinh viết rõ phép tính hoặc đơn vị, nhưng chỉ ngắn gọn, không lặp lại nhiều lần."
        if require_full_presentation
        else "Không được giữ học sinh quá lâu ở việc viết lại phép tính hoặc đơn vị nếu con đã hiểu ý chính."
    )

    finish_rule = (
        "Bài đã hoàn tất. Không hỏi hỗ trợ thêm. Chỉ chốt ngắn gọn nếu cần."
        if is_finished
        else "Nếu bài vừa hoàn tất, hãy chốt đáp án đầy đủ và chốt 1-2 ý kiến thức cần nhớ."
    )

    context = f"""
{system_prompt}

{support_guide}

Đề bài hiện tại:
{problem_text}

Lịch sử gần đây:
{history_text}

Trạng thái hiện tại:
- mode: {mode}
- current_step: {current_step}
- last_error_type: {last_error_type}
- reply_type: {reply_type}
- allow_full_solution: {allow_full_solution}
- small_error: {small_error}
- is_finished: {is_finished}
- hint_request_count: {hint_request_count}

Luật rất quan trọng:
- {full_solution_rule}
- {presentation_rule}
{error_rule}
- stuck_count hiện tại là: {stuck_count}
- Nếu mode là child:
  - mỗi lượt chỉ 1 mục tiêu
  - chỉ 1 câu hỏi cuối
  - không lặp cùng một ý quá 1 lần
  - không hỏi rồi tự trả lời ngay
- Nếu flow_type là {blueprint.get('flow_type', '')}:
  - bám đúng flow của dạng bài này
- knowledge_used: {blueprint.get('knowledge_used', '')}
{mc_rule}
- {finish_rule}

Tin nhắn mới nhất của người dùng:
{user_input}
"""
    return context.strip()


def update_step_and_error(st, reply_type: str):
    mapping = {
        "student_dont_know": "khong_biet",
        "student_number_only": "chi_1_con_so",
        "student_asks_answer": "xin_dap_an",
        "student_choice_only": "chi_chon_dap_an",
    }
    _set_state_value(st.session_state, "last_error_type", mapping.get(reply_type, ""))


def update_presentation_retry(st, require_full_presentation: bool):
    if require_full_presentation:
        _set_state_value(
            st.session_state,
            "presentation_retry_count",
            _get_state_value(st.session_state, "presentation_retry_count", 0) + 1,
        )
    else:
        _set_state_value(st.session_state, "presentation_retry_count", 0)


def build_summary_context(problem_text: str, chat_history: list) -> str:
    summary_prompt = get_summary_prompt()
    history_text = ""
    for msg in chat_history[-10:]:
        role = "Học sinh" if msg.get("role") == "user" else "Thầy"
        history_text += f"- {role}: {msg.get('content', '')}\n"

    return f"""
{summary_prompt}

Đề bài:
{problem_text}

Lịch sử buổi học:
{history_text}
""".strip()


def _clean_num(text: str) -> int:
    return int(re.sub(r"\D", "", text))


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _extract_all_numbers(problem_text: str) -> list[int]:
    return [_clean_num(m) for m in re.findall(r"\d[\d .]*", problem_text)]


def _extract_named_distances(problem_text: str) -> list[dict]:
    items = []
    seen = set()
    for line in problem_text.splitlines():
        raw = line.strip(" -\t")
        if not raw:
            continue
        if ":" not in raw:
            continue
        digits = re.findall(r"\d[\d .]*", raw)
        if not digits:
            continue
        value = _clean_num(digits[-1])
        if value < 10:
            continue
        name_part, _ = raw.split(":", 1)
        name = re.sub(r"^đường đến\s*", "", name_part, flags=re.IGNORECASE).strip()
        key = (name.lower(), value)
        if key in seen:
            continue
        seen.add(key)
        items.append({"name": name, "value": value})
    return items


def _extract_options(problem_text: str) -> list[dict]:
    options = []
    flat = problem_text.replace("\n", " ")
    for match in re.finditer(r"([A-D])\.\s*(.*?)(?=\s+[A-D]\.\s*|$)", flat, flags=re.IGNORECASE):
        options.append({"letter": match.group(1).upper(), "text": match.group(2).strip()})
    return options


def _solve_geometry_farthest(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "xa nhất" not in text:
        return None

    items = _extract_named_distances(problem_text)
    options = _extract_options(problem_text)
    if not items:
        return None

    best = max(items, key=lambda item: item["value"])
    correct_letter = None
    for option in options:
        if normalize_text(option["text"]) in normalize_text(best["name"]):
            correct_letter = option["letter"]
            break
        if normalize_text(best["name"]) in normalize_text(option["text"]):
            correct_letter = option["letter"]
            break

    return {
        "kind": "geometry_farthest",
        "correct_name": best["name"],
        "correct_value": best["value"],
        "correct_letter": correct_letter,
        "items": items,
        "options": options,
        "answer_text": best["name"],
    }


def _solve_circle_mcq(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "hình tròn" not in text and "tâm hình tròn" not in text:
        return None

    options = _extract_options(problem_text)
    if not options:
        return None

    for option in options:
        option_text = normalize_text(option["text"])
        if re.search(r"\bo\b.*\blà tâm hình tròn\b", option_text):
            return {
                "kind": "circle_mcq",
                "correct_letter": option["letter"],
                "correct_name": option["text"],
                "options": options,
            }
    return None


def _parse_store_case(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "xếp đều vào" not in text or "mỗi chồng lấy ra bán" not in text:
        return None
    numbers = _extract_all_numbers(problem_text)
    if len(numbers) < 3:
        return None
    total, groups, sold_each = numbers[:3]
    sold_total = groups * sold_each
    answer = total - sold_total
    unit = "quyển vở" if "quyển vở" in text else "quyển"
    return {
        "kind": "store_case",
        "step_values": [sold_total, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} {unit}",
        "unit": unit,
    }


def _parse_unit_conversion_subtract(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if not any(token in text for token in ["m", "cm", "xăng-ti-mét"]) or "cắt đi" not in text:
        return None

    meter_match = re.search(r"(\d+)\s*m\s*(\d+)\s*cm", text)
    cut_match = re.search(r"cắt đi\s*(\d+)\s*cm", text)
    if not meter_match or not cut_match:
        return None

    total_cm = int(meter_match.group(1)) * 100 + int(meter_match.group(2))
    cut_cm = int(cut_match.group(1))
    answer = total_cm - cut_cm
    return {
        "kind": "unit_conversion_subtract",
        "step_values": [total_cm, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} cm",
        "unit": "cm",
        "total_converted": total_cm,
    }


def _parse_unit_rate_case(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if not any(k in text for k in ["như nhau", "tất cả"]):
        return None
    numbers = _extract_all_numbers(problem_text)
    if len(numbers) < 3:
        return None
    first_many, total, second_many = numbers[:3]
    if first_many == 0:
        return None
    one_part = total // first_many
    answer = one_part * second_many
    unit = "chiếc bút" if "chiếc bút" in text or "bút" in text else "đơn vị"
    group_name = "hộp" if "hộp" in text else "phần"
    return {
        "kind": "unit_rate",
        "step_values": [one_part, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} {unit}",
        "unit": unit,
        "group_name": group_name,
        "one_part": one_part,
    }


def _parse_multi_step_bricks(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "mỗi lần" not in text or "còn phải" not in text:
        return None
    numbers = _extract_all_numbers(problem_text)
    if len(numbers) < 3:
        return None
    target, times, each = numbers[:3]
    bought = times * each
    answer = target - bought
    unit = "viên gạch" if "viên gạch" in text else "viên"
    return {
        "kind": "multi_step_bricks",
        "step_values": [bought, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} {unit}",
        "unit": unit,
        "intermediate_label": "đã mua",
    }


def _parse_one_step_division(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "chia đều" not in text:
        return None
    numbers = _extract_all_numbers(problem_text)
    if len(numbers) < 2:
        return None
    total, groups = numbers[:2]
    if groups == 0:
        return None
    answer = total // groups
    if "chai" in text:
        unit = "chai"
    elif "quyển" in text:
        unit = "quyển"
    elif "bút" in text:
        unit = "chiếc bút"
    else:
        unit = "đơn vị"
    return {
        "kind": "one_step_division",
        "step_values": [answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} {unit}",
        "unit": unit,
    }




def _parse_perimeter_square(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "hình vuông" not in text:
        return None
    match = re.search(r"cạnh\s*(\d+)\s*cm", text)
    if not match:
        return None
    side = int(match.group(1))
    answer = side * 4
    return {
        "kind": "perimeter_square",
        "step_values": [4, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} cm",
        "side": side,
        "unit": "cm",
    }


def _parse_perimeter_rectangle(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "hình chữ nhật" not in text or "chiều dài" not in text or "chiều rộng" not in text:
        return None
    match = re.search(r"chiều dài\s*(\d+)\s*cm.*?chiều rộng\s*(\d+)\s*cm", text)
    if not match:
        return None
    length = int(match.group(1))
    width = int(match.group(2))
    summed = length + width
    answer = summed * 2
    return {
        "kind": "perimeter_rectangle",
        "step_values": [summed, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} cm",
        "length": length,
        "width": width,
        "unit": "cm",
    }


def _parse_predecessor(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "số liền trước" not in text:
        return None
    nums = _extract_all_numbers(problem_text)
    if not nums:
        return None
    base = nums[-1]
    answer = base - 1
    return {
        "kind": "predecessor",
        "answer_value": answer,
        "answer_text": _format_int(answer),
        "base": base,
    }


def _parse_successor(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "số liền sau" not in text:
        return None
    if "số lớn nhất có 4 chữ số" in text:
        base = 9999
    else:
        nums = _extract_all_numbers(problem_text)
        if not nums:
            return None
        base = nums[-1]
    answer = base + 1
    return {
        "kind": "successor",
        "answer_value": answer,
        "answer_text": _format_int(answer),
        "base": base,
    }


def _parse_unknown_minuend(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    match = re.search(r"bị trừ đi\s*(\d+)\s*thì được\s*(\d+)", text)
    if not match:
        return None
    subtrahend = int(match.group(1))
    difference = int(match.group(2))
    answer = subtrahend + difference
    return {
        "kind": "unknown_minuend",
        "step_values": [answer],
        "answer_value": answer,
        "answer_text": _format_int(answer),
        "subtrahend": subtrahend,
        "difference": difference,
    }


def _parse_operation_chain(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "->" not in problem_text or "ô trống" not in text:
        return None
    nums = _extract_all_numbers(problem_text)
    if len(nums) < 3:
        return None
    start, minus_value, divide_value = nums[:3]
    first_blank = start - minus_value
    if divide_value == 0:
        return None
    second_blank = first_blank // divide_value
    return {
        "kind": "operation_chain",
        "step_values": [first_blank, second_blank],
        "answer_value": second_blank,
        "answer_text": _format_int(second_blank),
        "start": start,
        "minus_value": minus_value,
        "divide_value": divide_value,
    }


def _parse_gift_then_subtract(problem_text: str) -> dict | None:
    text = normalize_text(problem_text)
    if "gấp" not in text or "còn lại" not in text:
        return None
    nums = _extract_all_numbers(problem_text)
    if len(nums) < 3:
        return None
    start, multiplier, subtract_value = nums[:3]
    gifted = start * multiplier
    total = start + gifted
    answer = total - subtract_value
    unit = "bông hoa" if "bông hoa" in text else "đơn vị"
    return {
        "kind": "gift_then_subtract",
        "step_values": [gifted, total, answer],
        "answer_value": answer,
        "answer_text": f"{_format_int(answer)} {unit}",
        "gifted": gifted,
        "total": total,
        "unit": unit,
        "multiplier": multiplier,
    }

def _solve_supported_problem(problem_text: str) -> dict | None:
    for solver in [
        _solve_geometry_farthest,
        _solve_circle_mcq,
        _parse_store_case,
        _parse_unit_conversion_subtract,
        _parse_unit_rate_case,
        _parse_multi_step_bricks,
        _parse_one_step_division,
        _parse_perimeter_square,
        _parse_perimeter_rectangle,
        _parse_predecessor,
        _parse_successor,
        _parse_unknown_minuend,
        _parse_operation_chain,
        _parse_gift_then_subtract,
    ]:
        solved = solver(problem_text)
        if solved is not None:
            return solved
    return None


def _build_micro_goals(problem_text: str) -> list[str]:
    blueprint = get_problem_blueprint(detect_problem_type(problem_text))
    flow_type = blueprint.get("flow_type")

    if flow_type == "unit_conversion":
        return [
            "Đổi về cùng đơn vị trước.",
            "Làm phép tính với đơn vị đã thống nhất.",
            "Viết đáp số kèm đơn vị.",
        ]

    if flow_type == "unit_rate":
        return [
            "Tìm 1 phần trước.",
            "Tìm nhiều phần cần hỏi.",
            "Viết đáp số kèm đơn vị.",
        ]

    if flow_type == "multi_step":
        return [
            "Tìm phần đã có hoặc đã làm xong.",
            "Tìm phần còn thiếu hoặc còn lại.",
            "Viết đáp số kèm đơn vị.",
        ]

    if flow_type == "multiple_choice":
        return [
            "Xét đáp án A.",
            "Nếu cần, xét tiếp B, C, D.",
            "Chốt đáp án đúng.",
        ]

    return ["Làm phép tính chính.", "Viết đáp số kèm đơn vị."]


def _infer_active_micro_goal(problem_text: str, chat_history: list) -> dict:
    goals = _build_micro_goals(problem_text)
    assistant_text = "\n".join(
        normalize_text(msg.get("content", ""))
        for msg in chat_history
        if msg.get("role") == "assistant"
    )

    index = 0
    if len(goals) >= 3 and any(word in assistant_text for word in ["đổi", "cùng đơn vị", "325 cm", "1 phần", "đã mua", "xét a"]):
        index = 1
    if len(goals) >= 3 and any(word in assistant_text for word in ["đáp số", "viết đáp số", "đơn vị"]):
        index = min(2, len(goals) - 1)

    return {"index": index, "goal": goals[index], "goals": goals}


def _line_block(lines: list[str]) -> str:
    return "\n".join([line for line in lines if line]).strip()




def _build_supported_opening_from_solution(problem_text: str, solved: dict | None) -> str | None:
    if not solved:
        return None

    kind = solved.get("kind")
    if kind == "geometry_farthest":
        return _line_block([
            "Dạng bài: So sánh quãng đường để chọn đáp án đúng.",
            "Kiến thức dùng: tìm số lớn nhất rồi ghép với đúng vườn hoa.",
            "Cách nghĩ nhanh: nhìn 4 số đường dài và chọn số lớn nhất.",
            "Con nhìn 4 số này nhé: số nào lớn nhất?",
        ])
    if kind == "perimeter_square":
        return _line_block([
            "Dạng bài: Chu vi hình vuông.",
            "Kiến thức dùng: lấy số đo 1 cạnh nhân 4.",
            "Cách nghĩ nhanh: hình vuông có 4 cạnh bằng nhau.",
            "Con cho Thầy biết hình vuông có mấy cạnh nào?",
        ])
    if kind == "perimeter_rectangle":
        return _line_block([
            "Dạng bài: Chu vi hình chữ nhật.",
            "Kiến thức dùng: cộng chiều dài với chiều rộng rồi nhân 2.",
            "Cách nghĩ nhanh: mình tìm tổng dài và rộng trước.",
            "Con thử cộng 12 với 7 trước nhé?",
        ])
    if kind == "predecessor":
        return _line_block([
            "Dạng bài: Số liền trước.",
            "Kiến thức dùng: lấy số đã cho trừ 1.",
            "Cách nghĩ nhanh: lùi lại 1 đơn vị.",
            "Con thử lấy số đó bớt 1 xem nào?",
        ])
    if kind == "successor":
        return _line_block([
            "Dạng bài: Số liền sau.",
            "Kiến thức dùng: lấy số đã cho cộng 1.",
            "Cách nghĩ nhanh: tiến thêm 1 đơn vị.",
            "Con thử nghĩ xem sau 9 999 là số nào?",
        ])
    if kind == "unknown_minuend":
        return _line_block([
            "Dạng bài: Tìm số bị trừ.",
            "Kiến thức dùng: muốn tìm số bị trừ thì lấy hiệu cộng số trừ.",
            "Cách nghĩ nhanh: nhìn hai số đã biết rồi cộng lại.",
            "Con thử lấy 348 cộng 125 nhé?",
        ])
    if kind == "operation_chain":
        return _line_block([
            "Dạng bài: Chuỗi thao tác.",
            "Kiến thức dùng: làm lần lượt từ trái sang phải.",
            "Cách nghĩ nhanh: tính ô trước rồi mới sang ô sau.",
            "Con thử tính ô trống đầu tiên trước nhé?",
        ])
    if kind == "gift_then_subtract":
        return _line_block([
            "Dạng bài: Toán nhiều bước.",
            "Kiến thức dùng: tìm phần được cho thêm rồi tính phần còn lại.",
            "Cách nghĩ nhanh: nhìn phần gấp lên trước rồi mới trừ tiếp.",
            "Con thử tìm xem mẹ cho thêm bao nhiêu bông trước nhé?",
        ])
    return None


def _build_child_opening(problem_text: str, blueprint: dict) -> str:
    flow_type = blueprint.get("flow_type", "")
    label = blueprint.get("label", "Bài toán")
    knowledge = blueprint.get("knowledge_used", "")
    plan_steps = blueprint.get("plan_steps", [])

    if flow_type == "multiple_choice":
        return _line_block([
            f"Dạng bài: {label}",
            f"Kiến thức dùng: {knowledge}",
            "Cách nghĩ nhanh: mình xét từng đáp án một.",
            "Mình xét A trước nhé. Con nhìn A xem đúng hay sai?",
        ])

    if blueprint.get("show_plan_steps") and len(plan_steps) >= 2:
        return _line_block([
            f"Dạng bài: {label}",
            f"Kiến thức dùng: {knowledge}",
            f"Cách nghĩ nhanh: Mình đi {len(plan_steps)} bước.",
            f"Bước 1: {plan_steps[0]}. Bước 2: {plan_steps[1]}. Con nói Thầy nghe bước 1 là gì nhé?",
        ])

    return _line_block([
        f"Dạng bài: {label}",
        f"Kiến thức dùng: {knowledge}",
        "Cách nghĩ nhanh: làm đúng ý chính trước rồi mới chốt đáp án.",
        "Con thử nói bước đầu tiên mình nên làm nhé?",
    ])


def _build_parent_opening(problem_text: str, blueprint: dict, solved: dict | None) -> str:
    plan_steps = blueprint.get("plan_steps", [])
    lines = [
        f"Dạng bài: {blueprint.get('label', 'Bài toán')}",
        f"Kiến thức dùng: {blueprint.get('knowledge_used', '')}",
    ]

    if blueprint.get("flow_type") == "multiple_choice":
        lines.append("Hướng làm cả bài: cho con xét từng đáp án một, bắt đầu từ A, không chốt theo cảm giác.")
    elif blueprint.get("show_plan_steps") and len(plan_steps) >= 2:
        lines.append(f"Hướng làm cả bài: đi {len(plan_steps)} bước — bước 1 {plan_steps[0].lower()}, bước 2 {plan_steps[1].lower()}.")
    else:
        lines.append("Hướng làm cả bài: xác định đúng phép tính chính rồi mới viết câu trả lời.")

    common_errors = blueprint.get("common_errors", [])
    if common_errors:
        lines.append(f"Lỗi dễ mắc: {common_errors[0]}.")
    lines.append("Ba mẹ nên hỏi con: Con đang làm bước nào trước?")
    if solved and solved.get("answer_text") and blueprint.get("flow_type") != "multiple_choice":
        lines.append(f"Lời giải mẫu ngắn: Đáp số {solved['answer_text']}.")
    return _line_block(lines)


def _extract_choice_letter(user_input: str) -> str | None:
    normalized = normalize_user_input(user_input)
    match = re.search(r"\b([A-D])\b", normalized)
    return match.group(1).upper() if match else None


def _extract_last_number(user_input: str) -> int | None:
    matches = re.findall(r"\d[\d .]*", user_input or "")
    if not matches:
        return None
    return _clean_num(matches[-1])


def responses_too_similar(previous: str, current: str) -> bool:
    a = normalize_text(previous)
    b = normalize_text(current)
    if not a or not b:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.86


def should_mark_finished_after_child_help(response: str, hint_request_count: int) -> bool:
    text = normalize_text(response)
    if "đáp số" in text or "kiến thức cần nhớ" in text:
        return True
    if hint_request_count >= 3 and any(k in text for k in ["vậy", "kết quả", "đáp án"]):
        return True
    return False


def generate_opening_tutoring_response(problem_text: str, mode: str, support_level: str) -> str | None:
    problem_type = detect_problem_type(problem_text)
    blueprint = get_problem_blueprint(problem_type)
    flow_type = blueprint.get("flow_type", "")
    solved = _solve_supported_problem(problem_text)
    _ = support_level

    if mode == "parent":
        return _build_parent_opening(problem_text, blueprint, solved)

    if mode == "child" and flow_type in {"multi_step", "unit_conversion", "unit_rate", "multiple_choice"}:
        return _build_child_opening(problem_text, blueprint)

    if mode == "child":
        supported_opening = _build_supported_opening_from_solution(problem_text, solved)
        if supported_opening:
            return supported_opening

    return None


def _child_hint_for_supported_problem(problem_text: str, solved: dict | None, stuck_count: int) -> str | None:
    blueprint = get_problem_blueprint(detect_problem_type(problem_text))
    flow_type = blueprint.get("flow_type", "")

    if flow_type == "multiple_choice":
        if solved and solved.get("kind") == "geometry_farthest":
            return "Mình tìm số lớn nhất trong 4 quãng đường nhé. Con nhìn xem số nào lớn nhất?"
        if solved and solved.get("kind") == "circle_mcq":
            return "Mình xét A trước nhé. OQ đi từ tâm ra đường tròn, vậy nó là bán kính hay đường kính?"
        return "Mình xét từng đáp án một nhé. Con nhìn A trước: A đúng hay sai?"

    if flow_type == "unit_conversion":
        if solved and solved.get("kind") == "unit_conversion_subtract":
            total_cm = solved.get("total_converted")
            if stuck_count >= 2:
                return f"Mình đổi về cùng đơn vị trước nhé: 3 m 25 cm = {_format_int(total_cm)} cm. Rồi con làm phép trừ tiếp nào?"
            return "Trước hết con đổi về cùng một đơn vị nhé. Ở đây mình nên đổi hết ra cm."

    if flow_type == "unit_rate":
        if solved and solved.get("kind") == "unit_rate":
            if stuck_count >= 2:
                return f"Mình tìm 1 {solved['group_name']} trước nhé: lấy tổng số chia cho số {solved['group_name']}."
            return f"Đây là bài rút về đơn vị. Con tìm 1 {solved['group_name']} trước nhé."

    if flow_type == "multi_step":
        if solved and solved.get("kind") == "multi_step_bricks":
            if stuck_count >= 2:
                return "Bước 1 mình tìm số viên gạch đã mua bằng phép nhân nhé."
            return "Mình đi 2 bước. Con tìm phần đã có trước nhé."
        if solved and solved.get("kind") == "store_case":
            if stuck_count >= 2:
                return "Mình tìm số quyển đã bán trước nhé: số chồng nhân với số quyển bán ở mỗi chồng."
            return "Mình đi 2 bước. Con tìm số đã bán trước nhé."
        if solved and solved.get("kind") == "operation_chain":
            return "Mình làm từ trái sang phải nhé. Con tính ô trống đầu tiên trước nào."
        if solved and solved.get("kind") == "gift_then_subtract":
            return "Con tìm phần mẹ cho thêm trước nhé. Ở đây mình nhìn vào chỗ gấp 4 lần."

    if solved and solved.get("kind") == "one_step_division":
        return "Đây là bài chia đều. Con lấy tổng số chia cho số phần nhé."
    if solved and solved.get("kind") == "perimeter_square":
        return "Hình vuông có 4 cạnh bằng nhau. Con lấy 1 cạnh nhân 4 nhé."
    if solved and solved.get("kind") == "perimeter_rectangle":
        return "Con cộng chiều dài với chiều rộng trước nhé, rồi mới nhân 2."
    if solved and solved.get("kind") == "predecessor":
        return "Số liền trước thì mình lùi lại 1 đơn vị nhé."
    if solved and solved.get("kind") == "successor":
        return "Số liền sau thì mình tiến thêm 1 đơn vị nhé."
    if solved and solved.get("kind") == "unknown_minuend":
        return "Muốn tìm số bị trừ, con lấy hiệu cộng số trừ nhé."

    return None


def _child_reply_for_supported_problem(
    problem_text: str,
    user_input: str,
    reply_type: str,
    allow_full_solution: bool,
    support_level: str,
    stuck_count: int,
) -> str | None:
    solved = _solve_supported_problem(problem_text)
    blueprint = get_problem_blueprint(detect_problem_type(problem_text))
    flow_type = blueprint.get("flow_type", "")

    if reply_type == "student_asks_answer" and not allow_full_solution:
        hint = _child_hint_for_supported_problem(problem_text, solved, max(stuck_count, 1))
        if hint:
            return f"Thầy chưa chốt đáp án ngay nhé. {hint}"

    if reply_type == "student_dont_know":
        return _child_hint_for_supported_problem(problem_text, solved, max(stuck_count, 1))

    if flow_type == "multiple_choice" and solved:
        letter = _extract_choice_letter(user_input)
        if solved.get("kind") == "geometry_farthest":
            if letter and solved.get("correct_letter"):
                if letter == solved["correct_letter"]:
                    return _line_block([
                        f"Đúng rồi, {letter} là đáp án đúng.",
                        f"Vì {solved['correct_name']} là xa nhất: {_format_int(solved['correct_value'])} m.",
                        "Kiến thức cần nhớ: bài kiểu này mình tìm số lớn nhất rồi ghép với đúng đối tượng.",
                    ])
                return "Chưa đúng nhé. Con so lại 4 số đường dài một lần nữa xem số nào lớn nhất?"
            return "Con nhìn 4 số quãng đường nhé. Số nào lớn nhất thì đó là đáp án đúng."

        if solved.get("kind") == "circle_mcq":
            if letter and solved.get("correct_letter"):
                if letter == solved["correct_letter"]:
                    return _line_block([
                        f"Đúng rồi, {letter} là đáp án đúng.",
                        f"Vì đáp án đúng là: {solved['correct_name']}.",
                        "Kiến thức cần nhớ: bán kính đi từ tâm ra đường tròn, còn đường kính đi qua tâm và nối hai điểm trên đường tròn.",
                    ])
                return "Chưa đúng nhé. Con nhìn lại A và C xem: OQ, OP đều chỉ đi từ tâm ra đường tròn thôi. Vậy chúng là gì nhỉ?"
            return "Mình xét A trước nhé. OQ đi từ tâm O ra đường tròn, vậy nó là bán kính hay đường kính?"

        if letter and solved.get("correct_letter"):
            if letter == solved["correct_letter"]:
                return _line_block([
                    f"Đúng rồi, {letter} là đáp án đúng.",
                    f"Vì đáp án đúng là: {solved['correct_name']}.",
                    "Kiến thức cần nhớ: bài trắc nghiệm nên xét từng đáp án một.",
                ])
            return f"Chưa đúng nhé. Mình chưa chốt vội. Con quay lại xét A trước, xem A đúng hay sai nào?"
        return "Mình xét từng đáp án một nhé. Con thử nói đáp án A đúng hay sai trước nào?"

    if not solved:
        return None

    user_number = _extract_last_number(user_input)

    if solved.get("kind") == "unit_conversion_subtract":
        total_cm, answer = solved["step_values"]
        if user_number == total_cm:
            return f"Đúng rồi, con đã đổi được {_format_int(total_cm)} cm. Giờ con lấy {_format_int(total_cm)} trừ 75 nhé."
        if user_number == answer:
            return _line_block([
                f"Đúng rồi, còn lại {solved['answer_text']}.",
                f"Đáp số: {solved['answer_text']}.",
                "Kiến thức cần nhớ: đổi về cùng đơn vị trước rồi mới tính.",
            ])

    if solved.get("kind") in {"multi_step_bricks", "store_case", "unit_rate", "operation_chain", "gift_then_subtract"}:
        steps = solved["step_values"]
        if solved.get("kind") == "operation_chain":
            first_blank, second_blank = steps
            if user_number == first_blank:
                return f"Đúng rồi, ô trống đầu tiên là {_format_int(first_blank)}. Giờ con lấy {_format_int(first_blank)} chia 5 nhé."
            if user_number == second_blank:
                return _line_block([
                    f"Đúng rồi, ô cuối là {_format_int(second_blank)}.",
                    f"Đáp số: {_format_int(second_blank)}.",
                    "Kiến thức cần nhớ: chuỗi thao tác thì làm từ trái sang phải.",
                ])
        elif solved.get("kind") == "gift_then_subtract":
            gifted, total, answer = steps
            if user_number == gifted:
                return f"Đúng rồi, mẹ cho thêm {_format_int(gifted)} {solved['unit']}. Giờ con tìm tất cả có bao nhiêu bông nhé."
            if user_number == total:
                return f"Đúng rồi, tất cả có {_format_int(total)} {solved['unit']}. Giờ con trừ tiếp 9 nhé."
            if user_number == answer:
                return _line_block([
                    f"Đúng rồi, Lan còn lại {solved['answer_text']}.",
                    f"Đáp số: {solved['answer_text']}.",
                    "Kiến thức cần nhớ: bài nhiều bước thì làm lần lượt từng phần.",
                ])
        else:
            if len(steps) >= 2 and user_number == steps[0]:
                if solved["kind"] == "unit_rate":
                    return f"Đúng rồi, con đã tìm được 1 {solved['group_name']} là {_format_int(steps[0])}. Giờ con tìm số của phần cần hỏi nhé."
                if solved["kind"] == "multi_step_bricks":
                    return f"Đúng rồi, bác đã mua {_format_int(steps[0])} viên gạch. Giờ con lấy 78 000 trừ {_format_int(steps[0])} nhé."
                return f"Đúng rồi, đã bán {_format_int(steps[0])} {solved['unit']}. Giờ con tìm phần còn lại nhé."
            if user_number == solved["answer_value"]:
                return _line_block([
                    f"Đúng rồi, kết quả là {solved['answer_text']}.",
                    f"Đáp số: {solved['answer_text']}.",
                    "Kiến thức cần nhớ: làm xong bước 1 rồi mới sang bước 2.",
                ])

    if solved.get("kind") == "one_step_division":
        if user_number == solved["answer_value"]:
            if support_level == "goi_y" and reply_type == "student_number_only":
                return f"Đúng kết quả số rồi. Con viết đầy đủ giúp Thầy: {solved['answer_text']}."
            return _line_block([
                f"Đúng rồi, mỗi phần có {solved['answer_text']}.",
                f"Đáp số: {solved['answer_text']}.",
                "Kiến thức cần nhớ: bài chia đều thì lấy tổng số chia cho số phần.",
            ])

    if solved.get("kind") == "perimeter_square":
        if user_number == 4:
            return f"Đúng rồi, hình vuông có 4 cạnh. Giờ con lấy {solved['side']} nhân 4 nhé."
        if user_number == solved["answer_value"]:
            return _line_block([
                f"Đúng rồi, chu vi là {solved['answer_text']}.",
                f"Đáp số: {solved['answer_text']}.",
                "Kiến thức cần nhớ: chu vi hình vuông bằng cạnh nhân 4.",
            ])

    if solved.get("kind") == "perimeter_rectangle":
        summed, answer = solved["step_values"]
        if user_number == summed:
            return f"Đúng rồi, con đã tìm được {solved['length']} + {solved['width']} = {_format_int(summed)}. Giờ con nhân 2 nhé."
        if user_number == answer:
            return _line_block([
                f"Đúng rồi, chu vi là {solved['answer_text']}.",
                f"Đáp số: {solved['answer_text']}.",
                "Kiến thức cần nhớ: chu vi hình chữ nhật bằng (dài + rộng) nhân 2.",
            ])

    if solved.get("kind") in {"predecessor", "successor", "unknown_minuend"}:
        if user_number == solved["answer_value"]:
            reminder = {
                "predecessor": "số liền trước thì trừ 1.",
                "successor": "số liền sau thì cộng 1.",
                "unknown_minuend": "muốn tìm số bị trừ thì lấy hiệu cộng số trừ.",
            }[solved["kind"]]
            return _line_block([
                f"Đúng rồi, kết quả là {solved['answer_text']}.",
                f"Đáp số: {solved['answer_text']}.",
                f"Kiến thức cần nhớ: {reminder}",
            ])

    if allow_full_solution or support_level == "cach_giai":
        if solved.get("kind") == "unit_conversion_subtract":
            total_cm, answer = solved["step_values"]
            return _line_block([
                f"Mình làm thế này nhé: 3 m 25 cm = {_format_int(total_cm)} cm.",
                f"Rồi lấy {_format_int(total_cm)} - 75 = {_format_int(answer)} cm.",
                f"Đáp số: {solved['answer_text']}.",
                "Kiến thức cần nhớ: đổi về cùng đơn vị trước rồi mới tính.",
            ])
        if solved.get("kind") in {"multi_step_bricks", "store_case", "unit_rate", "one_step_division", "perimeter_square", "perimeter_rectangle", "predecessor", "successor", "unknown_minuend", "operation_chain", "gift_then_subtract"}:
            lines = []
            if solved.get("kind") == "multi_step_bricks":
                bought, answer = solved["step_values"]
                lines.extend([
                    f"Bước 1: Bác đã mua {_format_int(bought)} viên gạch.",
                    f"Bước 2: Còn phải mua {_format_int(answer)} viên gạch.",
                ])
            elif solved.get("kind") == "store_case":
                sold, answer = solved["step_values"]
                lines.extend([
                    f"Bước 1: Đã bán {_format_int(sold)} quyển vở.",
                    f"Bước 2: Còn lại {_format_int(answer)} quyển vở.",
                ])
            elif solved.get("kind") == "unit_rate":
                one_part, answer = solved["step_values"]
                lines.extend([
                    f"Bước 1: 1 {solved['group_name']} có {_format_int(one_part)} {solved['unit']}.",
                    f"Bước 2: Phần cần tìm có {solved['answer_text']}.",
                ])
            elif solved.get("kind") == "one_step_division":
                lines.append(f"Lấy tổng số chia cho số phần, được {solved['answer_text']}.")
            elif solved.get("kind") == "perimeter_square":
                lines.append(f"Hình vuông có 4 cạnh nên lấy {solved['side']} x 4 = {_format_int(solved['answer_value'])} cm.")
            elif solved.get("kind") == "perimeter_rectangle":
                summed, answer = solved['step_values']
                lines.extend([
                    f"Bước 1: {solved['length']} + {solved['width']} = {_format_int(summed)}.",
                    f"Bước 2: {_format_int(summed)} x 2 = {_format_int(answer)} cm.",
                ])
            elif solved.get("kind") == "predecessor":
                lines.append(f"Số liền trước của {_format_int(solved['base'])} là {_format_int(solved['answer_value'])}.")
            elif solved.get("kind") == "successor":
                lines.append(f"Số liền sau của {_format_int(solved['base'])} là {_format_int(solved['answer_value'])}.")
            elif solved.get("kind") == "unknown_minuend":
                lines.append(f"Muốn tìm số bị trừ, lấy {solved['difference']} + {solved['subtrahend']} = {_format_int(solved['answer_value'])}.")
            elif solved.get("kind") == "operation_chain":
                first_blank, second_blank = solved['step_values']
                lines.extend([
                    f"Ô trống thứ nhất: {solved['start']} - {solved['minus_value']} = {_format_int(first_blank)}.",
                    f"Ô trống thứ hai: {_format_int(first_blank)} : {solved['divide_value']} = {_format_int(second_blank)}.",
                ])
            elif solved.get("kind") == "gift_then_subtract":
                gifted, total, answer = solved['step_values']
                lines.extend([
                    f"Bước 1: Mẹ cho thêm {_format_int(gifted)} {solved['unit']}.",
                    f"Bước 2: Lan có tất cả {_format_int(total)} {solved['unit']}.",
                    f"Bước 3: Lan còn lại {_format_int(answer)} {solved['unit']}.",
                ])
            lines.extend([
                f"Đáp số: {solved['answer_text']}.",
                "Kiến thức cần nhớ: đi đúng thứ tự các bước của bài.",
            ])
            return _line_block(lines)

    return None


def generate_followup_tutoring_response(
    problem_text: str,
    mode: str,
    support_level: str,
    chat_history: list,
    current_step: str | None = None,
    last_error_type: str | None = None,
    user_input: str = "",
    reply_type: str = "normal_reply",
    allow_full_solution: bool = False,
    require_full_presentation: bool = False,
    small_error: bool = False,
    stuck_count: int = 0,
    is_finished: bool = False,
    hint_request_count: int = 0,
) -> str | None:
    del chat_history, current_step, last_error_type, require_full_presentation, small_error, is_finished, hint_request_count

    if mode == "child":
        return _child_reply_for_supported_problem(
            problem_text=problem_text,
            user_input=user_input,
            reply_type=reply_type,
            allow_full_solution=allow_full_solution,
            support_level=support_level,
            stuck_count=stuck_count,
        )

    solved = _solve_supported_problem(problem_text)
    blueprint = get_problem_blueprint(detect_problem_type(problem_text))
    if solved and reply_type in {"student_asks_answer", "student_dont_know"}:
        return _build_parent_opening(problem_text, blueprint, solved)
    return None
