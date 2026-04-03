def test_child_initial_easy_context_requires_short_opening():
    context = build_initial_context(
        problem_text=EASY_CHILD_PROBLEM,
        mode="child",
        support_level="goi_y",
    )

    assert "Nếu mode là child:" in context
    assert "Nếu bài easy:" in context
    assert (
        "khung này phải rất ngắn" in context
        or "ưu tiên mở đầu gọn" in context
        or "tối đa 4 dòng ngắn + 1 câu hỏi" in context
    )
