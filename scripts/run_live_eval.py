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

from eval_cases import EvalCase, get_eval_cases
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
    checks_passed: int
    checks_total: int
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


def contains_all(text: str, needles: List[str]):
    missing = [item for item in needles if item not in text]
    return len(missing) == 0, missing


def contains_none(text: str, needles: List[str]):
    found = [item for item in needles if item in text]
    return len(found) == 0, found


def run_case(case: EvalCase, model_name: str) -> EvalResult:
    st = DummyStreamlit(support_level=case.support_level)
    system_prompt = get_system_prompt(case.mode)

    opening_context = build_initial_context(
        problem_text=case.problem,
        mode=case.mode,
        support_level=case.support_level,
    )
    opening_response = call_model(system_prompt, opening_context, model_name=model_name)

    chat_history = [{"role": "assistant", "content": opening_response}]
    st.session_state.is_finished = detect_finished_response(opening_response)

    failed_checks = []
    checks_total = 0
    checks_passed = 0

    checks_total += 1
    ok, missing = contains_all(opening_response, case.opening_must_have)
    if ok:
        checks_passed += 1
    else:
        failed_checks.append(f"opening thiếu: {missing}")

    checks_total += 1
    ok, found = contains_none(opening_response, case.opening_must_not_have)
    if ok:
        checks_passed += 1
    else:
        failed_checks.append(f"opening có cụm không mong muốn: {found}")

    last_response = opening_response

    for turn in case.student_turns:
        if st.session_state.is_finished:
            break

        if turn == "__HINT__":
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

            last_response = call_model(system_prompt, followup_context, model_name=model_name)
            chat_history.append({"role": "assistant", "content": last_response})
            st.session_state.is_finished = detect_finished_response(last_response)
            continue

        if looks_like_new_problem(turn):
            failed_checks.append("case bị hiểu như bài mới giữa chừng")
            break

        chat_history.append({"role": "user", "content": turn})

        reply_type = classify_user_reply(turn)
        update_step_and_error(st, reply_type)
        update_stuck_ui(st, reply_type)

        require_full_presentation = should_require_full_presentation(st, turn)
        update_presentation_retry(st, require_full_presentation)
        small_error = is_small_error(turn)

        followup_context = build_followup_context(
            problem_text=case.problem,
            mode=case.mode,
            support_level=case.support_level,
            chat_history=chat_history,
            current_step=st.session_state.current_step,
            last_error_type=st.session_state.last_error_type,
            user_input=turn,
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

    all_assistant_text = "\n".join(
        msg["content"] for msg in chat_history if msg["role"] == "assistant"
    )

    checks_total += 1
    ok, missing = contains_all(all_assistant_text, case.final_must_have)
    if ok:
        checks_passed += 1
    else:
        failed_checks.append(f"final thiếu: {missing}")

    checks_total += 1
    ok, found = contains_none(all_assistant_text, case.final_must_not_have)
    if ok:
        checks_passed += 1
    else:
        failed_checks.append(f"final có cụm không mong muốn: {found}")

    passed = len(failed_checks) == 0

    return EvalResult(
        case_id=case.id,
        mode=case.mode,
        category=case.category,
        passed=passed,
        checks_passed=checks_passed,
        checks_total=checks_total,
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
                "checks_passed",
                "checks_total",
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
                    r.checks_passed,
                    r.checks_total,
                    " | ".join(r.failed_checks),
                ]
            )


def write_markdown(results: List[EvalResult], output_path: Path, model_name: str):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    lines = [
        "# Live Eval Report",
        "",
        f"- Model: **{model_name}**",
        f"- Time: **{datetime.now().isoformat(timespec='seconds')}**",
        f"- Passed: **{passed}/{total}**",
        "",
        "## Kết quả theo case",
        "",
    ]

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        lines.append(f"### {status} — {r.case_id}")
        lines.append(f"- Mode: `{r.mode}`")
        lines.append(f"- Category: `{r.category}`")
        lines.append(f"- Checks: `{r.checks_passed}/{r.checks_total}`")
        if r.failed_checks:
            lines.append(f"- Failed checks: {', '.join(r.failed_checks)}")
        lines.append("")
        lines.append("**Opening response**")
        lines.append("")
        lines.append(r.opening_response)
        lines.append("")
        lines.append("**Final response**")
        lines.append("")
        lines.append(r.final_response)
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    configure_gemini_from_env()

    model_name = "gemini-2.5-pro"
    cases = get_eval_cases()
    results = []

    for idx, case in enumerate(cases, start=1):
        print(f"[{idx}/{len(cases)}] Running {case.id} ...")
        result = run_case(case, model_name=model_name)
        results.append(result)
        print(f"    -> {'PASS' if result.passed else 'FAIL'}")

    outdir = Path("eval_reports")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = outdir / f"live_eval_{timestamp}.csv"
    md_path = outdir / f"live_eval_{timestamp}.md"

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
