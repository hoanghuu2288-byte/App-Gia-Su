# logic.py

from prompts import (
    get_system_prompt,
    get_support_guide,
    get_summary_prompt,
    get_first_response_guide,
)
from grade3_math_master import GRADE3_MATH_MASTER, get_problem_blueprint


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
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session(st):
    st.session_state.problem_text = ""
    st.session_state.problem_confirmed = False
    st.session_state.problem_type = ""
    st.session_state.problem_blueprint = {}
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
        "chọn đáp án đúng", "khẳng định đúng"
    ]

    long_enough = len(text) >= 20
    has_signal = any(s in text for s in signals)

    return long_enough and has_signal


def normalize_text(text: str) -> str:
    return text.strip().lower()


def detect_problem_type(problem_text: str) -> str:
    text = normalize_text(problem_text)

    # Ưu tiên các dạng đặc biệt trước
    if any(k in text for k in ["chọn khẳng định đúng", "chọn đáp án đúng", "câu nào đúng", "phương án đúng"]):
        if any(k in text for k in ["tâm hình tròn", "bán kính", "đường kính", "hình tròn", "oq", "op", "mn"]):
            return "multiple_choice_geometry_circle"
        return "multiple_choice_general"

    if any(k in text for k in ["tâm", "bán kính", "đường kính", "hình tròn"]):
        return "geometry_identification_circle_parts"

    if any(k in text for k in ["xa nhất", "lớn nhất", "bé nhất", "nhỏ nhất", "ngắn nhất"]):
        return "compare_largest_smallest"

    if any(k in text for k in [" m ", " cm", " kg", " g", "xăng-ti-mét", "ki-lô-gam", "đổi"]):
        return "unit_conversion_then_calculate"

    if any(k in text for k in ["như nhau", "tất cả", "mấy hộp", "mấy khay", "mấy gói", "mấy chồng"]):
        if any(k in text for k in ["9 hộp", "mỗi hộp", "mỗi khay", "mỗi gói", "mỗi chồng"]):
            return "unit_rate_find_one_then_many"

    if any(k in text for k in ["mỗi lần", "đã mua", "còn phải", "còn thiếu", "dự tính"]):
        return "multi_step_find_missing"

    if any(k in text for k in ["còn lại", "bớt", "cắt đi", "cho đi", "bán đi"]):
        return "one_step_word_problem_subtract"

    if any(k in text for k in ["thêm", "tất cả", "cả hai", "gộp", "tổng cộng"]):
        return "one_step_word_problem_add"

    if any(k in text for k in [":", "×", "x", "nhân", "chia"]):
        return "direct_calculation_multiply_divide"

    if any(k in text for k in ["+", "-", "đặt tính", "tính nhẩm"]):
        return "direct_calculation_add_subtract"

    # fallback
    return "multi_step_find_missing"


def start_new_problem(st, new_problem_text: str):
    detected_type = detect_problem_type(new_problem_text)
    blueprint = get_problem_blueprint(detected_type)

    st.session_state.problem_text = new_problem_text.strip()
    st.session_state.problem_confirmed = True
    st.session_state.problem_type = detected_type
    st.session_state.problem_blueprint = blueprint
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
        "chọn khẳng định đúng", "chọn đáp án đúng"
    ]

    count = sum(1 for s in multi_step_signals if s in text)

    if count >= 2:
        return "medium_or_hard"
    return "easy"


