import os
import sys

# Cho pytest thấy thư mục gốc của repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic import build_followup_context, build_initial_context


EASY_CHILD_PROBLEM = "36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?"
UNIT_CHILD_PROBLEM = "Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?"


def test_child_initial_easy_context_requires_short_opening():
    context = build_initial_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "Nếu mode là child:" in context
    assert "Nếu bài easy:" in context
    assert "mở đầu rất ngắn" in context
    assert "tối đa 3 dòng ngắn + 1 câu hỏi" in context
    assert "không giảng dài dòng" in context


def test_child_initial_context_reminds_unit_conversion_when_needed():
    context = build_initial_context(
        problem_text=UNIT_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "Nếu bài có dấu hiệu khác đơn vị, phải nhắc chú ý đổi về cùng đơn vị" in context


def test_child_followup_dont_know_first_time_keeps_light_hint():
    context = build_followup_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
        chat_history=[{"role": "assistant", "content": "Con xem đây là bài gì nhé."}],
        current_step="start",
        last_error_type="khong_biet",
        user_input="con không biết",
        reply_type="student_dont_know",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=1,
        is_finished=False,
    )

    assert "stuck_count hiện tại là: 1" in context
    assert "stuck_count = 1: gợi ý nhẹ" in context
    assert "tối đa 2 câu ngắn + 1 câu hỏi" in context


def test_child_followup_dont_know_second_time_requires_clearer_hint():
    context = build_followup_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
        chat_history=[{"role": "assistant", "content": "Con xem đây là bài gì nhé."}],
        current_step="start",
        last_error_type="khong_biet",
        user_input="con vẫn không biết",
        reply_type="student_dont_know",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=2,
        is_finished=False,
    )

    assert "stuck_count hiện tại là: 2" in context
    assert "stuck_count = 2: gợi ý rõ hơn, nêu số cần dùng hoặc nêu chọn phép tính" in context


def test_child_followup_dont_know_third_time_must_stop_being_vague():
    context = build_followup_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
        chat_history=[{"role": "assistant", "content": "Con xem đây là bài gì nhé."}],
        current_step="start",
        last_error_type="khong_biet",
        user_input="con không biết thật",
        reply_type="student_dont_know",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=3,
        is_finished=False,
    )

    assert "stuck_count hiện tại là: 3" in context
    assert "không được vòng vo nữa" in context
    assert "nói thẳng bước cần làm hoặc phép tính cần viết" in context


def test_child_followup_asks_answer_but_not_allowed_yet():
    context = build_followup_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
        chat_history=[{"role": "assistant", "content": "Con thử nghĩ xem nên dùng phép tính gì nhé."}],
        current_step="start",
        last_error_type="xin_dap_an",
        user_input="cho con đáp án",
        reply_type="student_asks_answer",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=1,
        is_finished=False,
    )

    assert "Nếu reply_type là student_asks_answer mà chưa được phép giải đầy đủ:" in context
    assert "child: từ chối nhẹ nhàng trước, rồi tăng hỗ trợ nếu bí nhiều lần" in context


def test_child_followup_number_only_keeps_reply_short():
    context = build_followup_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="tung_buoc",
        chat_history=[{"role": "assistant", "content": "Con thử tính 36 chia 6 nhé."}],
        current_step="step_1",
        last_error_type="chi_1_con_so",
        user_input="6",
        reply_type="student_number_only",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=True,
        stuck_count=0,
        is_finished=False,
    )

    assert "Nếu reply_type là student_number_only:" in context
    assert "chỉ nhắc viết rõ hơn thật ngắn" in context
    assert "Không được giữ học sinh quá lâu ở việc viết lại phép tính hoặc đơn vị nếu con đã hiểu ý chính." in context


def test_child_followup_finished_response_stops_extra_help():
    context = build_followup_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
        chat_history=[
            {"role": "assistant", "content": "Con thử tính 36 chia 6 nhé."},
            {"role": "user", "content": "6"},
        ],
        current_step="done",
        last_error_type="",
        user_input="con làm xong rồi",
        reply_type="normal_reply",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=0,
        is_finished=True,
    )

    assert "Bài đã hoàn tất. Không hỏi hỗ trợ thêm. Chỉ chốt ngắn gọn nếu cần." in context
