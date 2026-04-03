import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic import build_initial_context


CHILD_PROBLEM = "Có 6 hộp bút như nhau đựng tất cả 48 chiếc bút. Hỏi 9 hộp như thế đựng bao nhiêu chiếc bút?"


def test_child_initial_context_contains_child_teaching_rules():
    context = build_initial_context(
        problem_text=CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "Nếu mode là child:" in context
    assert "Dạng bài" in context
    assert "Kiến thức dùng" in context
    assert "Cách nghĩ nhanh" in context
    assert "tối đa 4 dòng ngắn + 1 câu hỏi" in context
    assert "không viết thêm các câu xã giao" in context
