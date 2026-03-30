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

Yêu cầu:
- Đây là phản hồi đầu tiên sau khi đã có đề bài.
- Nếu mode là child, hãy trả lời rất ngắn, dễ hiểu, đúng trình độ lớp 3.
- Nếu mode là parent, hãy nói với phụ huynh bằng giọng rõ ràng, thực dụng.
- Không giải hộ ngay trừ khi support_level là 'cach_giai'.
- Nếu bài có dấu hiệu khác đơn vị, phải nhắc chú ý đổi về cùng đơn vị.
"""
    return context.strip()


def classify_user_reply(user_input: str) -> str:
    text = user_input.strip().lower()

    if not text:
        return "empty"

    dont_know_signals = [
        "không biết", "ko biết", "k biết", "con không biết",
        "khó quá", "bí", "con bí", "không hiểu", "ko hiểu"
    ]
    if any(signal in text for signal in dont_know_signals):
        return "student_dont_know"

    ask_answer_signals = [
        "đáp án", "giải luôn", "cho con đáp án", "cho đáp án",
        "giải hộ", "làm hộ", "cho con kết quả"
    ]
    if any(signal in text for signal in ask_answer_signals):
        return "student_asks_answer"

    # chỉ 1 con số đơn giản
    cleaned = text.replace(",", "").replace(".", "")
    if cleaned.isdigit():
        return "student_number_only"

    return "normal_reply"


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
) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)

    history_text = ""
    for msg in chat_history[-8:]:
        role = "Học sinh" if msg["role"] == "user" else "Thầy"
        history_text += f"- {role}: {msg['content']}\n"

    full_solution_rule = (
        "Được phép trình bày cách giải theo từng bước."
        if allow_full_solution
        else "Không được đưa lời giải đầy đủ hoặc đáp án cuối cùng ngay."
    )

    context = f"""
{system_prompt}

{support_guide}

Đề bài:
{problem_text}

Lịch sử gần đây:
{history_text}

Trạng thái hiện tại:
- mode: {mode}
- current_step: {current_step}
- last_error_type: {last_error_type}
- reply_type: {reply_type}
- allow_full_solution: {allow_full_solution}

Luật thêm:
- {full_solution_rule}
- Nếu reply_type là student_number_only, yêu cầu viết rõ phép tính và đơn vị.
- Nếu reply_type là student_dont_know, tăng hỗ trợ thêm một nấc bằng lời ngắn gọn.
- Nếu reply_type là student_asks_answer mà chưa được phép giải đầy đủ, từ chối nhẹ nhàng và kéo về bước gần nhất.
- Mỗi lượt chỉ kết thúc bằng đúng 1 câu hỏi ngắn.
- Không viết dài dòng.

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


def build_summary_context(problem_text: str, chat_history: list) -> str:
    summary_prompt = get_summary_prompt()

    history_text = ""
    for msg in chat_history[-12:]:
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
