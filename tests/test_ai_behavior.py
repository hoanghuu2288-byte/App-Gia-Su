import os
import sys

# Cho pytest thấy thư mục gốc của repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_contracts import (
    PARENT_REQUIRED_SECTIONS,
    assert_child_response_contract,
    assert_parent_response_contract,
    validate_child_response,
    validate_parent_response,
)
from logic import build_followup_context, build_initial_context


PARENT_PROBLEM = (
    "Bác Hùng dự tính xây một ngôi nhà hết 78 000 viên gạch. "
    "Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. "
    "Hỏi theo dự tính, bác Hùng còn phải mua bao nhiêu viên gạch nữa?"
)

CHILD_PROBLEM = "36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?"


def test_parent_initial_context_contains_required_behavior_sections():
    context = build_initial_context(
        problem_text=PARENT_PROBLEM,
        mode="parent",
        support_level="goi_y",
    )

    for section in PARENT_REQUIRED_SECTIONS:
        assert section in context

    assert "TOÀN BÀI" in context
    assert "không được hỏi phụ huynh từng bước như mode trẻ" in context


def test_parent_followup_context_contains_required_behavior_sections():
    context = build_followup_context(
        problem_text=PARENT_PROBLEM,
        mode="parent",
        support_level="goi_y",
        chat_history=[{"role": "user", "content": "Con em bị bí ở đoạn nhân."}],
        current_step="start",
        last_error_type="",
        user_input="Con em bị bí ở đâu trước?",
        reply_type="normal_reply",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=2,
        is_finished=False,
    )

    for section in PARENT_REQUIRED_SECTIONS:
        assert section in context

    assert "ưu tiên giải thích TOÀN BÀI trong một lượt" in context
    assert "không hỏi phụ huynh từng bước như học sinh" in context


def test_child_initial_context_contains_short_and_one_question_rules():
    context = build_initial_context(
        problem_text=CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "tối đa 3 dòng ngắn + 1 câu hỏi" in context
    assert "không giảng dài dòng" in context


def test_child_followup_context_contains_short_and_one_question_rules():
    context = build_followup_context(
        problem_text=CHILD_PROBLEM,
        mode="child",
        support_level="tung_buoc",
        chat_history=[{"role": "assistant", "content": "Con thử chọn phép tính nhé."}],
        current_step="start",
        last_error_type="",
        user_input="con không biết",
        reply_type="student_dont_know",
        allow_full_solution=False,
        require_full_presentation=False,
        small_error=False,
        stuck_count=3,
        is_finished=False,
    )

    assert "tối đa 2 câu ngắn + 1 câu hỏi" in context
    assert "không được vòng vo nữa" in context
    assert "nói thẳng bước cần làm hoặc phép tính cần viết" in context


def test_parent_response_contract_accepts_expected_shape():
    response = """
Dạng bài: Bài toán có lời văn nhiều bước.

Kiến thức dùng: Phép nhân rồi phép trừ.

Hướng làm cả bài: Tính số gạch đã mua trước, rồi lấy số gạch dự tính cần có trừ số gạch đã mua.

Ba mẹ nên hỏi con:
- Đề bài hỏi gì?
- Con cần tính số gạch đã mua trước hay số còn thiếu trước?
""".strip()

    assert_parent_response_contract(response)


def test_parent_response_contract_rejects_missing_required_section():
    response = """
Dạng bài: Bài toán có lời văn nhiều bước.

Kiến thức dùng: Phép nhân rồi phép trừ.

Ba mẹ nên hỏi con:
- Đề bài hỏi gì?
- Con cần tính số nào trước?
""".strip()

    errors = validate_parent_response(response)

    assert errors
    assert "Hướng làm cả bài".lower() in " ".join(errors).lower()


def test_child_response_contract_accepts_short_reply_with_one_final_question():
    response = """
Đây là bài chia đều.
Con lấy 36 chia 6 trước nhé.
36 chia 6 bằng mấy?
""".strip()

    assert_child_response_contract(response)


def test_child_response_contract_rejects_multiple_questions():
    response = """
Con thấy đây là phép tính gì?
36 chia 6 bằng mấy?
""".strip()

    errors = validate_child_response(response)

    assert errors
    assert "exactly 1 question mark" in " ".join(errors)


def test_child_response_contract_rejects_question_not_at_end():
    response = """
36 chia 6 bằng mấy?
Con cứ tính thật chậm nhé.
""".strip()

    errors = validate_child_response(response)

    assert errors
    assert "final non-empty line" in " ".join(errors).lower()
