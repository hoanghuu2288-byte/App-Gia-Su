import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic import build_initial_context


EASY_CHILD_PROBLEM = "36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?"
MEDIUM_CHILD_PROBLEM = "Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?"


def test_child_initial_easy_context_requires_short_opening():
    context = build_initial_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "Nếu mode là child:" in context
    assert "Mức độ bài:" in context
    assert "easy" in context
    assert "tối đa 4 dòng ngắn + 1 câu hỏi" in context
    assert "Dạng bài" in context
    assert "Kiến thức dùng" in context
    assert "Cách nghĩ nhanh" in context


def test_child_initial_medium_context_mentions_unit_attention():
    context = build_initial_context(
        problem_text=MEDIUM_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "Đổi đơn vị rồi tính" in context or "đổi về cùng đơn vị" in context
    assert "Nếu bài có dấu hiệu khác đơn vị, phải nhắc chú ý đổi về cùng đơn vị" in context