def build_plan_block(problem_blueprint: dict) -> str:
    if not problem_blueprint:
        return ""

    if not problem_blueprint.get("show_plan_steps"):
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
- Nên đi theo kiểu:
  - xét A đúng hay sai
  - rồi mới sang B
  - rồi C
  - rồi D
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

    context = f"""
{system_prompt}

{support_guide}

{first_response_guide}

Đề bài đã xác nhận:
{problem_text}

Dạng bài nội bộ:
- problem_type: {problem_type}
- label: {blueprint.get("label", "")}
- flow_type: {blueprint.get("flow_type", "")}
- knowledge_used: {blueprint.get("knowledge_used", "")}

Mức độ bài:
{complexity}

{plan_block}

{mc_rule}

Yêu cầu rất quan trọng:
- Đây là phản hồi đầu tiên sau khi đã có đề bài.
- Nếu mode là child:
  - Nếu bài easy:
    - mở đầu ngắn
    - không nói thừa
  - Nếu bài nhiều bước:
    - nêu:
      - Dạng bài
      - Kiến thức dùng
      - sơ đồ bước rất ngắn nếu cần
    - không được lộ phép tính
    - không được lộ đáp án
  - Nếu bài trắc nghiệm:
    - phải nói "mình xét từng đáp án một"
    - không được giải hộ rồi chốt ngay
  - tối đa 4 đoạn ngắn
  - chỉ 1 câu hỏi cuối

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

- "Kiến thức dùng" phải nói đúng bản chất toán học đang dùng
- Không được nói mơ hồ kiểu:
  - "Cốt lõi là tìm đáp án"
  - "Cốt lõi là tìm số còn lại"

- Nếu bài nhiều bước:
  - chỉ hiện tên bước
  - không hiện phép tính ở opening
- Nếu bài trắc nghiệm:
  - ưu tiên chiến lược xét từng đáp án
- Nếu support_level là 'goi_y':
  - không được giải hộ sớm
  - không được cho kết quả trung gian quá sớm
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


def is_small_error(user_input: str) -> bool:
    text = user_input.strip().lower()

    has_number = any(ch.isdigit() for ch in text)
    has_equal = "=" in text
    has_unit = any(
        unit in text for unit in [
            "bao", "cm", "kg", "g", "quyển", "chai", "khay", "mét",
            "xi măng", "quả", "cái", "m", "viên", "gạch", "hộp", "bút"
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
            "xi măng", "quả", "cái", "m", "viên", "gạch", "hộp", "bút"
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
    finish_signals = [
        "đã hoàn thành bài toán này",
        "đã làm xong bài này",
        "đáp số",
        "vậy mình sẽ nói là",
        "con giỏi lắm! con đã hoàn thành",
        "con đã hoàn thành bài này rồi"
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
) -> str:
    system_prompt = get_system_prompt(mode)
    support_guide = get_support_guide(support_level)
    problem_type = detect_problem_type(problem_text)
    blueprint = get_problem_blueprint(problem_type)
    mc_rule = build_multiple_choice_rule(blueprint)

    history_text = ""
    for msg in chat_history[-6:]:
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
  - có thể tự chốt câu trả lời đầy đủ
  - không giữ học sinh quá lâu
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
  - stuck_count = 2: gợi ý rõ hơn, nêu bước cần làm
  - stuck_count >= 3:
    - không được vòng vo nữa
    - nói thẳng bước cần làm
    - nhưng chưa tự chốt toàn bộ bài nếu chưa cần
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
        else "Nếu bài vừa hoàn tất, hãy chốt đáp án đầy đủ và chốt 1-2 ý kiến thức cần nhớ."
    )

    mode_rule = """
- Nếu mode là child:
  - mỗi lượt chỉ 1 mục tiêu
  - chỉ 1 câu hỏi cuối
  - không lặp cùng một ý quá 1 lần
  - tránh lặp lại nguyên dữ kiện dài dòng
  - không hỏi rồi tự trả lời ngay
- Nếu mode là parent:
  - ưu tiên giải thích TOÀN BÀI trong một lượt
  - không hỏi phụ huynh từng bước như học sinh
  - dùng cấu trúc:
    - Dạng bài
    - Kiến thức dùng
    - Hướng làm cả bài
    - Lỗi dễ mắc
    - Ba mẹ nên hỏi con
  - nếu phù hợp có thể thêm:
    - Lời giải mẫu ngắn
"""

    problem_flow_rule = f"""
- problem_type hiện tại: {problem_type}
- flow_type hiện tại: {blueprint.get("flow_type", "")}
- knowledge_used: {blueprint.get("knowledge_used", "")}

- Nếu flow_type là multi_step:
  - chỉ đi từng bước
  - không tự nhảy tới đáp số
- Nếu flow_type là unit_conversion:
  - bắt buộc đổi đơn vị trước, rồi mới tính
- Nếu flow_type là compare_numbers:
  - tập trung tìm số lớn nhất/nhỏ nhất trước
- Nếu flow_type là unit_rate:
  - phải tìm 1 phần trước rồi mới tìm nhiều phần
- Nếu flow_type là multiple_choice:
  - phải ưu tiên xét từng đáp án
  - không được tự loại hết quá sớm
- Nếu flow_type là geometry_identification:
  - nhận ra khái niệm chính trước rồi mới xét tiếp
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
{problem_flow_rule}
{mc_rule}

- Nếu reply_type là student_number_only:
  - chỉ nhắc viết rõ hơn thật ngắn
  - không kéo dài nhiều lượt
- Nếu reply_type là student_dont_know:
  - child: tăng hỗ trợ theo stuck_count
  - parent: gom lại và giải thích toàn bài ngắn gọn hơn
- Nếu reply_type là student_asks_answer mà chưa được phép giải đầy đủ:
  - child: từ chối nhẹ nhàng trước, rồi tăng hỗ trợ nếu bí nhiều lần
  - parent: có thể cho hướng giải đầy đủ ngắn gọn hơn
- Không được lẫn sang bài cũ
- Chỉ bám đúng đề bài hiện tại
- Nếu học sinh đã có kết quả đúng nhưng thiếu đơn vị/câu đầy đủ:
  - nói rõ là kết quả đúng rồi
  - nhắc thêm phần còn thiếu
  - rồi có thể tự chốt câu trả lời đầy đủ
- {finish_rule}
- Sau khi chốt đáp án, thêm 1 dòng rất ngắn:
  - Kiến thức cần nhớ: ...
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
