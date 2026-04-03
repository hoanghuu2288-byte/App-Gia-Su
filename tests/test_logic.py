# tests/test_logic.py

import os
import sys
from types import SimpleNamespace

# Cho pytest thấy thư mục gốc của repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic import (
    looks_like_new_problem,
    classify_user_reply,
    is_small_error,
    detect_problem_complexity,
    detect_finished_response,
    update_stuck_ui,
    reset_session,
    start_new_problem,
    should_require_full_presentation,
    update_presentation_retry,
    should_mark_finished_after_child_help,
    generate_opening_tutoring_response,
    generate_followup_tutoring_response,
)


class DummyStreamlit:
    def __init__(self):
        self.session_state = SimpleNamespace(
            problem_text="Bài cũ",
            problem_confirmed=True,
            problem_type="word_problem",
            current_step="step_2",
            last_error_type="khong_biet",
            allow_full_solution=False,
            chat_history=[{"role": "assistant", "content": "Old"}],
            summary="old summary",
            pending_image="img",
            presentation_retry_count=1,
            stuck_count=2,
            show_help_buttons=True,
            show_hint_button=True,
            show_solution_button=True,
            is_finished=True,
        )


def test_looks_like_new_problem_true():
    text = "Một thùng có 36 chai nước, chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai nước?"
    assert looks_like_new_problem(text) is True


def test_looks_like_new_problem_false():
    text = "con không biết"
    assert looks_like_new_problem(text) is False


def test_classify_user_reply_dont_know():
    assert classify_user_reply("con không biết") == "student_dont_know"
    assert classify_user_reply("khó quá") == "student_dont_know"


def test_classify_user_reply_asks_answer():
    assert classify_user_reply("cho con đáp án") == "student_asks_answer"
    assert classify_user_reply("giải luôn đi") == "student_asks_answer"


def test_classify_user_reply_number_only():
    assert classify_user_reply("24000") == "student_number_only"
    assert classify_user_reply("  54000  ") == "student_number_only"


def test_classify_user_reply_normal():
    assert classify_user_reply("con nghĩ là phép trừ") == "normal_reply"


def test_is_small_error_true():
    assert is_small_error("24000") is True


def test_is_small_error_false_when_has_unit():
    assert is_small_error("24000 viên gạch") is False


def test_is_small_error_false_when_has_equation():
    assert is_small_error("18000 x 3 = 54000") is False


def test_detect_problem_complexity_medium_or_hard():
    text = "Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. Hỏi còn phải mua bao nhiêu viên nữa?"
    assert detect_problem_complexity(text) == "medium_or_hard"


def test_detect_problem_complexity_easy():
    text = "36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?"
    assert detect_problem_complexity(text) == "easy"


def test_detect_finished_response_true():
    assert detect_finished_response("Con đã hoàn thành bài này rồi.") is True
    assert detect_finished_response("Đáp số: 24 000 viên gạch.") is True


def test_detect_finished_response_false():
    assert detect_finished_response("Con hãy tính bước tiếp theo nhé.") is False


def test_update_stuck_ui_first_level():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 0
    st.session_state.allow_full_solution = False

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.stuck_count == 1
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is False
    assert st.session_state.show_solution_button is False


def test_update_stuck_ui_second_level():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 1
    st.session_state.allow_full_solution = False

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.stuck_count == 2
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is True
    assert st.session_state.show_solution_button is False


def test_update_stuck_ui_third_level():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 2
    st.session_state.allow_full_solution = False

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.stuck_count == 3
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is True
    assert st.session_state.show_solution_button is True


def test_update_stuck_ui_solution_shows_when_full_solution_allowed():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 1
    st.session_state.allow_full_solution = True

    update_stuck_ui(st, "normal_reply")

    assert st.session_state.show_solution_button is True


def test_update_stuck_ui_hides_buttons_when_finished():
    st = DummyStreamlit()
    st.session_state.is_finished = True

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.show_help_buttons is False
    assert st.session_state.show_hint_button is False
    assert st.session_state.show_solution_button is False


def test_reset_session_clears_state():
    st = DummyStreamlit()

    reset_session(st)

    assert st.session_state.problem_text == ""
    assert st.session_state.problem_confirmed is False
    assert st.session_state.problem_type == ""
    assert st.session_state.current_step == "start"
    assert st.session_state.last_error_type == ""
    assert st.session_state.allow_full_solution is False
    assert st.session_state.chat_history == []
    assert st.session_state.summary == ""
    assert st.session_state.pending_image is None
    assert st.session_state.presentation_retry_count == 0
    assert st.session_state.stuck_count == 0
    assert st.session_state.show_help_buttons is False
    assert st.session_state.show_hint_button is False
    assert st.session_state.show_solution_button is False
    assert st.session_state.is_finished is False


