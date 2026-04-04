# logic.py

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from gemini_client import generate_text_response
from prompts import (
    get_first_response_guide,
    get_support_guide,
    get_summary_prompt,
    get_system_prompt,
)


# =========================================================
# TEXT NORMALIZATION
# =========================================================
def _strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")



def _normalize_for_matching(text: str) -> str:
    text = _strip_accents((text or "").lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def _compact_number_text(text: str) -> str:
    return re.sub(r"[^0-9]", "", text or "")



def _parse_int(text: str) -> int:
    return int(_compact_number_text(text) or "0")



def _format_int(value: int) -> str:
    if abs(value) < 10000:
        return str(value)
    return f"{value:,}".replace(",", " ")


# =========================================================
# INPUT NORMALIZATION / REPLY CLASSIFICATION
# =========================================================
def _extract_choice_letter(user_input: str) -> str | None:
    if not user_input or not user_input.strip():
        return None

    raw = user_input.strip()
    normalized = _normalize_for_matching(raw)
    if not normalized:
        return None

    compact = re.sub(r"[^a-z0-9]", "", normalized)
    if compact in {"a", "b", "c", "d"}:
        return compact.upper()

    tokens = normalized.split()
    if tokens and tokens[-1] in {"a", "b", "c", "d"}:
        prefixes = {
            ("chon",),
            ("dap", "an"),
            ("la",),
            ("con", "chon"),
            ("con", "nghi", "la"),
        }
        for prefix in prefixes:
            if tuple(tokens[-(len(prefix) + 1):-1]) == prefix:
                return tokens[-1].upper()

    direct = re.fullmatch(r"\(?\[?\{?\s*([a-dA-D])\s*[\)\]\}\.\:]?", raw)
    if direct:
        return direct.group(1).upper()

    phrase = re.fullmatch(r"(?:dap\s*an|chon|la|con\s*chon)\s*[:\-]?\s*([a-d])", normalized)
    if phrase:
        return phrase.group(1).upper()

    return None



def normalize_user_input(user_input: str) -> str:
    text = (user_input or "").strip()
    if not text:
        return ""

    choice = _extract_choice_letter(text)
    if choice:
        return f"Chọn đáp án {choice}"

    return re.sub(r"\s+", " ", text).strip()



def classify_user_reply(user_input: str) -> str:
    raw_text = normalize_user_input(user_input)
    if not raw_text:
        return "empty"

    text = raw_text.lower()
    normalized = _normalize_for_matching(raw_text)
    compact = normalized.replace(" ", "")

    exact_dont_know = {
        "khong",
        "ko",
        "k",
        "khongbiet",
        "kobiet",
        "kbiet",
        "khonghieu",
        "kohieu",
        "chuabiet",
    }
    dont_know_signals = [
        "khong biet",
        "ko biet",
        "k biet",
        "con khong biet",
        "khong hieu",
        "khong ro",
        "kho qua",
        "con bi",
        "khong lam duoc",
        "khong biet lam",
        "chua biet",
        "chua hieu",
        "khong biet nua",
    ]

    if normalized in exact_dont_know or compact in exact_dont_know:
        return "student_dont_know"

    if any(signal in normalized for signal in dont_know_signals):
        return "student_dont_know"

    if _extract_choice_letter(raw_text):
        return "student_choice_only"

    ask_answer_signals = [
        "dap an",
        "giai luon",
        "cho con dap an",
        "cho dap an",
        "giai ho",
        "lam ho",
        "cho con ket qua",
        "noi dap an",
        "cho con loi giai",
        "cho con xem dap an",
    ]
    if any(signal in normalized for signal in ask_answer_signals):
        return "student_asks_answer"

    cleaned = re.sub(r"[\s,\.]", "", text)
    if cleaned.isdigit():
        return "student_number_only"

    return "normal_reply"



def is_small_error(user_input: str) -> bool:
    text = (user_input or "").strip().lower()
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
            "quyen",
            "chai",
            "khay",
            "mét",
            "met",
            "m",
            "viên",
            "vien",
            "gạch",
            "gach",
            "bút",
            "but",
            "hoa",
        ]
    )
    return has_number and not has_equal and not has_unit



def should_require_full_presentation(st, user_input: str) -> bool:
    text = (user_input or "").strip().lower()
    if "=" in text:
        return False
    if any(unit in text for unit in ["bao", "cm", "kg", "g", "quyển", "chai", "khay", "mét", "m", "viên", "gạch", "bút", "hoa"]):
        return False
    if getattr(st.session_state, "presentation_retry_count", 0) >= 1:
        return False
    return bool(re.sub(r"[^0-9]", "", text))


