# tests/test_eval_catalog.py

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from eval_cases import get_eval_cases


def test_eval_catalog_has_enough_cases():
    cases = get_eval_cases()
    assert len(cases) >= 16


def test_eval_catalog_ids_are_unique():
    cases = get_eval_cases()
    ids = [case.id for case in cases]
    assert len(ids) == len(set(ids))


def test_eval_catalog_has_both_modes():
    cases = get_eval_cases()
    modes = {case.mode for case in cases}
    assert "child" in modes
    assert "parent" in modes


def test_eval_catalog_has_key_grade3_categories():
    cases = get_eval_cases()
    categories = {case.category for case in cases}

    expected = {
        "rut_ve_don_vi",
        "chia_deu",
        "doi_don_vi",
        "nhan_roi_tru",
        "chu_vi_hinh_vuong",
        "chu_vi_hinh_chu_nhat",
        "gap_len",
        "so_lien_truoc",
        "so_lien_sau",
        "tim_thanh_phan_chua_biet",
        "chuoi_thao_tac",
        "xin_dap_an_v2",
    }

    missing = expected - categories
    assert not missing, f"Thiếu category: {missing}"


def test_child_cases_require_strategy_opening():
    cases = [c for c in get_eval_cases() if c.mode == "child"]

    for case in cases:
        joined = " | ".join(case.opening_must_have)
        assert "Dạng bài" in joined
        assert "Kiến thức dùng" in joined
        assert "Cách nghĩ nhanh" in joined


def test_parent_cases_require_parent_structure():
    cases = [c for c in get_eval_cases() if c.mode == "parent"]

    for case in cases:
        joined = " | ".join(case.opening_must_have)
        assert "Dạng bài" in joined
        assert "Kiến thức dùng" in joined
        assert "Hướng làm cả bài" in joined
        assert "Ba mẹ nên hỏi con" in joined


def test_catalog_has_turn_checks():
    cases = get_eval_cases()
    assert any(case.turns for case in cases)


def test_catalog_has_multiple_behavior_patterns():
    cases = get_eval_cases()
    behavior_counts = Counter()

    for case in cases:
        for turn in case.turns:
            if turn.user == "__HINT__":
                behavior_counts["hint_flow"] += 1
            if "đáp án" in turn.user:
                behavior_counts["ask_answer"] += 1
            if turn.user.isdigit():
                behavior_counts["number_only"] += 1

    assert behavior_counts["hint_flow"] >= 6
    assert behavior_counts["ask_answer"] >= 1
    assert behavior_counts["number_only"] >= 6


def test_all_cases_have_reasonable_pass_ratio():
    cases = get_eval_cases()
    for case in cases:
        assert 0.5 <= case.min_pass_ratio <= 1.0
