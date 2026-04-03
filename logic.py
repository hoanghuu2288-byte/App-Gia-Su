def classify_user_reply(user_input: str) -> str:
    raw_text = user_input.strip()
    if not raw_text:
        return "empty"

    text = raw_text.lower()
    normalized = _normalize_for_matching(raw_text)
    compact = normalized.replace(" ", "")

    exact_dont_know = {
        "khong",
        "ko",
        "k",
        "khongbiet",
        "khongbieet",
        "kobiet",
        "kbiet",
        "khonghieu",
        "kohieu",
        "chuabiet",
        "chuabieet",
    }
    dont_know_signals = [
        "khong biet",
        "ko biet",
        "k biet",
        "con khong biet",
        "con ko biet",
        "khong hieu",
        "ko hieu",
        "khong ro",
        "la sao",
        "kho qua",
        "con bi",
        "bi qua",
        "khong lam duoc",
        "ko lam duoc",
        "khong biet lam",
        "khong biet nua",
        "khong biet that",
        "van khong biet",
        "chua biet",
        "chua biet nua",
        "chua hieu",
        "khong biey",
    ]

    if normalized in exact_dont_know or compact in exact_dont_know:
        return "student_dont_know"

    if any(signal in normalized for signal in dont_know_signals):
        return "student_dont_know"

    ask_answer_signals_normalized = [
        "dap an",
        "giai luon",
        "cho con dap an",
        "cho dap an",
        "giai ho",
        "lam ho",
        "cho con ket qua",
        "noi dap an",
        "cho con loi giai",
        "cho con xem dap an",
    ]
    ask_answer_signals_raw = [
        "đáp án",
        "giải luôn",
        "cho con đáp án",
        "cho đáp án",
        "giải hộ",
        "làm hộ",
        "cho con kết quả",
        "nói đáp án",
        "cho con lời giải",
        "cho con xem đáp án",
    ]

    if any(signal in normalized for signal in ask_answer_signals_normalized):
        return "student_asks_answer"

    if any(signal in text for signal in ask_answer_signals_raw):
        return "student_asks_answer"

    cleaned = re.sub(r"[\s,\.]", "", text)
    if cleaned.isdigit():
        return "student_number_only"

    return "normal_reply"
