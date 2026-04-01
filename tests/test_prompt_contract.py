import os
import sys

# Cho pytest thấy thư mục gốc của repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from prompts import (
    CHILD_SYSTEM_PROMPT,
    FIRST_RESPONSE_GUIDE,
    PARENT_SYSTEM_PROMPT,
)


def test_parent_prompt_contains_required_sections():
    source = "\n".join([PARENT_SYSTEM_PROMPT, FIRST_RESPONSE_GUIDE])

    required_markers = (
        "Dạng bài",
        "Kiến thức dùng",
        "Hướng làm cả bài",
        "Ba mẹ nên hỏi con",
    )

    missing = [marker for marker in required_markers if marker not in source]
    assert not missing, f"Parent prompt is missing markers: {missing}"


def test_parent_prompt_keeps_whole_problem_direction():
    source = "\n".join([PARENT_SYSTEM_PROMPT, FIRST_RESPONSE_GUIDE]).lower()

    assert "toàn bài" in source
    assert "không hỏi phụ huynh từng bước như học sinh" in source or "không hỏi từng bước" in source


def test_child_prompt_mentions_shortness_rule():
    source = "\n".join([CHILD_SYSTEM_PROMPT, FIRST_RESPONSE_GUIDE]).lower()

    short_markers = (
        "mỗi lượt tối đa 2 câu ngắn + 1 câu hỏi.",
        "câu ngắn, dễ hiểu",
        "không viết thành đoạn văn dài",
    )

    for marker in short_markers:
        assert marker in source


def test_child_prompt_mentions_exactly_one_question_rule():
    source = "\n".join([CHILD_SYSTEM_PROMPT, FIRST_RESPONSE_GUIDE]).lower()

    markers = (
        "1 câu hỏi",
        "đúng 1 câu hỏi",
        "rồi hỏi ngay 1 câu hành động",
        "rồi kết thúc bằng đúng 1 câu hỏi",
    )

    assert any(marker in source for marker in markers), (
        "Child prompt should explicitly require one question."
    )
