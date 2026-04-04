import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic import (
    _build_micro_goals,
    _extract_named_distances,
    _infer_active_micro_goal,
    _solve_circle_mcq,
    _solve_geometry_farthest,
    _solve_supported_problem,
    classify_user_reply,
    detect_finished_response,
    detect_problem_complexity,
    is_small_error,
    looks_like_new_problem,
    normalize_user_input,
    reset_session,
    should_require_full_presentation,
    start_new_problem,
    update_presentation_retry,
    update_stuck_ui,
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
            hint_request_count=3,
            last_assistant_response="old",
            last_real_user_reply="old",
        )


GEOMETRY_TEXT = """
Câu 4: (1 điểm) Cho hình vẽ. Từ vị trí ong vàng đến vườn hoa nào là xa nhất?

Dữ kiện nhìn thấy trong hình:
- Vườn hoa hồng: 42890 m (khoảng cách từ ong vàng)
- Vườn hoa cúc: 45050 m (khoảng cách từ ong vàng)
- Vườn hoa lan: 35000 m (khoảng cách từ ong vàng)
- Vườn hoa hướng dương: 25090 m (khoảng cách từ ong vàng)

Các lựa chọn:
A. Vườn hoa hồng
B. Vườn hoa lan
C. Vườn hoa cúc
D. Vườn hoa hướng dương
"""

CIRCLE_TEXT = """
Câu 6: Chọn khẳng định đúng trong các khẳng định sau:

Nhãn hình học nhìn thấy:
circle | Hình tròn tâm O: None None
point | O: None None
point | P: None None
point | Q: None None
point | N: None None
point | M: None None
line_segment | MN: None None
line_segment | OP: None None
line_segment | OQ: None None

Các lựa chọn:
A. OQ là đường kính
B. MN là bán kính
C. OP là đường kính
D. O là tâm hình tròn
"""


def test_looks_like_new_problem_true():
    text = "Một thùng có 36 chai nước, chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai nước?"
    assert looks_like_new_problem(text) is True



def test_looks_like_new_problem_false():
    assert looks_like_new_problem("con không biết") is False



def test_classify_user_reply_variants():
    assert classify_user_reply("con không biết") == "student_dont_know"
    assert classify_user_reply("cho con đáp án") == "student_asks_answer"
    assert classify_user_reply("24000") == "student_number_only"
    assert classify_user_reply("d") == "student_choice_only"
    assert classify_user_reply("con nghĩ là phép trừ") == "normal_reply"



def test_normalize_user_input_choice_letter():
    assert normalize_user_input("d") == "Chọn đáp án D"
    assert normalize_user_input("đáp án d") == "Chọn đáp án D"



def test_is_small_error_true_false():
    assert is_small_error("24000") is True
    assert is_small_error("24000 viên gạch") is False
    assert is_small_error("18000 x 3 = 54000") is False



def test_detect_problem_complexity():
    text = "Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. Hỏi còn phải mua bao nhiêu viên nữa?"
    assert detect_problem_complexity(text) == "medium_or_hard"
    assert detect_problem_complexity("36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?") == "easy"



def test_detect_finished_response():
    assert detect_finished_response("Đáp số: 24 000 viên gạch.") is True
    assert detect_finished_response("Kiến thức cần nhớ: đổi về cùng đơn vị trước rồi mới tính.") is True
    assert detect_finished_response("Con hãy tính bước tiếp theo nhé.") is False



def test_update_stuck_ui_levels():
    st = DummyStreamlit()
    st.session_state.is_finished = False
    st.session_state.stuck_count = 0
    st.session_state.allow_full_solution = False
    update_stuck_ui(st, "student_dont_know")
    assert st.session_state.show_help_buttons is True
    assert st.session_state.show_hint_button is False
    assert st.session_state.show_solution_button is False

    update_stuck_ui(st, "student_dont_know")
    assert st.session_state.show_hint_button is True

    st.session_state.stuck_count = 4
    update_stuck_ui(st, "student_dont_know")
    assert st.session_state.show_solution_button is True



def test_reset_session_and_start_new_problem():
    st = DummyStreamlit()
    reset_session(st)
    assert st.session_state.problem_text == ""
    assert st.session_state.chat_history == []
    assert st.session_state.pending_image is None
    assert st.session_state.hint_request_count == 0

    start_new_problem(st, "Một bài mới")
    assert st.session_state.problem_text == "Một bài mới"
    assert st.session_state.problem_confirmed is True
    assert st.session_state.chat_history == []



def test_should_require_full_presentation_and_update_retry():
    st = DummyStreamlit()
    st.session_state.presentation_retry_count = 0
    assert should_require_full_presentation(st, "54000") is True
    assert should_require_full_presentation(st, "24000 viên gạch") is False
    update_presentation_retry(st, True)
    assert st.session_state.presentation_retry_count == 1
    update_presentation_retry(st, False)
    assert st.session_state.presentation_retry_count == 0



def test_extract_named_distances_ignores_question_number():
    items = _extract_named_distances(GEOMETRY_TEXT)
    values = sorted(item["value"] for item in items)
    assert values == [25090, 35000, 42890, 45050]
    assert 4 not in values
    assert 1 not in values



def test_solve_geometry_farthest_maps_correct_choice():
    solved = _solve_geometry_farthest(GEOMETRY_TEXT)
    assert solved is not None
    assert solved["correct_value"] == 45050
    assert solved["correct_letter"] == "C"
    assert "Vườn hoa cúc" in solved["correct_name"]



def test_solve_circle_mcq_picks_center_option():
    solved = _solve_circle_mcq(CIRCLE_TEXT)
    assert solved is not None
    assert solved["correct_letter"] == "D"
    assert solved["correct_name"] == "O là tâm hình tròn"


STORE_TEXT = """
Một cửa hàng có 95 quyển vở. Người ta xếp đều vào 5 chồng, mỗi chồng lấy ra bán 7 quyển. Hỏi sau khi bán, cửa hàng còn lại bao nhiêu quyển vở?
"""

DOI_DON_VI_TEXT = """
Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?
"""


def test_build_micro_goals_for_doi_don_vi():
    goals = _build_micro_goals(DOI_DON_VI_TEXT)
    assert goals[0].lower().startswith("đổi")
    assert len(goals) >= 3


def test_infer_active_micro_goal_for_doi_don_vi_history():
    chat_history = [{"role": "assistant", "content": "Con đổi 3 m 25 cm ra 325 cm nhé.", "hidden": False}]
    goal = _infer_active_micro_goal(DOI_DON_VI_TEXT, chat_history)
    assert goal["index"] == 1


def test_solve_supported_problem_for_store_case():
    solved = _solve_supported_problem(STORE_TEXT)
    assert solved is not None
    assert solved["answer_value"] == 60
    assert "quyển vở" in solved["answer_text"]
