# logic.py

import re
import unicodedata

from prompts import (
    get_system_prompt,
    get_support_guide,
    get_summary_prompt,
    get_first_response_guide,
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _normalize_for_matching(text: str) -> str:
    text = _strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _infer_teaching_frame(problem_text: str) -> dict:
    raw = problem_text.lower()
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

    if (
        ("hop" in text or "thung" in text or "goi" in text)
        and "tat ca" in text
        and ("nhu nhau" in text or "moi" in text)
    ):
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

    if (
        (" m " in f" {text} " and " cm" in raw)
        or (" kg" in raw and " g" in raw)
        or ("met" in text and "xang ti met" in text)
    ):
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

    if "gap" in text and ("roi" in text or "sau do" in text or "tang" in text or "bot" in text or "tang ban" in text):
        return {
            "problem_type": "Bài nhiều bước",
            "knowledge": "Phép nhân rồi cộng hoặc trừ",
            "thinking": "Tính phần gấp lên trước, rồi làm bước tiếp theo",
        }

    if "gap" in text:
        return {
            "problem_type": "Gấp lên nhiều lần",
            "knowledge": "Phép nhân",
            "thinking": "Lấy số đã cho nhân với số lần",
        }

    if (
        ("moi lan" in text or "moi chong" in text or "3 lan" in text or "2 lan" in text or "4 lan" in text)
        and ("ban" in text or "con lai" in text or "con phai" in text or "sau khi" in text)
    ):
        return {
            "problem_type": "Bài nhiều bước",
            "knowledge": "Phép nhân rồi phép trừ",
            "thinking": "Tính phần đã có hoặc đã bán trước, rồi tìm phần còn lại",
        }

    if "mot so" in text and "tim so do" in text and "tru" in text:
        return {
            "problem_type": "Tìm thành phần chưa biết",
            "knowledge": "Tìm số bị trừ khi biết hiệu và số trừ",
            "thinking": "Muốn tìm số bị trừ thì lấy hiệu cộng số trừ",
        }

    if "mot so" in text and "tim so do" in text and "chia" in text:
        return {
            "problem_type": "Tìm thành phần chưa biết",
            "knowledge": "Tìm số bị chia khi biết thương và số chia",
            "thinking": "Muốn tìm số bị chia thì lấy thương nhân số chia",
        }

    return {
        "problem_type": "Bài toán có lời văn",
        "knowledge": "Đọc kỹ đề để chọn phép tính phù hợp",
        "thinking": "Xem bài đang hỏi gì rồi tìm bước cần làm trước",
    }


def _build_step_plan(problem_text: str, frame: dict) -> list[str]:
    text = _normalize_for_matching(problem_text)
    pt = frame["problem_type"]
    knowledge = frame["knowledge"]

    if pt == "Rút về đơn vị":
        return [
            "Bước 1: tìm 1 phần trước.",
            "Bước 2: từ 1 phần tính nhiều phần.",
        ]

    if pt == "Đổi đơn vị rồi tính":
        return [
            "Bước 1: đổi các số đo về cùng một đơn vị.",
            "Bước 2: làm phép tính theo đề bài.",
        ]

    if pt == "Chu vi hình vuông":
        return [
            "Bước 1: lấy cạnh nhân 4 để ra chu vi.",
        ]

    if pt == "Chu vi hình chữ nhật":
        return [
            "Bước 1: cộng chiều dài với chiều rộng.",
            "Bước 2: lấy kết quả nhân 2.",
        ]

    if pt == "Số liền trước":
        return [
            "Bước 1: lấy số đã cho trừ 1.",
        ]

    if pt == "Số liền sau":
        return [
            "Bước 1: lấy số đã cho cộng 1.",
        ]

    if pt == "Chuỗi thao tác":
        return [
            "Bước 1: tính ô đầu tiên.",
            "Bước 2: dùng kết quả đó để tính ô tiếp theo.",
        ]

    if pt == "Tìm thành phần chưa biết":
        return [
            "Bước 1: dùng đúng quy tắc tìm thành phần chưa biết.",
        ]

    if pt == "Bài nhiều bước":
        if "tru" in _normalize_for_matching(knowledge):
            return [
                "Bước 1: tính phần đã có hoặc đã bán trước.",
                "Bước 2: tính phần còn lại hoặc còn thiếu.",
            ]
        return [
            "Bước 1: làm bước trung gian trước.",
            "Bước 2: dùng kết quả đó làm bước tiếp theo.",
        ]

    if pt == "Chia đều":
        return [
            "Bước 1: lấy tổng chia cho số phần bằng nhau.",
        ]

    if pt == "Gấp lên nhiều lần":
        return [
            "Bước 1: lấy số đã cho nhân với số lần.",
        ]

    return [
        "Bước 1: xác định điều cần tìm trước.",
        "Bước 2: chọn phép tính đúng để làm.",
    ]


def _infer_current_step_hint(problem_text: str, chat_history: list) -> str:
    frame = _infer_teaching_frame(problem_text)
    plan = _build_step_plan(problem_text, frame)
    history_text = _normalize_for_matching(" ".join(msg["content"] for msg in chat_history[-10:]))

    if frame["problem_type"] == "Rút về đơn vị":
        if any(s in history_text for s in ["1 hop co", "moi hop co", "48 chia 6", "48 6 bang 8", "bang 8"]):
            return "Hiện tại đang ở bước 2: từ 1 phần tính nhiều phần."
        return "Hiện tại đang ở bước 1: tìm 1 phần trước."

    if frame["problem_type"] == "Đổi đơn vị rồi tính":
        if any(s in history_text for s in ["325 cm", "bang 325", "doi xong", "cung don vi"]):
            return "Hiện tại đang ở bước 2: làm phép tính sau khi đã đổi đơn vị."
        return "Hiện tại đang ở bước 1: đổi về cùng một đơn vị trước."

    if frame["problem_type"] == "Bài nhiều bước":
        if any(s in history_text for s in ["35 quy", "54 000", "54000", "da mua", "da ban"]):
            return "Hiện tại đang ở bước 2: dùng kết quả trung gian để tìm phần còn lại hoặc còn thiếu."
        return "Hiện tại đang ở bước 1: làm bước trung gian trước."

    return f"Hiện tại đang ở {plan[0].lower()}"


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


def looks_like_new_problem(user_input: str) -> bool:
    text = user_input.strip().lower()

    signals = [
        "hỏi", "một", "một cửa hàng", "một cuộn", "một thùng",
        "một thư viện", "một hình", "tính", "tìm x", "tìm",
        "bao nhiêu", "còn lại", "chia đều", "chiều dài", "chiều rộng",
        "câu 1", "khoanh", "số liền trước", "số liền sau"
    ]

    long_enough = len(text) >= 20
    has_signal = any(s in text for s in signals)

    return long_enough and has_signal


def start_new_problem(st, new_problem_text: str):
    st.session_state.problem_text = new_problem_text.strip()
    st.session_state.problem_confirmed = True
    st.session_state.problem_type = ""
    st.session_state.current_step = "start"
    st.session_state.last_error_type = ""
    st.session_state.chat_history = []
    st.session_state.summary = ""
    st.session_state.presentation_retry_count = 0
    st.session_state.stuck_count = 0
    st.session_state.show_help_buttons = False
    st.session_state.show_hint_button = False
    st.session_state.show_solution_button = False
    st.session_state.is_finished = False


def detect_problem_complexity(problem_text: str) -> str:
    text = problem_text.lower()

    multi_step_signals = [
        "mỗi lần", "lần", "sau đó", "rồi", "còn phải", "còn lại",
        "đổi đơn vị", " cm", " kg", " g", "1/2", "1/3", "1/4", "1/5",
        "gấp", "chu vi", "ô trống", "→", "->"
    ]

    count = sum(1 for s in multi_step_signals if s in text)

    if count >= 2:
        return "medium_or_hard"
    return "easy"


def build_initial_context(problem_text: str, mode: str, support_level: str) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    first_response_guide = get_first_response_guide()
    complexity = detect_problem_complexity(problem_text)
    frame = _infer_teaching_frame(problem_text)
    step_plan = _build_step_plan(problem_text, frame)

    context = f"""
{system_prompt}

{support_guide}

{first_response_guide}

Đề bài đã xác nhận:
{problem_text}

Mức độ bài:
{complexity}

Khung tư duy gợi ý cho bài này:
- Dạng bài phù hợp: {frame["problem_type"]}
- Kiến thức dùng phù hợp: {frame["knowledge"]}
- Cách nghĩ nhanh: {frame["thinking"]}

Kế hoạch bước giải gợi ý:
{chr(10).join(f"- {step}" for step in step_plan)}

Yêu cầu rất quan trọng:
- Đây là phản hồi đầu tiên sau khi đã có đề bài.
- Nếu mode là child:
  - Ưu tiên mở đầu gọn, vào thẳng ý chính.
  - Có thể bỏ hoàn toàn câu chào nếu đã có khung tư duy rõ.
  - Ưu tiên cấu trúc:
    - Dạng bài: ...
    - Kiến thức dùng: ...
    - Cách nghĩ nhanh: ...
    - rồi kết thúc bằng đúng 1 câu hỏi để con làm bước đầu tiên
  - tối đa 4 dòng ngắn + 1 câu hỏi
  - không viết thêm các câu xã giao như:
    - "Chào con"
    - "Thầy trò mình cùng xem nhé"
    - "Đây là dạng bài rất hay gặp"
- Nếu mode là parent:
  - luôn ưu tiên trả lời theo kiểu TOÀN BÀI
  - phải nêu rõ:
    - Dạng bài
    - Kiến thức dùng
    - Hướng làm cả bài
    - Lỗi dễ mắc
    - Ba mẹ nên hỏi con
  - nếu phù hợp có thể thêm:
    - Lời giải mẫu ngắn
  - không được hỏi phụ huynh từng bước như mode trẻ

- "Kiến thức dùng" phải nói đúng bản chất toán học đang dùng.
- "Cách nghĩ nhanh" hoặc "Hướng làm" phải nói ngắn gọn bước đi.
- Không giải hộ ngay trừ khi support_level là 'cach_giai'
- Nếu bài có dấu hiệu khác đơn vị, phải nhắc chú ý đổi về cùng đơn vị
"""
    return context.strip()


def classify_user_reply(user_input: str) -> str:
    raw_text = user_input.strip()
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
        "khongbieet",
        "kobiet",
        "kbiet",
        "khonghieu",
        "kohieu",
        "chuabiet",
        "chuabieet",
    }
    dont_know_signals = [
        "khong biet",
        "ko biet",
        "k biet",
        "con khong biet",
        "con ko biet",
        "khong hieu",
        "ko hieu",
        "khong ro",
        "la sao",
        "kho qua",
        "con bi",
        "bi qua",
        "khong lam duoc",
        "ko lam duoc",
        "khong biet lam",
        "khong biet nua",
        "khong biet that",
        "van khong biet",
        "chua biet",
        "chua biet nua",
        "chua hieu",
        "khong biey",
    ]

    if normalized in exact_dont_know or compact in exact_dont_know:
        return "student_dont_know"

    if any(signal in normalized for signal in dont_know_signals):
        return "student_dont_know"

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
    text = user_input.strip().lower()

    has_number = any(ch.isdigit() for ch in text)
    has_equal = "=" in text
    has_unit = any(
        unit in text for unit in [
            "bao", "cm", "kg", "g", "quyển", "chai", "khay", "mét",
            "xi măng", "quả", "cái", "m", "viên", "gạch", "bút", "hoa"
        ]
    )

    if has_number and not has_equal and not has_unit:
        return True

    return False