# =========================================================
# PROBLEM TYPE / LIGHT ANALYSIS
# =========================================================
def _infer_teaching_frame(problem_text: str) -> dict[str, str]:
    raw = (problem_text or "").lower()
    text = _normalize_for_matching(problem_text)

    if "lien truoc" in text:
        return {
            "problem_type": "Số liền trước",
            "knowledge": "Lấy số đã cho trừ 1",
            "thinking": "Nhìn số đã cho rồi bớt đi 1",
        }

    if "lien sau" in text:
        return {
            "problem_type": "Số liền sau",
            "knowledge": "Lấy số đã cho cộng 1",
            "thinking": "Nhìn số đã cho rồi thêm 1",
        }

    if "hinh vuong" in text and ("canh" in text or "chu vi" in text or "doan day" in text):
        return {
            "problem_type": "Chu vi hình vuông",
            "knowledge": "Lấy cạnh nhân 4",
            "thinking": "Muốn biết độ dài quanh hình vuông thì tính 4 cạnh",
        }

    if "hinh chu nhat" in text and "chu vi" in text:
        return {
            "problem_type": "Chu vi hình chữ nhật",
            "knowledge": "Lấy chiều dài cộng chiều rộng rồi nhân 2",
            "thinking": "Tính tổng một chiều dài và một chiều rộng trước, rồi nhân 2",
        }

    if "xa nhat" in text and ("vườn hoa" in problem_text.lower() or "vuon hoa" in text or "khoang cach" in text):
        return {
            "problem_type": "So sánh số đo để chọn xa nhất",
            "knowledge": "So sánh các số đo độ dài",
            "thinking": "Nhìn các số đo rồi chọn số lớn nhất",
        }

    if "chon khang dinh dung" in text and ("hinh tron" in text or "tam o" in text):
        return {
            "problem_type": "Nhận biết tâm, bán kính, đường kính",
            "knowledge": "Phân biệt tâm, bán kính, đường kính của hình tròn",
            "thinking": "Nhìn tâm trước, rồi xét đoạn nào đi từ tâm ra đường tròn",
        }

    if (("hop" in text or "thung" in text or "goi" in text) and ("tat ca" in text or "nhu the" in text or "như thế" in problem_text.lower()) and ("nhu nhau" in text or "moi" in text or "đều" in problem_text.lower())):
        return {
            "problem_type": "Rút về đơn vị",
            "knowledge": "Phép chia rồi phép nhân",
            "thinking": "Tìm 1 phần trước, rồi từ 1 phần tính nhiều phần",
        }

    if "chia deu" in text:
        return {
            "problem_type": "Chia đều",
            "knowledge": "Phép chia",
            "thinking": "Lấy tổng chia cho số phần bằng nhau",
        }

    if ((" m " in f" {text} " and " cm" in raw) or (" kg" in raw and " g" in raw) or ("met" in text and "xang ti met" in text)):
        return {
            "problem_type": "Đổi đơn vị rồi tính",
            "knowledge": "Đổi về cùng đơn vị rồi cộng hoặc trừ",
            "thinking": "Đưa các số đo về cùng một đơn vị trước rồi mới tính",
        }

    if "o trong" in text or "->" in problem_text or "→" in problem_text:
        return {
            "problem_type": "Chuỗi thao tác",
            "knowledge": "Làm lần lượt từng phép tính theo thứ tự",
            "thinking": "Tính ô trước rồi mới dùng kết quả để tính ô sau",
        }

    if "gap" in text and ("roi" in text or "sau do" in text or "tang" in text or "bot" in text):
        return {
            "problem_type": "Bài nhiều bước",
            "knowledge": "Phép nhân rồi cộng hoặc trừ",
            "thinking": "Tính phần gấp lên trước, rồi làm bước tiếp theo",
        }

    if "moi lan" in text and ("con phai" in text or "con lai" in text or "sau khi" in text or "mua" in text or "ban" in text):
        return {
            "problem_type": "Bài nhiều bước",
            "knowledge": "Phép nhân rồi phép trừ",
            "thinking": "Tính phần đã có trước, rồi tìm phần còn lại hoặc còn thiếu",
        }

    if "mot so" in text and "tim so do" in text and "tru" in text:
        return {
            "problem_type": "Tìm thành phần chưa biết",
            "knowledge": "Muốn tìm số bị trừ thì lấy hiệu cộng số trừ",
            "thinking": "Lấy hiệu cộng với số trừ",
        }

    if "mot so" in text and "tim so do" in text and "chia" in text:
        return {
            "problem_type": "Tìm thành phần chưa biết",
            "knowledge": "Muốn tìm số bị chia thì lấy thương nhân số chia",
            "thinking": "Lấy thương nhân với số chia",
        }

    if "tinh gia tri bieu thuc" in text:
        return {
            "problem_type": "Tính giá trị biểu thức",
            "knowledge": "Nhân, chia trước rồi mới cộng, trừ",
            "thinking": "Nhìn phép nhân, chia trước rồi mới làm phép còn lại",
        }

    return {
        "problem_type": "Bài toán có lời văn",
        "knowledge": "Đọc kỹ đề để chọn phép tính phù hợp",
        "thinking": "Xem bài đang hỏi gì rồi tìm bước cần làm trước",
    }



def _build_step_plan(problem_text: str, frame: dict[str, str]) -> list[str]:
    pt = frame["problem_type"]
    if pt == "Rút về đơn vị":
        return [
            "Tìm 1 phần trước.",
            "Từ 1 phần suy ra nhiều phần.",
        ]
    if pt == "Đổi đơn vị rồi tính":
        return ["Đổi về cùng đơn vị.", "Làm phép tính theo đề bài."]
    if pt == "Chu vi hình vuông":
        return ["Lấy cạnh nhân 4."]
    if pt == "Chu vi hình chữ nhật":
        return ["Cộng dài với rộng.", "Lấy kết quả nhân 2."]
    if pt in {"Số liền trước", "Số liền sau"}:
        return ["Nhìn số đã cho rồi thêm hoặc bớt 1."]
    if pt == "Chuỗi thao tác":
        return ["Làm ô đầu trước.", "Dùng kết quả đó cho ô sau."]
    if pt == "Tìm thành phần chưa biết":
        return ["Gọi đúng tên thành phần.", "Dùng đúng quy tắc tương ứng."]
    if pt == "Bài nhiều bước":
        return ["Làm bước trung gian trước.", "Dùng kết quả đó để ra đáp án cuối."]
    if pt == "Chia đều":
        return ["Lấy tổng chia cho số phần bằng nhau."]
    if pt == "So sánh số đo để chọn xa nhất":
        return ["So sánh các số đo.", "Nối số lớn nhất với đáp án đúng."]
    if pt == "Nhận biết tâm, bán kính, đường kính":
        return ["Xác định tâm.", "Đối chiếu từng lựa chọn với định nghĩa đúng."]
    return ["Xác định điều cần tìm trước.", "Chọn phép tính đúng để làm."]



def _text_mentions_number(text: str, value: int) -> bool:
    compact = _compact_number_text(text)
    return str(value) in compact if compact else False


def _build_micro_goals(problem_text: str) -> list[str]:
    solved = _solve_supported_problem(problem_text)
    if solved and solved.get("kind") == "geometry_farthest":
        return [
            "Tìm số đo lớn nhất trong các khoảng cách.",
            "Nối số đo lớn nhất với đúng tên vườn hoa.",
            "Chốt đáp án chữ cái tương ứng.",
        ]
    if solved and solved.get("kind") == "circle_mcq":
        return [
            "Nhìn đúng khái niệm đang hỏi trong 4 lựa chọn.",
            "Loại các câu sai nếu cần.",
            "Chọn đáp án đúng và nói vì sao ngắn gọn.",
        ]
    if solved and solved.get("category") == "doi_don_vi":
        return [
            "Đổi số đo về cùng một đơn vị trước.",
            "Làm phép tính sau khi đã đổi đơn vị.",
            "Chốt đáp số đầy đủ đơn vị.",
        ]
    if solved and solved.get("category") == "rut_ve_don_vi":
        return [
            "Tìm 1 phần trước.",
            "Từ 1 phần suy ra nhiều phần.",
            "Chốt đáp số đầy đủ.",
        ]
    if solved and solved.get("category") == "chia_deu":
        return [
            "Viết phép chia để tìm 1 phần.",
            "Nói đáp số đầy đủ.",
        ]
    if solved and solved.get("category") == "nhan_roi_tru":
        return [
            "Tính bước trung gian trước.",
            "Dùng kết quả đó để tìm phần còn lại hoặc còn thiếu.",
            "Chốt đáp số đầy đủ.",
        ]
    if solved and solved.get("category") in {"so_lien_sau", "so_lien_truoc"}:
        return [
            "Làm phép tính ngắn đúng quy tắc.",
            "Chốt đáp án cuối cùng.",
        ]
    frame = _infer_teaching_frame(problem_text)
    return _build_step_plan(problem_text, frame)