def test_start_new_problem_resets_learning_flow():
    st = DummyStreamlit()

    new_problem = "Một thư viện có 840 quyển sách. Hỏi còn lại bao nhiêu quyển?"
    start_new_problem(st, new_problem)

    assert st.session_state.problem_text == new_problem
    assert st.session_state.problem_confirmed is True
    assert st.session_state.current_step == "start"
    assert st.session_state.last_error_type == ""
    assert st.session_state.chat_history == []
    assert st.session_state.summary == ""
    assert st.session_state.presentation_retry_count == 0
    assert st.session_state.stuck_count == 0
    assert st.session_state.show_help_buttons is False
    assert st.session_state.show_hint_button is False
    assert st.session_state.show_solution_button is False
    assert st.session_state.is_finished is False


def test_should_require_full_presentation_true_initially():
    st = DummyStreamlit()
    st.session_state.presentation_retry_count = 0

    assert should_require_full_presentation(st, "54000") is True


def test_should_require_full_presentation_false_after_retry():
    st = DummyStreamlit()
    st.session_state.presentation_retry_count = 1

    assert should_require_full_presentation(st, "54000") is False


def test_should_require_full_presentation_false_when_has_unit():
    st = DummyStreamlit()
    st.session_state.presentation_retry_count = 0

    assert should_require_full_presentation(st, "24000 viên gạch") is False


def test_update_presentation_retry():
    st = DummyStreamlit()
    st.session_state.presentation_retry_count = 0

    update_presentation_retry(st, True)
    assert st.session_state.presentation_retry_count == 1

    update_presentation_retry(st, False)
    assert st.session_state.presentation_retry_count == 0


def test_classify_user_reply_choice_letter_variants():
    assert classify_user_reply("d") == "normal_reply"
    assert classify_user_reply("D.") == "normal_reply"
    assert classify_user_reply("đáp án d") == "normal_reply"


def test_detect_finished_response_true_with_knowledge_line_and_full_answer():
    text = (
        "Thầy nói thẳng: **78 000 - 54 000 = 24 000**.\n\n"
        "Bác Hùng còn phải mua **24 000 viên gạch** nữa.\n\n"
        "Kiến thức cần nhớ: Tìm số còn lại thì lấy số dự tính trừ số đã có."
    )
    assert detect_finished_response(text) is True


def test_should_mark_finished_after_child_help_true_after_many_hints():
    text = (
        "Thầy nói thẳng: **78 000 - 54 000 = 24 000**.\n\n"
        "Bác Hùng còn phải mua **24 000 viên gạch** nữa.\n\n"
        "Kiến thức cần nhớ: Tìm số còn lại thì lấy số dự tính trừ số đã có."
    )
    assert should_mark_finished_after_child_help(text, hint_request_count=3) is True


def test_generate_opening_tutoring_response_child_geometry():
    response = generate_opening_tutoring_response(
        """Câu 4: (1 điểm) Cho hình vẽ. Từ vị trí ong vàng đến vườn hoa nào là xa nhất?

Dữ kiện nhìn thấy trong hình:
- Đường đến Vườn hoa hồng: 42890 m
- Đường đến Vườn hoa lan: 35000 m
- Đường đến Vườn hoa cúc: 45050 m
- Đường đến Vườn hoa hướng dương: 25090 m

Các lựa chọn:
A. Vườn hoa hồng
B. Vườn hoa lan
C. Vườn hoa cúc
D. Vườn hoa hướng dương
""",
        mode="child",
        support_level="goi_y",
    )

    assert "Dạng bài" in response
    assert "45050" in response or "45 050" in response


def test_generate_followup_tutoring_response_child_geometry_finalizes_choice():
    chat_history = [
        {"role": "assistant", "content": "opening"},
        {"role": "user", "content": "Chọn đáp án C"},
    ]
    response = generate_followup_tutoring_response(
        problem_text="""Câu 4: (1 điểm) Cho hình vẽ. Từ vị trí ong vàng đến vườn hoa nào là xa nhất?

Dữ kiện nhìn thấy trong hình:
- Đường đến Vườn hoa hồng: 42890 m
- Đường đến Vườn hoa lan: 35000 m
- Đường đến Vườn hoa cúc: 45050 m
- Đường đến Vườn hoa hướng dương: 25090 m

Các lựa chọn:
A. Vườn hoa hồng
B. Vườn hoa lan
C. Vườn hoa cúc
D. Vườn hoa hướng dương
""",
        mode="child",
        support_level="goi_y",
        chat_history=chat_history,
        user_input="Chọn đáp án C",
        reply_type="normal_reply",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=0,
        is_finished=False,
        hint_request_count=0,
    )

    assert "Vườn hoa cúc" in response
    assert "Kiến thức cần nhớ" in response


def test_generate_followup_tutoring_response_rut_ve_don_vi_finalizes():
    chat_history = [
        {"role": "assistant", "content": "opening"},
        {"role": "user", "content": "72"},
    ]
    response = generate_followup_tutoring_response(
        problem_text="Có 6 hộp bút như nhau đựng tất cả 48 chiếc bút. Hỏi 9 hộp như thế đựng bao nhiêu chiếc bút?",
        mode="child",
        support_level="goi_y",
        chat_history=chat_history,
        user_input="72",
        reply_type="student_number_only",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=True,
        stuck_count=0,
        is_finished=False,
        hint_request_count=0,
    )

    assert "72 chiếc bút" in response
    assert "Kiến thức cần nhớ" in response
