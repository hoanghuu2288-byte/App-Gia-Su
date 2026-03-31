# logic.py

from prompts import (
    get_system_prompt,
    get_support_guide,
    get_summary_prompt,
    get_first_response_guide,
)


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
        "presentation_retry_count": 0,   # số lần đã nhắc viết rõ phép tính/đơn vị
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


def looks_like_new_problem(user_input: str) -> bool:
    text = user_input.strip().lower()

    # dấu hiệu khá mạnh của một đề bài mới
    signals = [
        "hỏi", "một", "một cửa hàng", "một cuộn", "một thùng",
        "một thư viện", "một hình", "tính", "tìm x", "tìm",
        "bao nhiêu", "còn lại", "chia đều", "chiều dài", "chiều rộng"
    ]

    long_enough = len(text) >= 35
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


def build_initial_context(problem_text: str, mode: str, support_level: str) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    first_response_guide = get_first_response_guide()

    context = f"""
{system_prompt}

{support_guide}

{first_response_guide}

Đề bài đã xác nhận:
{problem_text}

Yêu cầu rất quan trọng:
- Đây là phản hồi đầu tiên sau khi đã có đề bài.
- Nếu mode là child:
  - chỉ trả lời NGẮN
  - tối đa 2 câu ngắn + 1 câu hỏi
  - không giảng dài dòng
- Nếu mode là parent:
  - ngắn, rõ, thực dụng
- Không giải hộ ngay trừ khi support_level là 'cach_giai'
- Nếu bài có dấu hiệu khác đơn vị, phải nhắc chú ý đổi về cùng đơn vị
- Không dùng lời mở đầu quá dài
"""
    return context.strip()


def classify_user_reply(user_input: str) -> str:
    text = user_input.strip().lower()

    if not text:
        return "empty"

    dont_know_signals = [
        "không biết", "ko biết", "k biết", "con không biết",
        "khó quá", "bí", "con bí", "không hiểu", "ko hiểu", "là sao"
    ]
    if any(signal in text for signal in dont_know_signals):
        return "student_dont_know"

    ask_answer_signals = [
        "đáp án", "giải luôn", "cho con đáp án", "cho đáp án",
        "giải hộ", "làm hộ", "cho con kết quả"
    ]
    if any(signal in text for signal in ask_answer_signals):
        return "student_asks_answer"

    cleaned = text.replace(",", "").replace(".", "").replace(" ", "")
    if cleaned.isdigit():
        return "student_number_only"

    return "normal_reply"


def should_require_full_presentation(st, user_input: str) -> bool:
    """
    Giảm việc bắt viết lại phép tính/đơn vị quá nhiều lần.
    Chỉ nhắc tối đa 1 lần mạnh mẽ cho mỗi bước.
    """
    text = user_input.strip().lower()

    has_equal = "=" in text
    has_unit = any(unit in text for unit in ["bao", "cm", "kg", "g", "quyển", "chai", "khay", "mét"])

    # nếu đã có phép tính hoặc đơn vị tương đối rõ, không ép thêm
    if has_equal or has_unit:
        return False

    # nếu đã nhắc rồi, cho qua để giữ nhịp
    if st.session_state.presentation_retry_count >= 1:
        return False

    return True


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
) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)

    history_text = ""
    for msg in chat_history[-6:]:
        role = "Học sinh" if msg["role"] == "user" else "Thầy"
        history_text += f"- {role}: {msg['content']}\n"

    full_solution_rule = (
        "Được phép trình bày cách giải theo từng bước."
        if allow_full_solution
        else "Không được đưa lời giải đầy đủ hoặc đáp án cuối cùng ngay."
    )

    presentation_rule = (
        "Có thể yêu cầu học sinh viết rõ phép tính hoặc đơn vị, nhưng chỉ ngắn gọn, không lặp lại nhiều lần."
        if require_full_presentation
        else "Không được giữ học sinh quá lâu ở việc viết lại phép tính/đơn vị nếu con đã hiểu ý chính."
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

Luật rất quan trọng:
- {full_solution_rule}
- {presentation_rule}
- Nếu reply_type là student_number_only:
  - chỉ nhắc viết rõ phép tính/đơn vị thật ngắn
  - không kéo dài nhiều lượt
- Nếu reply_type là student_dont_know:
  - tăng hỗ trợ thêm một nấc
  - ngắn gọn
  - có thể dùng sơ đồ chữ nếu thật cần
- Nếu reply_type là student_asks_answer mà chưa được phép giải đầy đủ:
  - từ chối nhẹ nhàng
  - kéo về bước gần nhất
- Nếu học sinh đã hiểu bước hiện tại, chuyển tiếp nhanh sang bước sau
- Nếu mode là child:
  - tối đa 2 câu ngắn + 1 câu hỏi
  - tránh lặp lại nguyên dữ kiện dài dòng
- Không được lẫn sang bài cũ
- Chỉ bám đúng đề bài hiện tại
- Mỗi lượt chỉ kết thúc bằng đúng 1 câu hỏi ngắn

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