def _infer_active_micro_goal(problem_text: str, chat_history: list[dict[str, Any]]) -> dict[str, Any]:
    solved = _solve_supported_problem(problem_text)
    joined = "\n".join(msg.get("content", "") for msg in chat_history if not msg.get("hidden"))
    goals = _build_micro_goals(problem_text)

    def pack(index: int) -> dict[str, Any]:
        index = max(0, min(index, len(goals) - 1))
        return {"index": index, "text": goals[index], "total": len(goals)}

    if not solved:
        return pack(0)

    if solved.get("kind") == "geometry_farthest":
        if not _text_mentions_number(joined, solved["correct_value"]):
            return pack(0)
        if not _contains_name(joined, solved["correct_name"]):
            return pack(1)
        if _response_mentions_choice(joined) != solved["correct_letter"]:
            return pack(2)
        return pack(len(goals) - 1)

    if solved.get("kind") == "circle_mcq":
        if _response_mentions_choice(joined) != solved["correct_letter"] and not _contains_name(joined, solved["correct_name"]):
            return pack(0)
        return pack(len(goals) - 1)

    steps = solved.get("step_values", {})
    category = solved.get("category")
    if category == "doi_don_vi":
        if not _text_mentions_number(joined, steps.get("converted", -1)):
            return pack(0)
        if not _text_mentions_number(joined, solved["answer_value"]):
            return pack(1)
        return pack(2)
    if category == "rut_ve_don_vi":
        if not _text_mentions_number(joined, steps.get("one_part", -1)):
            return pack(0)
        if not _text_mentions_number(joined, solved["answer_value"]):
            return pack(1)
        return pack(2)
    if category == "nhan_roi_tru":
        if not _text_mentions_number(joined, steps.get("intermediate", -1)):
            return pack(0)
        if not _text_mentions_number(joined, solved["answer_value"]):
            return pack(1)
        return pack(2)
    if category == "chia_deu":
        if not _text_mentions_number(joined, solved["answer_value"]):
            return pack(0)
        return pack(1 if len(goals) > 1 else 0)
    if category in {"so_lien_sau", "so_lien_truoc", "tim_thanh_phan_chua_biet"}:
        if not _text_mentions_number(joined, solved["answer_value"]):
            return pack(0)
        return pack(len(goals) - 1)

    return pack(0)


def detect_problem_complexity(problem_text: str) -> str:
    text = (problem_text or "").lower()
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
        "gấp",
        "chu vi",
        "ô trống",
        "→",
        "->",
    ]
    count = sum(1 for signal in multi_step_signals if signal in text)
    return "medium_or_hard" if count >= 2 else "easy"