def should_require_full_presentation(st, user_input: str) -> bool:
    text = user_input.strip().lower()

    has_equal = "=" in text
    has_unit = any(
        unit in text for unit in [
            "bao", "cm", "kg", "g", "quyển", "chai", "khay", "mét",
            "xi măng", "quả", "cái", "m", "viên", "gạch", "bút", "hoa"
        ]
    )

    if has_equal or has_unit:
        return False

    if st.session_state.presentation_retry_count >= 1:
        return False

    return True


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
    st.session_state.show_solution_button = (
        st.session_state.stuck_count >= 3 or st.session_state.allow_full_solution
    )


def detect_finished_response(response_text: str) -> bool:
    text = response_text.lower()

    direct_finish_signals = [
        "đáp số",
        "đáp án đầy đủ là",
        "vậy đáp án đầy đủ là",
        "vậy là con đã giải xong",
        "vậy là mình đã giải xong",
        "con đã giải xong bài này rồi",
        "con đã hoàn thành bài này rồi",
        "đã hoàn thành bài toán này",
        "đã làm xong bài này",
    ]
    if any(s in text for s in direct_finish_signals):
        return True

    if "kiến thức cần nhớ:" in text and any(
        s in text for s in [
            "đáp án",
            "đáp số",
            "vậy là con đã giải xong",
            "vậy là mình đã giải xong",
            "con làm rất tốt",
            "chính xác",
            "đúng rồi",
            "kết quả là",
        ]
    ):
        return True

    return False


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
    step_plan = _build_step_plan(problem_text, frame)
    current_step_hint = _infer_current_step_hint(problem_text, chat_history)

    history_text = ""
    for msg in chat_history[-6:]:
        if mode == "parent":
            role = "Ba mẹ" if msg["role"] == "user" else "Trợ lý"
        else:
            role = "Học sinh" if msg["role"] == "user" else "Thầy"
        history_text += f"- {role}: {msg['content']}\n"

    full_solution_rule = (
        "Được phép trình bày cách giải theo từng bước."
        if allow_full_solution
        else "Không được đưa lời giải đầy đủ hoặc đáp án cuối cùng ngay."
    )

    if small_error:
        error_rule = """
- Đây là lỗi nhỏ.
- Nếu học sinh đã ra đúng kết quả số hoặc gần đúng ý chính:
  - công nhận điều đúng trước
  - nhắc lỗi nhỏ ngắn gọn
  - nếu chỉ thiếu đơn vị/câu trả lời thì chỉ nhắc tối đa 1 lần
  - sau đó có thể tự chốt câu trả lời đầy đủ
- Không giữ học sinh quá lâu ở phần trình bày hình thức.
"""
    else:
        error_rule = """
- Nếu đây là lỗi lớn:
  - chỉ ra đúng chỗ sai
  - dạy tiếp ngắn gọn
  - kéo học sinh làm tiếp bước đúng
"""

    escalation_rule = f"""
- stuck_count hiện tại là: {stuck_count}
- Nếu mode là child:
  - stuck_count = 1: gợi ý nhẹ
  - stuck_count = 2: gợi ý rõ hơn, nêu số cần dùng hoặc nêu chọn phép tính
  - stuck_count >= 3:
    - không được vòng vo nữa
    - nói thẳng bước cần làm hoặc phép tính cần viết
    - để học sinh làm bước cuối hoặc tính kết quả
- Nếu mode là parent:
  - không đi theo kiểu stuck_count từng bước như trẻ
  - trả lời theo kiểu nhìn toàn bài, gói gọn vấn đề chính
"""

    presentation_rule = (
        "Có thể yêu cầu học sinh viết rõ phép tính hoặc đơn vị, nhưng chỉ ngắn gọn, không lặp lại nhiều lần."
        if require_full_presentation
        else "Không được giữ học sinh quá lâu ở việc viết lại phép tính hoặc đơn vị nếu con đã hiểu ý chính."
    )

    finish_rule = (
        "Bài đã hoàn tất. Không hỏi hỗ trợ thêm. Chỉ chốt ngắn gọn nếu cần."
        if is_finished
        else "Nếu bài vừa hoàn tất, hãy chốt đáp án đầy đủ và chốt 1 dòng kiến thức cần nhớ."
    )

    mode_rule = f"""
- Khung tư duy gợi ý cho bài này:
  - Dạng bài: {frame["problem_type"]}
  - Kiến thức dùng: {frame["knowledge"]}
  - Cách nghĩ nhanh: {frame["thinking"]}

- Kế hoạch bước giải gợi ý:
{chr(10).join(f"  - {step}" for step in step_plan)}

- Gợi ý bước hiện tại:
  - {current_step_hint}

- Nếu mode là child:
  - tối đa 2 câu ngắn + 1 câu hỏi
  - tránh lặp lại nguyên dữ kiện dài dòng
  - không chỉ dắt thao tác; phải cho con thấy mình đang ở bước nào
  - nếu con đang bí, câu đầu tiên ưu tiên nhắc ngắn:
    - đang ở bước nào
    - bước này để làm gì
  - sau đó mới hỏi tiếp hoặc cho phép tính
  - nếu đã biết rõ bước hiện tại, ưu tiên hỏi thẳng phép tính hoặc kết quả của bước đó; tránh hỏi lại quá chung chung kiểu "dùng phép tính gì?" nhiều lần
  - tránh mở đầu lặp lại các câu như:
    - "Chào con"
    - "Không sao đâu con"
    - "À, thầy hiểu rồi"
  - nếu cần động viên, chỉ dùng 1 cụm rất ngắn rồi vào ngay việc chính
  - nếu học sinh đã có đúng kết quả số nhưng thiếu đơn vị hoặc thiếu câu đầy đủ:
    - chỉ nhắc thêm 1 ý còn thiếu
    - sau đó chốt luôn khi con chưa bổ sung đúng ở lượt kế tiếp
  - khi phù hợp, có thể nhắc rất ngắn theo mẫu:
    - Dạng bài: ...
    - Kiến thức dùng: ...
    - Cách nghĩ nhanh: ...
  - nhưng phải gọn, không giảng thành đoạn dài

- Nếu mode là parent:
  - ưu tiên giải thích TOÀN BÀI trong một lượt
  - không hỏi phụ huynh từng bước như học sinh
  - tuyệt đối không gọi người dùng là "con"
  - nếu phụ huynh nhắn ngắn kiểu "không biết", vẫn hiểu là đang hỏi thay con hoặc hỏi tiếp cho con
  - dùng cấu trúc:
    - Dạng bài
    - Kiến thức dùng
    - Hướng làm cả bài
    - Lỗi dễ mắc
    - Ba mẹ nên hỏi con
  - nếu phù hợp có thể thêm:
    - Lời giải mẫu ngắn
"""

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

