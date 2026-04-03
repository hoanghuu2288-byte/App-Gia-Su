def test_child_initial_context_contains_short_and_one_question_rules():
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