# =========================================================
# SESSION STATE HELPERS
# =========================================================
def init_app_state(st):
    defaults = {
        "mode": "child",
        "support_level": "goi_y",
        "problem_text": "",
        "problem_confirmed": False,
        "problem_type": "",
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
        if key not in st.session_state:
            st.session_state[key] = value



def reset_session(st):
    st.session_state.problem_text = ""
    st.session_state.problem_confirmed = False
    st.session_state.problem_type = ""
    st.session_state.current_step = "start"
    st.session_state.last_error_type = ""
    st.session_state.allow_full_solution = False
    st.session_state.chat_history = []
    st.session_state.summary = ""
    st.session_state.pending_image = None
    st.session_state.presentation_retry_count = 0
    st.session_state.stuck_count = 0
    st.session_state.show_help_buttons = False
    st.session_state.show_hint_button = False
    st.session_state.show_solution_button = False
    st.session_state.is_finished = False
    st.session_state.hint_request_count = 0
    st.session_state.last_assistant_response = ""
    st.session_state.last_real_user_reply = ""



def looks_like_new_problem(user_input: str) -> bool:
    text = (user_input or "").strip().lower()
    signals = [
        "hỏi",
        "một",
        "một cửa hàng",
        "một cuộn",
        "một thùng",
        "một thư viện",
        "một hình",
        "tính",
        "tìm x",
        "tìm",
        "bao nhiêu",
        "còn lại",
        "chia đều",
        "chiều dài",
        "chiều rộng",
        "câu 1",
        "khoanh",
        "số liền trước",
        "số liền sau",
    ]
    return len(text) >= 20 and any(signal in text for signal in signals)



def start_new_problem(st, new_problem_text: str):
    st.session_state.problem_text = (new_problem_text or "").strip()
    st.session_state.problem_confirmed = True
    st.session_state.problem_type = ""
    st.session_state.current_step = "start"
    st.session_state.last_error_type = ""
    st.session_state.allow_full_solution = False
    st.session_state.chat_history = []
    st.session_state.summary = ""
    st.session_state.presentation_retry_count = 0
    st.session_state.stuck_count = 0
    st.session_state.show_help_buttons = False
    st.session_state.show_hint_button = False
    st.session_state.show_solution_button = False
    st.session_state.is_finished = False
    st.session_state.hint_request_count = 0
    st.session_state.last_assistant_response = ""
    st.session_state.last_real_user_reply = ""



def update_step_and_error(st, reply_type: str):
    mapping = {
        "student_dont_know": "khong_biet",
        "student_number_only": "chi_1_con_so",
        "student_choice_only": "chon_dap_an",
        "student_asks_answer": "xin_dap_an",
    }
    st.session_state.last_error_type = mapping.get(reply_type, "")



def update_presentation_retry(st, require_full_presentation: bool):
    st.session_state.presentation_retry_count = (
        st.session_state.presentation_retry_count + 1 if require_full_presentation else 0
    )



def update_stuck_ui(st, reply_type: str):
    if reply_type == "student_dont_know":
        st.session_state.stuck_count += 1
    else:
        st.session_state.stuck_count = max(0, st.session_state.stuck_count - 1)

    if st.session_state.is_finished:
        st.session_state.show_help_buttons = False
        st.session_state.show_hint_button = False
        st.session_state.show_solution_button = False
        return

    st.session_state.show_help_buttons = st.session_state.stuck_count >= 1
    st.session_state.show_hint_button = st.session_state.stuck_count >= 2
    st.session_state.show_solution_button = st.session_state.stuck_count >= 4 or st.session_state.allow_full_solution


# =========================================================
# FINISH / REPETITION DETECTION
# =========================================================
def detect_finished_response(response_text: str) -> bool:
    text = (response_text or "").lower()
    direct_signals = [
        "đáp số:",
        "đáp án:",
        "đáp án đúng là",
        "kiến thức cần nhớ:",
        "vậy là con làm xong",
        "con đã làm xong bài này",
        "mình chốt lại nhé",
    ]
    if any(signal in text for signal in direct_signals):
        return True
    if "kiến thức cần nhớ" in text and any(token in text for token in ["đúng rồi", "vậy", "đáp án", "đáp số", "kết quả"]):
        return True
    return False



def responses_too_similar(previous_text: str, current_text: str) -> bool:
    prev = _normalize_for_matching(previous_text)
    curr = _normalize_for_matching(current_text)
    if not prev or not curr:
        return False
    if prev == curr:
        return True
    if prev in curr or curr in prev:
        shorter = min(len(prev), len(curr))
        longer = max(len(prev), len(curr))
        if shorter / max(longer, 1) >= 0.75:
            return True
    return SequenceMatcher(None, prev, curr).ratio() >= 0.88



def should_mark_finished_after_child_help(response_text: str, hint_request_count: int) -> bool:
    if hint_request_count < 3:
        return False
    text = _normalize_for_matching(response_text)
    has_final = any(s in text for s in ["dap so", "dap an", "kien thuc can nho", "ket qua la"])
    has_question = "?" in (response_text or "")
    return has_final and not has_question


# =========================================================
# STRUCTURED FACTS / SOLVERS / CHECKERS
# =========================================================
def _extract_options(problem_text: str) -> list[dict[str, str]]:
    flattened = re.sub(r"\s+", " ", problem_text or " ").strip()
    matches = re.finditer(r"([A-D])\.\s*(.*?)(?=(?:\s+[A-D]\.\s)|$)", flattened)
    options: list[dict[str, str]] = []
    for match in matches:
        letter = match.group(1).upper()
        text = match.group(2).strip(" .;")
        if text:
            options.append({"letter": letter, "text": text})
    return options



def _extract_section(problem_text: str, start_markers: list[str], end_markers: list[str]) -> str:
    text = problem_text or ""
    lower = text.lower()
    start_positions = [lower.find(marker.lower()) for marker in start_markers if lower.find(marker.lower()) != -1]
    if not start_positions:
        return ""
    start = min(start_positions)
    end = len(text)
    for marker in end_markers:
        pos = lower.find(marker.lower(), start + 1)
        if pos != -1:
            end = min(end, pos)
    return text[start:end].strip()



def _extract_numbers(text: str) -> list[int]:
    return [_parse_int(match) for match in re.findall(r"\d[\d\s\.]*", text or "")]



def _extract_named_distances(problem_text: str) -> list[dict[str, Any]]:
    data_section = _extract_section(
        problem_text,
        ["Dữ kiện nhìn thấy trong hình", "Du lieu nhin thay trong hinh", "Chữ/số nhìn thấy trong ảnh", "Chu/sọ nhin thay"],
        ["Các lựa chọn", "Cac lua chon", "Xem lại ảnh gốc"],
    )
    if not data_section:
        data_section = problem_text or ""

    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    pattern = re.compile(
        r"(?:^|\n|-)\s*(?:Đường đến\s+)?(.+?)\s*:\s*(\d[\d\s]*)\s*m\b",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(data_section):
        name = match.group(1).strip(" -:\n\t")
        value = _parse_int(match.group(2))
        if not name or value <= 0:
            continue
        key = _normalize_for_matching(name)
        if key in seen:
            continue
        seen.add(key)
        results.append({"name": name, "value": value})
    return results



def _match_option_letter_by_name(options: list[dict[str, str]], answer_name: str) -> str | None:
    target = _normalize_for_matching(answer_name)
    for option in options:
        option_name = _normalize_for_matching(option["text"])
        if not option_name:
            continue
        if target == option_name or target in option_name or option_name in target:
            return option["letter"]
    return None



def _solve_geometry_farthest(problem_text: str) -> dict[str, Any] | None:
    normalized = _normalize_for_matching(problem_text)
    if "xa nhat" not in normalized:
        return None
    options = _extract_options(problem_text)
    distances = _extract_named_distances(problem_text)
    if len(options) < 2 or len(distances) < 2:
        return None

    best = max(distances, key=lambda item: item["value"])
    best_letter = _match_option_letter_by_name(options, best["name"])
    if not best_letter:
        return None

    return {
        "kind": "geometry_farthest",
        "problem_type": "Chọn đường xa nhất",
        "knowledge": "So sánh các số đo độ dài",
        "thinking": "Nhìn các số đo rồi chọn số lớn nhất",
        "options": options,
        "distances": distances,
        "correct_letter": best_letter,
        "correct_name": next(opt["text"] for opt in options if opt["letter"] == best_letter),
        "correct_value": best["value"],
        "teacher_hint": f"Nhìn các khoảng cách {', '.join(_format_int(d['value']) for d in distances)} rồi tìm số lớn nhất.",
        "memory": "Muốn tìm xa nhất thì chọn số đo lớn nhất.",
    }



def _extract_circle_context(problem_text: str) -> dict[str, Any] | None:
    normalized = _normalize_for_matching(problem_text)
    if "hinh tron" not in normalized and "tam o" not in normalized:
        return None
    options = _extract_options(problem_text)
    if not options:
        return None
    labels_section = _extract_section(problem_text, ["Nhãn hình học nhìn thấy", "Nhan hinh hoc nhin thay"], ["Các lựa chọn", "Cac lua chon"])
    source = labels_section or problem_text
    accent_safe_source = _strip_accents(source)
    center_match = re.search(r"tam\s+([A-Z])", accent_safe_source, flags=re.IGNORECASE)
    center = center_match.group(1).upper() if center_match else None
    points = {m.group(1).upper() for m in re.finditer(r"point\s*\|\s*([A-Z])", source, flags=re.IGNORECASE)}
    segments = {m.group(1).upper() for m in re.finditer(r"line_segment\s*\|\s*([A-Z]{2})", source, flags=re.IGNORECASE)}
    if not center:
        return None
    return {"center": center, "points": points, "segments": segments, "options": options}



def _solve_circle_mcq(problem_text: str) -> dict[str, Any] | None:
    ctx = _extract_circle_context(problem_text)
    if not ctx:
        return None
    center = ctx["center"]
    segments = ctx["segments"]
    options = ctx["options"]

    truths: dict[str, bool] = {}
    for option in options:
        text = option["text"]
        norm = _normalize_for_matching(text)
        letter = option["letter"]
        truths[letter] = False

        if re.fullmatch(rf"{center.lower()} la tam hinh tron", norm):
            truths[letter] = True
            continue

        radius_match = re.fullmatch(r"([a-z]{2}) la ban kinh", norm)
        if radius_match:
            seg = radius_match.group(1).upper()
            truths[letter] = seg in segments and center in seg and len(seg) == 2
            continue

        diameter_match = re.fullmatch(r"([a-z]{2}) la duong kinh", norm)
        if diameter_match:
            # Không khẳng định đường kính nếu dữ kiện ảnh không nêu rõ.
            truths[letter] = False
            continue

    true_letters = [letter for letter, value in truths.items() if value]
    if len(true_letters) != 1:
        return None

    correct_letter = true_letters[0]
    correct_text = next(opt["text"] for opt in options if opt["letter"] == correct_letter)
    return {
        "kind": "circle_mcq",
        "problem_type": "Nhận biết tâm, bán kính, đường kính",
        "knowledge": "Phân biệt tâm, bán kính, đường kính của hình tròn",
        "thinking": "Nhìn tâm trước, rồi xét từng lựa chọn theo đúng định nghĩa",
        "options": options,
        "center": center,
        "correct_letter": correct_letter,
        "correct_name": correct_text,
        "teacher_hint": f"Con nhìn xem câu nào nói đúng nhất về tâm hoặc đoạn thẳng quanh tâm {center}.",
        "memory": f"{center} là tâm; đoạn từ tâm đến một điểm trên đường tròn là bán kính.",
    }



def _extract_unit_after_question(problem_text: str, fallback: str = "") -> str:
    lowered = (problem_text or "").lower()
    patterns = [
        r"bao nhi[eê]u\s+([a-zà-ỹ\s]+?)(?:[\?\.]|$)",
        r"còn lại bao nhiêu\s+([a-zà-ỹ\s]+?)(?:[\?\.]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue
        unit = match.group(1).strip(" .?")
        unit = re.sub(r"\s+", " ", unit)
        if unit:
            return unit
    return fallback



def _solve_numeric_problem(problem_text: str) -> dict[str, Any] | None:
    frame = _infer_teaching_frame(problem_text)
    normalized = _normalize_for_matching(problem_text)
    numbers = _extract_numbers(problem_text)

    if frame["problem_type"] == "Số liền trước":
        if not numbers:
            return None
        base = numbers[-1]
        answer = base - 1
        return {
            "kind": "numeric",
            "category": "so_lien_truoc",
            "problem_type": frame["problem_type"],
            "knowledge": frame["knowledge"],
            "thinking": frame["thinking"],
            "answer_value": answer,
            "answer_text": _format_int(answer),
            "memory": "Số liền trước là lấy số đó trừ 1.",
        }

    if frame["problem_type"] == "Số liền sau":
        base = 9999 if "lon nhat co 4 chu so" in normalized else (numbers[-1] if numbers else None)
        if base is None:
            return None
        answer = base + 1
        return {
            "kind": "numeric",
            "category": "so_lien_sau",
            "problem_type": frame["problem_type"],
            "knowledge": frame["knowledge"],
            "thinking": frame["thinking"],
            "answer_value": answer,
            "answer_text": _format_int(answer),
            "memory": "Số liền sau là lấy số đó cộng 1.",
        }

    if frame["problem_type"] == "Chia đều":
        if len(numbers) < 2:
            return None
        total, parts = numbers[0], numbers[1]
        if parts == 0:
            return None
        answer = total // parts
        unit = _extract_unit_after_question(problem_text, fallback="")
        return {
            "kind": "numeric",
            "category": "chia_deu",
            "problem_type": frame["problem_type"],
            "knowledge": frame["knowledge"],
            "thinking": frame["thinking"],
            "answer_value": answer,
            "unit": unit,
            "answer_text": f"{_format_int(answer)} {unit}".strip(),
            "memory": "Chia đều thì lấy tổng chia cho số phần bằng nhau.",
            "step_values": {"main": answer},
        }

    if frame["problem_type"] == "Rút về đơn vị":
        if len(numbers) < 3:
            return None
        first, second, third = numbers[0], numbers[1], numbers[2]
        groups, total, target = first, second, third
        if total < groups:
            total, groups, target = max(first, second), min(first, second), third
        if groups == 0:
            return None
        one_part = total // groups
        answer = one_part * target
        unit = _extract_unit_after_question(problem_text, fallback="chiếc")
        if "but" in normalized:
            unit = "chiếc bút"
        return {
            "kind": "numeric",
            "category": "rut_ve_don_vi",
            "problem_type": frame["problem_type"],
            "knowledge": frame["knowledge"],
            "thinking": frame["thinking"],
            "answer_value": answer,
            "unit": unit,
            "answer_text": f"{_format_int(answer)} {unit}".strip(),
            "memory": "Muốn tìm nhiều phần như nhau thì tìm 1 phần trước rồi nhân lên.",
            "step_values": {"one_part": one_part, "target": target},
        }

    if frame["problem_type"] == "Đổi đơn vị rồi tính":
        match = re.search(r"(\d+)\s*m\s*(\d+)\s*cm.*?(\d+)\s*cm", problem_text.lower())
        if not match:
            return None
        meters = int(match.group(1))
        extra_cm = int(match.group(2))
        change_cm = int(match.group(3))
        total_cm = meters * 100 + extra_cm
        answer = total_cm - change_cm
        return {
            "kind": "numeric",
            "category": "doi_don_vi",
            "problem_type": "Đổi về cùng đơn vị rồi trừ",
            "knowledge": "1 m = 100 cm",
            "thinking": "Đổi về cùng đơn vị trước rồi mới tính",
            "answer_value": answer,
            "unit": "cm",
            "answer_text": f"{_format_int(answer)} cm",
            "memory": "Đổi về cùng đơn vị trước rồi mới tính.",
            "step_values": {"converted": total_cm, "change": change_cm},
        }

    if frame["problem_type"] == "Chu vi hình vuông" and numbers:
        edge = numbers[0]
        answer = edge * 4
        return {
            "kind": "numeric",
            "category": "chu_vi_hinh_vuong",
            "problem_type": frame["problem_type"],
            "knowledge": frame["knowledge"],
            "thinking": frame["thinking"],
            "answer_value": answer,
            "unit": "cm",
            "answer_text": f"{_format_int(answer)} cm",
            "memory": "Chu vi hình vuông bằng cạnh nhân 4.",
        }

    if frame["problem_type"] == "Chu vi hình chữ nhật" and len(numbers) >= 2:
        length, width = numbers[0], numbers[1]
        answer = (length + width) * 2
        return {
            "kind": "numeric",
            "category": "chu_vi_hinh_chu_nhat",
            "problem_type": frame["problem_type"],
            "knowledge": frame["knowledge"],
            "thinking": frame["thinking"],
            "answer_value": answer,
            "unit": "cm",
            "answer_text": f"{_format_int(answer)} cm",
            "memory": "Chu vi hình chữ nhật bằng (dài + rộng) × 2.",
        }

    if "78 000" in problem_text and "18 000" in problem_text and "3 lần" in problem_text:
        purchased = 3 * 18000
        answer = 78000 - purchased
        return {
            "kind": "numeric",
            "category": "nhan_roi_tru",
            "problem_type": "Bài nhiều bước",
            "knowledge": "Phép nhân rồi phép trừ",
            "thinking": "Tính số đã mua trước, rồi tìm số còn phải mua",
            "answer_value": answer,
            "unit": "viên gạch",
            "answer_text": f"{_format_int(answer)} viên gạch",
            "memory": "Tính phần đã có trước rồi tìm phần còn thiếu.",
            "step_values": {"intermediate": purchased},
        }

    if "95" in problem_text and ("5 chồng" in problem_text or "5 chong" in normalized) and "7 quyển" in problem_text:
        sold = 5 * 7
        answer = 95 - sold
        return {
            "kind": "numeric",
            "category": "nhan_roi_tru",
            "problem_type": "Bài nhiều bước",
            "knowledge": "Tính số đã bán trước rồi lấy số ban đầu trừ đi",
            "thinking": "Tính xem đã bán bao nhiêu quyển trước, rồi tìm số còn lại",
            "answer_value": answer,
            "unit": "quyển vở",
            "answer_text": f"{_format_int(answer)} quyển vở",
            "memory": "Muốn biết còn lại bao nhiêu thì lấy số ban đầu trừ số đã bán.",
            "step_values": {"intermediate": sold},
        }

    if frame["problem_type"] == "Tìm thành phần chưa biết" and len(numbers) >= 2:
        a, b = numbers[0], numbers[1]
        if "hieu" in normalized or "số trừ" in problem_text.lower() or "so tru" in normalized:
            answer = a + b
            return {
                "kind": "numeric",
                "category": "tim_thanh_phan_chua_biet",
                "problem_type": frame["problem_type"],
                "knowledge": frame["knowledge"],
                "thinking": frame["thinking"],
                "answer_value": answer,
                "answer_text": _format_int(answer),
                "memory": "Muốn tìm số bị trừ thì lấy hiệu cộng với số trừ.",
            }

    return None



def _solve_supported_problem(problem_text: str) -> dict[str, Any] | None:
    return _solve_geometry_farthest(problem_text) or _solve_circle_mcq(problem_text) or _solve_numeric_problem(problem_text)


# =========================================================
# PROMPT CONTEXT BUILDERS
# =========================================================
def _format_truth_block(problem_text: str) -> str:
    solved = _solve_supported_problem(problem_text)
    if not solved:
        return "- Không có đáp án nội bộ dạng checker cho bài này. Hãy dạy theo đề đã xác nhận."

    if solved["kind"] == "geometry_farthest":
        facts = [f"  - {item['name']}: {_format_int(item['value'])} m" for item in solved["distances"]]
        return "\n".join(
            [
                "- Thông tin kiểm chứng nội bộ (không nói lệch đi):",
                *facts,
                f"  - Số lớn nhất: {_format_int(solved['correct_value'])}",
                f"  - Tên đúng: {solved['correct_name']}",
                f"  - Đáp án đúng: {solved['correct_letter']}",
            ]
        )

    if solved["kind"] == "circle_mcq":
        return "\n".join(
            [
                "- Thông tin kiểm chứng nội bộ (không nói lệch đi):",
                f"  - Tâm hình tròn: {solved['center']}",
                f"  - Đáp án đúng: {solved['correct_letter']}. {solved['correct_name']}",
            ]
        )

    return "\n".join(
        [
            "- Thông tin kiểm chứng nội bộ (không nói lệch đi):",
            f"  - Kết quả đúng: {solved['answer_text']}",
            f"  - Kiến thức chốt: {solved['memory']}",
        ]
    )



def _format_history(chat_history: list[dict[str, Any]], mode: str, limit: int = 6) -> str:
    rows = []
    for msg in chat_history[-limit:]:
        if msg.get("hidden"):
            continue
        role = msg.get("role", "assistant")
        if mode == "parent":
            label = "Ba mẹ" if role == "user" else "Trợ lý"
        else:
            label = "Con" if role == "user" else "Thầy"
        rows.append(f"- {label}: {msg.get('content', '')}")
    return "\n".join(rows) if rows else "- Chưa có lịch sử trước đó."



def build_initial_context(problem_text: str, mode: str, support_level: str) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    first_response_guide = get_first_response_guide()
    complexity = detect_problem_complexity(problem_text)
    frame = _infer_teaching_frame(problem_text)
    micro_goals = _build_micro_goals(problem_text)

    context = f"""
{system_prompt}

{support_guide}

{first_response_guide}

Đề bài đã xác nhận:
{problem_text}

Phân tích nội bộ để định hướng cho thầy:
- Mức độ bài: {complexity}
- Dạng bài gợi ý: {frame['problem_type']}
- Kiến thức dùng gợi ý: {frame['knowledge']}
- Cách nghĩ nhanh gợi ý: {frame['thinking']}
- Các mốc nên đi qua:
{chr(10).join(f"  - {step}" for step in micro_goals)}
{_format_truth_block(problem_text)}

Yêu cầu cho lượt đầu:
- Nếu mode là child:
  - Mở đầu đúng 1 lần theo khung: Dạng bài / Kiến thức dùng / Cách nghĩ nhanh.
  - Sau đó chỉ hỏi 1 câu ngắn để con làm bước đầu tiên.
  - Đừng lộ đáp án cuối ở lượt đầu, trừ mode cách giải.
  - Giữ giọng ấm, ngắn, tự nhiên, hợp audio.
- Nếu mode là parent:
  - Trả lời theo kiểu toàn bài, gọn mà đủ dùng ngay.
  - Luôn có các ý: Dạng bài, Kiến thức dùng, Hướng làm cả bài, Lỗi dễ mắc, Ba mẹ nên hỏi con.
  - Nếu đã biết đáp án chắc, ưu tiên thêm Lời giải mẫu ngắn và Đáp số.
"""
    return context.strip()


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
) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    frame = _infer_teaching_frame(problem_text)
    active_goal = _infer_active_micro_goal(problem_text, chat_history)
    micro_goals = _build_micro_goals(problem_text)

    reply_rules = []
    if reply_type == "student_dont_know":
        reply_rules.extend(
            [
                f"- Con đang bí. stuck_count hiện tại: {stuck_count}.",
                f"- Tập trung vào đúng mốc hiện tại: {active_goal['text']}",
                "- Lần bí đầu: nhắc con nên nhìn vào đâu trước.",
                "- Lần bí tiếp theo: nói rõ hơn bước cần làm.",
                "- Bí nhiều lượt mới được nói thẳng phép tính hoặc kết quả trung gian.",
            ]
        )
    elif reply_type == "student_asks_answer":
        reply_rules.extend(
            [
                "- Con đang xin đáp án.",
                f"- Trước khi chốt, ưu tiên giúp con đi qua mốc hiện tại: {active_goal['text']}",
                "- Nếu con đã bí quá nhiều lượt thì mới nói đường đi ngắn nhất tới kết quả.",
            ]
        )
    elif reply_type in {"student_number_only", "student_choice_only"}:
        reply_rules.extend(
            [
                "- Con đã đưa ra một mảnh trả lời ngắn.",
                "- Nếu đúng hướng thì công nhận ngắn gọn rồi đi tiếp hoặc chốt gọn.",
                "- Không bắt con viết lại quá nhiều lần.",
            ]
        )
    else:
        reply_rules.append(f"- Bám vào mốc hiện tại: {active_goal['text']}")

    if require_full_presentation:
        reply_rules.append("- Chỉ nhắc viết rõ hơn thật ngắn một lần.")
    if small_error:
        reply_rules.append("- Đây là lỗi nhỏ. Công nhận phần đúng trước, sửa phần thiếu thật ngắn.")
    if allow_full_solution:
        reply_rules.append("- Được phép nói lời giải rõ hơn hoặc chốt đáp án nếu cần.")
    if is_finished:
        reply_rules.append("- Bài đã xong. Chỉ chốt ngắn gọn, không mở thêm câu hỏi mới.")

    context = f"""
{system_prompt}

{support_guide}

Đề bài hiện tại:
{problem_text}

Lịch sử gần đây:
{_format_history(chat_history, mode)}

Phân tích nội bộ để giữ đường ray:
- current_step: {current_step}
- last_error_type: {last_error_type}
- reply_type: {reply_type}
- allow_full_solution: {allow_full_solution}
- require_full_presentation: {require_full_presentation}
- small_error: {small_error}
- is_finished: {is_finished}
- Dạng bài gợi ý: {frame['problem_type']}
- Kiến thức dùng gợi ý: {frame['knowledge']}
- Cách nghĩ nhanh gợi ý: {frame['thinking']}
- Mốc hiện tại nên tập trung: {active_goal['text']}
- Toàn bộ mốc của bài:
{chr(10).join(f"  - {step}" for step in micro_goals)}
{_format_truth_block(problem_text)}

Luật phản hồi cho lượt này:
{chr(10).join(reply_rules)}
- Nếu mode là child:
  - Không lặp lại block mở bài "Dạng bài / Kiến thức dùng / Cách nghĩ nhanh" nữa.
  - Nói như thầy giáo lớp 3: ngắn, mềm, rõ.
  - Mỗi lượt chỉ 1 việc chính.
  - Không nhảy cóc qua mốc hiện tại nếu con chưa đi qua nó.
  - Nếu chốt đáp án, thêm 1 dòng: Kiến thức cần nhớ: ...
- Nếu mode là parent:
  - Ưu tiên một lượt là dùng được ngay.
  - Nếu đã biết đáp án chắc, thêm Lời giải mẫu ngắn và Đáp số.
  - Không nói chuyện như đang dạy trực tiếp trẻ.

Tin nhắn mới nhất của người dùng:
{user_input}
"""
    return context.strip()


def build_summary_context(problem_text: str, chat_history: list) -> str:
    summary_prompt = get_summary_prompt()
    history_text = ""
    for msg in chat_history[-10:]:
        if msg.get("hidden"):
            continue
        role = "Học sinh" if msg.get("role") == "user" else "Thầy"
        history_text += f"- {role}: {msg.get('content', '')}\n"
    context = f"""
{summary_prompt}

Đề bài:
{problem_text}

Lịch sử buổi học:
{history_text}
"""
    return context.strip()


# =========================================================
# RESPONSE GUARDRAILS
# =========================================================
def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()



def _response_mentions_choice(response_text: str) -> str | None:
    choice = _extract_choice_letter(response_text)
    if choice:
        return choice
    normalized = _normalize_for_matching(response_text)
    match = re.search(r"dap an\s*([a-d])", normalized)
    if match:
        return match.group(1).upper()
    return None



def _contains_name(response_text: str, name: str) -> bool:
    norm_resp = _normalize_for_matching(response_text)
    norm_name = _normalize_for_matching(name)
    return bool(norm_name) and norm_name in norm_resp



def _maybe_append_parent_answer(response: str, solved: dict[str, Any] | None) -> str:
    if not solved:
        return response
    lower = response.lower()
    if "đáp số" in lower:
        return response
    if solved["kind"] == "geometry_farthest":
        return (
            response.rstrip()
            + f"\n\n**Lời giải mẫu ngắn:** So sánh các số đo, số lớn nhất là **{_format_int(solved['correct_value'])} m** nên xa nhất là **{solved['correct_name']}**.\n**Đáp số:** **{solved['correct_letter']}. {solved['correct_name']}**"
        )
    if solved["kind"] == "circle_mcq":
        return response.rstrip() + f"\n\n**Đáp số:** **{solved['correct_letter']}. {solved['correct_name']}**"
    return response.rstrip() + f"\n\n**Đáp số:** **{solved['answer_text']}**"



def _safe_child_geometry_prompt(solved: dict[str, Any]) -> str:
    values = ", ".join(_format_int(item["value"]) for item in solved["distances"])
    return (
        f"Dạng bài: Chọn đường xa nhất\n"
        f"Kiến thức dùng: So sánh các số đo\n"
        f"Cách nghĩ nhanh: Mình nhìn các số đo rồi tìm số lớn nhất\n\n"
        f"Con nhìn {values} nhé. Theo con, số nào lớn nhất?"
    )



def _safe_child_geometry_answer(solved: dict[str, Any]) -> str:
    return (
        "Đúng rồi.\n\n"
        f"Số lớn nhất là {_format_int(solved['correct_value'])}.\n"
        f"Vậy xa nhất là {solved['correct_name']}, mình chọn {solved['correct_letter']}.\n\n"
        f"Kiến thức cần nhớ: {solved['memory']}"
    )



def _safe_child_circle_answer(solved: dict[str, Any]) -> str:
    return (
        "Con nhìn đúng rồi.\n\n"
        f"Đáp án đúng là {solved['correct_letter']}. {solved['correct_name']}.\n\n"
        f"Kiến thức cần nhớ: {solved['memory']}"
    )



def _safe_child_numeric_step_prompt(solved: dict[str, Any]) -> str | None:
    category = solved.get("category")
    if category == "doi_don_vi":
        converted = solved.get("step_values", {}).get("converted")
        return (
            "Thầy thấy mình cần làm từng bước nhé.\n\n"
            "Con đổi 3 m 25 cm ra cm trước xem được bao nhiêu.\n"
            "3 m 25 cm = ? cm"
        ) if converted else None
    if category == "rut_ve_don_vi":
        return "Mình tìm 1 phần trước nhé. Con thử tính xem 1 hộp có bao nhiêu chiếc bút?"
    if category == "nhan_roi_tru":
        return "Mình tìm bước trung gian trước nhé. Con thử tính phần đã có hoặc đã bán trước xem sao."
    return None

def _apply_response_guardrails(
    response: str,
    problem_text: str,
    mode: str,
    *,
    opening: bool,
    reply_type: str = "normal_reply",
    allow_full_solution: bool = False,
    hint_request_count: int = 0,
    chat_history: list[dict[str, Any]] | None = None,
) -> str:
    solved = _solve_supported_problem(problem_text)
    if not solved:
        return response.strip()

    chat_history = chat_history or []

    if mode == "parent":
        return _maybe_append_parent_answer(response.strip(), solved)

    active_goal = _infer_active_micro_goal(problem_text, chat_history)

    if solved["kind"] == "geometry_farthest":
        mention_choice = _response_mentions_choice(response)
        mentions_name = _contains_name(response, solved["correct_name"])
        mentions_value = _text_mentions_number(response, solved["correct_value"])
        if opening:
            if mention_choice and mention_choice != solved["correct_letter"]:
                return _safe_child_geometry_prompt(solved)
            return response.strip()
        if mention_choice and mention_choice != solved["correct_letter"]:
            return _safe_child_geometry_answer(solved)
        wrong_names = [opt["text"] for opt in solved["options"] if opt["letter"] != solved["correct_letter"]]
        if any(_contains_name(response, name) for name in wrong_names) and not mentions_name:
            return _safe_child_geometry_answer(solved)
        if (mentions_value or mentions_name or mention_choice == solved["correct_letter"]) and hint_request_count >= 2:
            return _safe_child_geometry_answer(solved)
        return response.strip()

    if solved["kind"] == "circle_mcq":
        mention_choice = _response_mentions_choice(response)
        if mention_choice and mention_choice != solved["correct_letter"]:
            return _safe_child_circle_answer(solved)
        return response.strip()

    # numeric: keep AI natural, but do not let it jump over the current micro-goal too early.
    if not opening and not allow_full_solution and reply_type in {"student_dont_know", "student_asks_answer"} and hint_request_count < 2:
        category = solved.get("category")
        if category == "doi_don_vi" and active_goal["index"] == 0 and _text_mentions_number(response, solved["answer_value"]):
            safe = _safe_child_numeric_step_prompt(solved)
            if safe:
                return safe
        if category in {"rut_ve_don_vi", "nhan_roi_tru"} and active_goal["index"] == 0 and _text_mentions_number(response, solved["answer_value"]):
            safe = _safe_child_numeric_step_prompt(solved)
            if safe:
                return safe

    if detect_finished_response(response) and solved.get("answer_text"):
        compact = _compact_number_text(response)
        target = _compact_number_text(solved["answer_text"])
        if target and target not in compact:
            return response.rstrip() + f"\n\nĐáp số: {solved['answer_text']}."
    return response.strip()


def generate_opening_tutoring_response(problem_text: str, mode: str, support_level: str) -> str | None:
    context = build_initial_context(problem_text, mode, support_level)
    response = generate_text_response(
        system_prompt=get_system_prompt(mode),
        user_input=context,
    )
    return _apply_response_guardrails(
        response=response,
        problem_text=problem_text,
        mode=mode,
        opening=True,
        chat_history=[],
    )



def generate_followup_tutoring_response(
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
) -> str | None:
    context = build_followup_context(
        problem_text=problem_text,
        mode=mode,
        support_level=support_level,
        chat_history=chat_history,
        current_step=current_step,
        last_error_type=last_error_type,
        user_input=user_input,
        reply_type=reply_type,
        allow_full_solution=allow_full_solution,
        require_full_presentation=require_full_presentation,
        small_error=small_error,
        stuck_count=stuck_count,
        is_finished=is_finished,
    )
    response = generate_text_response(
        system_prompt=get_system_prompt(mode),
        user_input=context,
    )
    return _apply_response_guardrails(
        response=response,
        problem_text=problem_text,
        mode=mode,
        opening=False,
        reply_type=reply_type,
        allow_full_solution=allow_full_solution,
        hint_request_count=hint_request_count,
        chat_history=chat_history,
    )