Luật rất quan trọng:
- {full_solution_rule}
- {presentation_rule}
{error_rule}
{escalation_rule}
{mode_rule}
- Nếu reply_type là student_number_only:
  - chỉ nhắc viết rõ hơn thật ngắn
  - không kéo dài nhiều lượt
  - nếu con đã có đúng kết quả số thì chỉ hỏi thêm phần còn thiếu rồi chốt nhanh
- Nếu reply_type là student_dont_know:
  - child:
    - tăng hỗ trợ theo stuck_count
    - ưu tiên nhắc lại kiến thức đang dùng hoặc cách nghĩ nhanh trước
    - stuck_count = 1: nhắc rất ngắn bước hiện tại rồi hỏi lại đúng bước đó
    - stuck_count = 2: nói rõ hơn đang ở bước nào và cần làm phép tính gì
    - stuck_count >= 3: nói thẳng phép tính hoặc bước cần làm
  - parent:
    - gom lại và giải thích toàn bài ngắn gọn hơn
- Nếu reply_type là student_asks_answer mà chưa được phép giải đầy đủ:
  - child: từ chối nhẹ nhàng trước, rồi tăng hỗ trợ nếu bí nhiều lần
  - parent: có thể cho hướng giải đầy đủ ngắn gọn hơn
- Không được lẫn sang bài cũ
- Chỉ bám đúng đề bài hiện tại
- Nếu học sinh đã có kết quả đúng nhưng thiếu đơn vị/câu đầy đủ:
  - nói rõ là kết quả đúng rồi
  - nhắc thêm phần còn thiếu
  - nếu vẫn chưa bổ sung đúng ở lượt kế tiếp, tự chốt luôn câu trả lời đầy đủ
