# tests/test_logic.py

from types import SimpleNamespace

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
)


class DummyStreamlit:
    def __init__(self):
        self.session_state = SimpleNamespace(
            problem_text="Bài cũ",
            problem_confirmed=True,
            problem_type="word_problem",
            current_step="step_2",
            last_error_type="khong_biet",
            allow_full_solution=True,
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

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.stuck_count == 1
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is False
    assert st.session_state.show_solution_button is False


def test_update_stuck_ui_second_level():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 1

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.stuck_count == 2
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is True
    assert st.session_state.show_solution_button is False


def test_update_stuck_ui_third_level():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 2

    update_stuck_ui(st, "student_dont_know")

    assert st.session_state.stuck_count == 3
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is True
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
