from __future__ import annotations


PARENT_REQUIRED_SECTIONS = (
    "Dạng bài",
    "Kiến thức dùng",
    "Hướng làm cả bài",
    "Ba mẹ nên hỏi con",
)

DEFAULT_CHILD_MAX_NONEMPTY_LINES = 4
DEFAULT_CHILD_MAX_CHARS = 280


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\r", "\n").split()).lower()


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]


def missing_parent_sections(
    text: str,
    required_sections: tuple[str, ...] = PARENT_REQUIRED_SECTIONS,
) -> list[str]:
    normalized = _normalize_text(text)
    return [section for section in required_sections if section.lower() not in normalized]


def validate_parent_response(
    text: str,
    required_sections: tuple[str, ...] = PARENT_REQUIRED_SECTIONS,
) -> list[str]:
    errors: list[str] = []

    if not text or not text.strip():
        return ["Parent response is empty."]

    missing = missing_parent_sections(text, required_sections=required_sections)
    if missing:
        errors.append("Missing required parent sections: " + ", ".join(missing))

    return errors


def validate_child_response(
    text: str,
    *,
    max_nonempty_lines: int = DEFAULT_CHILD_MAX_NONEMPTY_LINES,
    max_chars: int = DEFAULT_CHILD_MAX_CHARS,
) -> list[str]:
    errors: list[str] = []

    if not text or not text.strip():
        return ["Child response is empty."]

    stripped = text.strip()
    lines = _nonempty_lines(text)
    question_count = stripped.count("?")

    if len(stripped) > max_chars:
        errors.append(
            f"Child response is too long: {len(stripped)} chars > {max_chars} chars."
        )

    if len(lines) > max_nonempty_lines:
        errors.append(
            f"Child response has too many non-empty lines: {len(lines)} > {max_nonempty_lines}."
        )

    if question_count != 1:
        errors.append(
            f"Child response must contain exactly 1 question mark, got {question_count}."
        )

    if lines and not lines[-1].endswith("?"):
        errors.append("Final non-empty line must be the only question.")

    return errors


def assert_parent_response_contract(text: str) -> None:
    errors = validate_parent_response(text)
    assert not errors, " | ".join(errors)


def assert_child_response_contract(
    text: str,
    *,
    max_nonempty_lines: int = DEFAULT_CHILD_MAX_NONEMPTY_LINES,
    max_chars: int = DEFAULT_CHILD_MAX_CHARS,
) -> None:
    errors = validate_child_response(
        text,
        max_nonempty_lines=max_nonempty_lines,
        max_chars=max_chars,
    )
    assert not errors, " | ".join(errors)