- Nếu học sinh trả lời các mảnh đúng như:
  - từ khóa ngắn
  - phép tính
  - vài số đúng
  thì hiểu là con đang có ý đúng một phần; hãy tận dụng để ghép lại và dạy tiếp, không coi như hoàn toàn không biết
- {finish_rule}
- Sau khi chốt đáp án, thêm 1 dòng rất ngắn:
  - Kiến thức cần nhớ: ...
- Dòng "Kiến thức cần nhớ" nên ưu tiên chốt theo mẫu tư duy, ví dụ:
  - tìm 1 phần trước rồi tìm nhiều phần
  - đổi về cùng đơn vị trước rồi mới tính
  - tính phần đã bán trước rồi tìm phần còn lại
- Nếu mode là parent, tránh kết thúc bằng câu hỏi nếu không cần

Tin nhắn mới nhất của người dùng:
{user_input}
"""
    return context.strip()


def update_step_and_error(st, reply_type: str):
    if reply_type == "student_dont_know":
        st.session_state.last_error_type = "khong_biet"
    elif reply_type == "student_number_only":
        st.session_state.last_error_type = "chi_1_con_so"
    elif reply_type == "student_asks_answer":
        st.session_state.last_error_type = "xin_dap_an"
    else:
        st.session_state.last_error_type = ""


def update_presentation_retry(st, require_full_presentation: bool):
    if require_full_presentation:
        st.session_state.presentation_retry_count += 1
    else:
        st.session_state.presentation_retry_count = 0


def build_summary_context(problem_text: str, chat_history: list) -> str:
    summary_prompt = get_summary_prompt()

    history_text = ""
    for msg in chat_history[-10:]:
        role = "Học sinh" if msg["role"] == "user" else "Thầy"
        history_text += f"- {role}: {msg['content']}\n"

    context = f"""
{summary_prompt}

Đề bài:
{problem_text}

Lịch sử buổi học:
{history_text}
"""
    return context.strip()
