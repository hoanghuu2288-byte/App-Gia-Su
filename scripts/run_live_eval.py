# scripts/run_live_eval.py

import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import List

import google.generativeai as genai

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval_cases import EvalCase, TurnSpec, get_eval_cases
from prompts import get_system_prompt
from logic import (
    build_initial_context,
    build_followup_context,
    classify_user_reply,
    update_step_and_error,
    update_presentation_retry,
    looks_like_new_problem,
    should_require_full_presentation,
    is_small_error,
    update_stuck_ui,
    detect_finished_response,
)


@dataclass
class EvalResult:
    case_id: str
    mode: str
    category: str
    passed: bool
    score: int
    max_score: int
    pass_ratio: float
    failed_checks: List[str]
    opening_response: str
    final_response: str


class DummyStreamlit:
    def __init__(self, support_level: str = "goi_y"):
        self.session_state = SimpleNamespace(
            presentation_retry_count=0,
            stuck_count=0,
            show_help_buttons=False,
            show_hint_button=False,
            show_solution_button=False,
            is_finished=False,
            last_error_type="",
            allow_full_solution=(support_level == "cach_giai"),
            current_step="start",
        )


def configure_gemini_from_env():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu GEMINI_API_KEY trong GitHub Secret.")
    genai.configure(api_key=api_key)


def call_model(system_prompt: str, user_input: str, model_name: str) -> str:
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_input)
    return getattr(response, "text", "") or ""


def get_child_help_response_settings(st):
    if st.session_state.allow_full_solution:
        return "cach_giai", True

    if st.session_state.stuck_count >= 4:
        return "cach_giai", True

    if st.session_state.stuck_count >= 2:
        return "tung_buoc", False

    return "goi_y", False


def has_all(text: str, items: List[str]):
    missing = [item for item in items if item not in text]
    return len(missing) == 0, missing


def has_none(text: str, items: List[str]):
    found = [item for item in items if item in text]
    return len(found) == 0, found


def score_block(label: str, text: str, must_have: List[str], must_not_have: List[str], failed_checks: List[str]):
    score = 0
    max_score = 0

    for item in must_have:
        max_score += 1
        if item in text:
            score += 1
        else:
            failed_checks.append(f"{label} thiếu: {item}")

    for item in must_not_have:
        max_score += 1
        if item not in text:
            score += 1
        else:
            failed_checks.append(f"{label} có cụm không mong muốn: {item}")

    return score, max_score


def run_case(case: EvalCase, model_name: str) -> EvalResult:
    st = DummyStreamlit(support_level=case.support_level)
    system_prompt = get_system_prompt(case.mode)

    failed_checks: List[str] = []
    total_score = 0
    total_max = 0

    opening_context = build_initial_context(
        problem_text=case.problem,
        mode=case.mode,
        support_level=case.support_level,
    )
    opening_response = call_model(system_prompt, opening_context, model_name=model_name)

    score, max_score = score_block(
        label="opening",
        text=opening_response,
        must_have=case.opening_must_have,
        must_not_have=case.opening_must_not_have,
        failed_checks=failed_checks,
    )
    total_score += score
    total_max += max_score

    chat_history = [{"role": "assistant", "content": opening_response}]
    st.session_state.is_finished = detect_finished_response(opening_response)
    last_response = opening_response

    for idx, turn in enumerate(case.turns, start=1):
        if st.session_state.is_finished:
            break

        if turn.user == "__HINT__":
            user_reply = "con cần gợi ý thêm"
            reply_type = "student_dont_know"

            update_step_and_error(st, reply_type)
            update_stuck_ui(st, reply_type)

            support_level_for_response, allow_full_solution_for_response = get_child_help_response_settings(st)

            require_full_presentation = False
            small_error = False
            update_presentation_retry(st, require_full_presentation)

            followup_context = build_followup_context(
                problem_text=case.problem,
                mode=case.mode,
                support_level=support_level_for_response,
                chat_history=chat_history,
                current_step=st.session_state.current_step,
                last_error_type=st.session_state.last_error_type,
                user_input=user_reply,
                reply_type=reply_type,
                allow_full_solution=allow_full_solution_for_response,
                require_full_presentation=require_full_presentation,
                small_error=small_error,
                stuck_count=st.session_state.stuck_count,
                is_finished=st.session_state.is_finished,
            )
        else:
            if looks_like_new_problem(turn.user):
                failed_checks.append(f"turn {idx} bị hiểu như bài mới giữa chừng")
                break

            chat_history.append({"role": "user", "content": turn.user})

            reply_type = classify_user_reply(turn.user)
            update_step_and_error(st, reply_type)
            update_stuck_ui(st, reply_type)

            require_full_presentation = should_require_full_presentation(st, turn.user)
            update_presentation_retry(st, require_full_presentation)
            small_error = is_small_error(turn.user)

            followup_context = build_followup_context(
                problem_text=case.problem,
                mode=case.mode,
                support_level=case.support_level,
                chat_history=chat_history,
                current_step=st.session_state.current_step,
                last_error_type=st.session_state.last_error_type,
                user_input=turn.user,
                reply_type=reply_type,
                allow_full_solution=st.session_state.allow_full_solution,
                require_full_presentation=require_full_presentation,
                small_error=small_error,
                stuck_count=st.session_state.stuck_count,
                is_finished=st.session_state.is_finished,
            )

        last_response = call_model(system_prompt, followup_context, model_name=model_name)
        chat_history.append({"role": "assistant", "content": last_response})
        st.session_state.is_finished = detect_finished_response(last_response)

        score, max_score = score_block(
            label=f"turn_{idx}",
            text=last_response,
            must_have=turn.must_have,
            must_not_have=turn.must_not_have,
            failed_checks=failed_checks,
        )
        total_score += score
        total_max += max_score

    all_assistant_text = "\n".join(
        msg["content"] for msg in chat_history if msg["role"] == "assistant"
    )

    score, max_score = score_block(
        label="transcript",
        text=all_assistant_text,
        must_have=case.transcript_must_have,
        must_not_have=case.transcript_must_not_have,
        failed_checks=failed_checks,
    )
    total_score += score
    total_max += max_score

    score, max_score = score_block(
        label="final",
        text=all_assistant_text,
        must_have=case.final_must_have,
        must_not_have=case.final_must_not_have,
        failed_checks=failed_checks,
    )
    total_score += score
    total_max += max_score

    pass_ratio = (total_score / total_max) if total_max else 1.0
    passed = pass_ratio >= case.min_pass_ratio

    return EvalResult(
        case_id=case.id,
        mode=case.mode,
        category=case.category,
        passed=passed,
        score=total_score,
        max_score=total_max,
        pass_ratio=pass_ratio,
        failed_checks=failed_checks,
        opening_response=opening_response,
        final_response=last_response,
    )


