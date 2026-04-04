# scripts/run_live_eval.py

import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval_cases import EvalCase, get_eval_cases
from logic import (
    classify_user_reply,
    detect_finished_response,
    generate_followup_tutoring_response,
    generate_opening_tutoring_response,
    is_small_error,
    looks_like_new_problem,
    should_require_full_presentation,
    update_presentation_retry,
    update_step_and_error,
    update_stuck_ui,
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


def get_child_help_response_settings(st):
    if st.session_state.allow_full_solution:
        return "cach_giai", True
    if st.session_state.stuck_count >= 4:
        return "cach_giai", True
    if st.session_state.stuck_count >= 2:
        return "tung_buoc", False
    return "goi_y", False



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



def run_case(case: EvalCase) -> EvalResult:
    st = DummyStreamlit(support_level=case.support_level)

    failed_checks: List[str] = []
    total_score = 0
    total_max = 0

    opening_response = generate_opening_tutoring_response(
        problem_text=case.problem,
        mode=case.mode,
        support_level=case.support_level,
    )

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
    hint_request_count = 0

    for idx, turn in enumerate(case.turns, start=1):
        if st.session_state.is_finished:
            break

        if turn.user == "__HINT__":
            user_reply = "Con cần một gợi ý ngắn."
            reply_type = "student_dont_know"
            hint_request_count += 1

            update_step_and_error(st, reply_type)
            update_stuck_ui(st, reply_type)
            support_level_for_response, allow_full_solution_for_response = get_child_help_response_settings(st)

            require_full_presentation = False
            small_error = False
            update_presentation_retry(st, require_full_presentation)
        else:
            if looks_like_new_problem(turn.user):
                failed_checks.append(f"turn {idx} bị hiểu như bài mới giữa chừng")
                break

            chat_history.append({"role": "user", "content": turn.user})
            user_reply = turn.user
            reply_type = classify_user_reply(turn.user)
            update_step_and_error(st, reply_type)
            update_stuck_ui(st, reply_type)
            support_level_for_response = case.support_level
            allow_full_solution_for_response = st.session_state.allow_full_solution
            require_full_presentation = should_require_full_presentation(st, turn.user)
            update_presentation_retry(st, require_full_presentation)
            small_error = is_small_error(turn.user)

        last_response = generate_followup_tutoring_response(
            problem_text=case.problem,
            mode=case.mode,
            support_level=support_level_for_response,
            chat_history=chat_history,
            user_input=user_reply,
            reply_type=reply_type,
            allow_full_solution=allow_full_solution_for_response,
            require_full_presentation=require_full_presentation,
            small_error=small_error,
            stuck_count=st.session_state.stuck_count,
            is_finished=st.session_state.is_finished,
            hint_request_count=hint_request_count,
        )
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

    all_assistant_text = "\n".join(msg["content"] for msg in chat_history if msg["role"] == "assistant")

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



def main():
    model_name = os.getenv("OPENAI_TEXT_MODEL", "gpt-5.4-mini")
    results = [run_case(case) for case in get_eval_cases()]

    output_dir = ROOT / "artifacts"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = output_dir / f"live_eval_{timestamp}.csv"
    md_path = output_dir / f"live_eval_{timestamp}.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_id", "mode", "category", "passed", "score", "max_score", "pass_ratio", "failed_checks"
        ])
        for r in results:
            writer.writerow([
                r.case_id,
                r.mode,
                r.category,
                r.passed,
                r.score,
                r.max_score,
                f"{r.pass_ratio:.2f}",
                " | ".join(r.failed_checks),
            ])

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    by_mode = {}
    by_category = {}
    for r in results:
        by_mode.setdefault(r.mode, [0, 0])
        by_mode[r.mode][1] += 1
        by_mode[r.mode][0] += int(r.passed)
        by_category.setdefault(r.category, [0, 0])
        by_category[r.category][1] += 1
        by_category[r.category][0] += int(r.passed)

    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Live Eval Report V2\n\n")
        f.write(f"- Model: **{model_name}**\n")
        f.write(f"- Time: **{datetime.now().isoformat(timespec='seconds')}**\n")
        f.write(f"- Passed: **{passed_count}/{total_count}**\n\n")

        f.write("## Tổng hợp theo mode\n\n")
        for mode, (passed, total) in by_mode.items():
            f.write(f"- **{mode}**: {passed}/{total}\n")
        f.write("\n## Tổng hợp theo category\n\n")
        for cat, (passed, total) in sorted(by_category.items()):
            f.write(f"- **{cat}**: {passed}/{total}\n")

        f.write("\n## Chi tiết từng case\n\n")
        for r in results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            f.write(f"### {status} — {r.case_id}\n")
            f.write(f"- Mode: `{r.mode}`\n")
            f.write(f"- Category: `{r.category}`\n")
            f.write(f"- Score: `{r.score}/{r.max_score}`\n")
            f.write(f"- Pass ratio: `{r.pass_ratio:.2f}`\n")
            if r.failed_checks:
                f.write("- Failed checks:\n")
                for item in r.failed_checks:
                    f.write(f"  - {item}\n")
            f.write("\n**Opening response**\n\n")
            f.write(f"{r.opening_response}\n\n")
            f.write("**Last response**\n\n")
            f.write(f"{r.final_response}\n\n---\n\n")

    print(f"Saved CSV report to: {csv_path}")
    print(f"Saved Markdown report to: {md_path}")
    print(f"Passed: {passed_count}/{total_count}")

    if passed_count < total_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