def write_csv(results: List[EvalResult], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "case_id",
                "mode",
                "category",
                "passed",
                "score",
                "max_score",
                "pass_ratio",
                "failed_checks",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.case_id,
                    r.mode,
                    r.category,
                    "PASS" if r.passed else "FAIL",
                    r.score,
                    r.max_score,
                    f"{r.pass_ratio:.2f}",
                    " | ".join(r.failed_checks),
                ]
            )


def write_markdown(results: List[EvalResult], output_path: Path, model_name: str):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    by_mode = {}
    by_category = {}
    for r in results:
        by_mode.setdefault(r.mode, []).append(r)
        by_category.setdefault(r.category, []).append(r)

    lines = [
        "# Live Eval Report V2",
        "",
        f"- Model: **{model_name}**",
        f"- Time: **{datetime.now().isoformat(timespec='seconds')}**",
        f"- Passed: **{passed}/{total}**",
        "",
        "## Tổng hợp theo mode",
        "",
    ]

    for mode, items in by_mode.items():
        mode_pass = sum(1 for r in items if r.passed)
        lines.append(f"- **{mode}**: {mode_pass}/{len(items)}")
    lines.append("")
    lines.append("## Tổng hợp theo category")
    lines.append("")
    for category, items in sorted(by_category.items()):
        cat_pass = sum(1 for r in items if r.passed)
        lines.append(f"- **{category}**: {cat_pass}/{len(items)}")
    lines.append("")
    lines.append("## Chi tiết từng case")
    lines.append("")

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        lines.append(f"### {status} — {r.case_id}")
        lines.append(f"- Mode: `{r.mode}`")
        lines.append(f"- Category: `{r.category}`")
        lines.append(f"- Score: `{r.score}/{r.max_score}`")
        lines.append(f"- Pass ratio: `{r.pass_ratio:.2f}`")
        if r.failed_checks:
            lines.append("- Failed checks:")
            for item in r.failed_checks:
                lines.append(f"  - {item}")
        lines.append("")
        lines.append("**Opening response**")
        lines.append("")
        lines.append(r.opening_response)
        lines.append("")
        lines.append("**Last response**")
        lines.append("")
        lines.append(r.final_response)
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    configure_gemini_from_env()

    model_name = os.getenv("EVAL_MODEL_NAME", "gemini-2.5-pro")
    cases = get_eval_cases()
    results = []

    for idx, case in enumerate(cases, start=1):
        print(f"[{idx}/{len(cases)}] Running {case.id} ...")
        result = run_case(case, model_name=model_name)
        results.append(result)
        print(f"    -> {'PASS' if result.passed else 'FAIL'} ({result.score}/{result.max_score}, ratio={result.pass_ratio:.2f})")

    outdir = Path("eval_reports")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = outdir / f"live_eval_v2_{timestamp}.csv"
    md_path = outdir / f"live_eval_v2_{timestamp}.md"

    write_csv(results, csv_path)
    write_markdown(results, md_path, model_name=model_name)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print()
    print("=" * 60)
    print(f"Done. Passed {passed}/{total}")
    print(f"CSV report: {csv_path}")
    print(f"MD  report: {md_path}")
    print("=" * 60)

    if passed < total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
