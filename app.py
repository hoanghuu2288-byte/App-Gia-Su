import streamlit as st
from PIL import Image

from prompts import get_system_prompt
from gemini_client import (
    generate_text_response,
    generate_multimodal_response,
)
from logic import (
    init_app_state,
    reset_session,
    build_initial_context,
    classify_user_reply,
    build_followup_context,
    update_step_and_error,
    update_presentation_retry,
    build_summary_context,
    looks_like_new_problem,
    start_new_problem,
    should_require_full_presentation,
    is_small_error,
    update_stuck_ui,
    detect_finished_response,
)

st.set_page_config(
    page_title="Trợ lý học Toán lớp 3",
    page_icon="🎓",
    layout="centered"
)

init_app_state(st)


def reset_learning_flow():
    st.session_state.chat_history = []
    st.session_state.summary = ""
    st.session_state.presentation_retry_count = 0
    st.session_state.stuck_count = 0
    st.session_state.show_help_buttons = False
    st.session_state.show_hint_button = False
    st.session_state.show_solution_button = False
    st.session_state.is_finished = False
    st.session_state.current_step = "start"
    st.session_state.last_error_type = ""


def start_problem_session():
    reset_learning_flow()

    initial_context = build_initial_context(
        problem_text=st.session_state.problem_text,
        mode=st.session_state.mode,
        support_level=st.session_state.support_level
    )

    response = generate_text_response(
        system_prompt=get_system_prompt(st.session_state.mode),
        user_input=initial_context
    )

    st.session_state.is_finished = detect_finished_response(response)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response
    })


def run_followup_turn(
    user_reply: str,
    *,
    reply_type_override: str | None = None,
    support_level_override: str | None = None,
    allow_full_solution_override: bool | None = None,
    append_user_message: bool = True,
):
    if append_user_message:
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_reply
        })

    reply_type = reply_type_override or classify_user_reply(user_reply)

    update_step_and_error(st, reply_type)
    update_stuck_ui(st, reply_type)

    if reply_type_override == "student_dont_know":
        require_full_presentation = False
        small_error = False
    else:
        require_full_presentation = should_require_full_presentation(st, user_reply)
        small_error = is_small_error(user_reply)

    update_presentation_retry(st, require_full_presentation)

    support_level_for_response = support_level_override or st.session_state.support_level
    allow_full_solution_for_response = (
        st.session_state.allow_full_solution
        if allow_full_solution_override is None
        else allow_full_solution_override
    )

    followup_context = build_followup_context(
        problem_text=st.session_state.problem_text,
        mode=st.session_state.mode,
        support_level=support_level_for_response,
        chat_history=st.session_state.chat_history,
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

    response = generate_text_response(
        system_prompt=get_system_prompt(st.session_state.mode),
        user_input=followup_context
    )

    st.session_state.is_finished = detect_finished_response(response)
    if st.session_state.is_finished:
        st.session_state.show_help_buttons = False
        st.session_state.show_hint_button = False
        st.session_state.show_solution_button = False

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response
    })


def get_child_help_response_settings():
    if st.session_state.support_level == "cach_giai":
        return "cach_giai", True

    if st.session_state.stuck_count >= 4:
        return "cach_giai", True

    if st.session_state.support_level == "tung_buoc" or st.session_state.stuck_count >= 2:
        return "tung_buoc", False

    return "goi_y", False


# =========================
# 1. CỔNG MỞ KHÓA ĐƠN GIẢN
# =========================
if "dang_nhap_thanh_cong" not in st.session_state:
    st.session_state.dang_nhap_thanh_cong = False

if not st.session_state.dang_nhap_thanh_cong:
    st.title("🔒 Cổng Đăng Nhập Gia Sư AI")
    st.info("Chào ba mẹ! Vui lòng nhập mã bản quyền để kích hoạt trợ lý học Toán cho con nhé.")

    mat_khau = st.text_input("Nhập mã bản quyền:", type="password")

    if st.button("Mở Khóa 🚀"):
        if mat_khau == "vip123":
            st.session_state.dang_nhap_thanh_cong = True
            st.rerun()
        else:
            st.error("Mã bản quyền không chính xác!")

else:
    st.title("🎓 Trợ lý học Toán lớp 3 cho phụ huynh bận rộn")

    col_left, col_right = st.columns([4, 1])
    with col_right:
        if st.button("Đăng xuất 🚪"):
            st.session_state.dang_nhap_thanh_cong = False
            reset_session(st)
            st.rerun()

    st.subheader("1) Chọn cách dùng")

    mode_label = st.radio(
        "Chế độ",
        options=["Con học cùng app", "Ba mẹ dạy con"],
        horizontal=True
    )

    st.session_state.mode = "child" if mode_label == "Con học cùng app" else "parent"

    support_map = {
        "Gợi ý nhẹ": "goi_y",
        "Dẫn từng bước": "tung_buoc",
        "Xem cách giải": "cach_giai",
    }

    support_label = st.radio(
        "Mức hỗ trợ",
        options=list(support_map.keys()),
        index=0,
        horizontal=True
    )

    st.session_state.support_level = support_map[support_label]
    st.session_state.allow_full_solution = st.session_state.support_level == "cach_giai"

    st.divider()

    st.subheader("2) Nhập đề bài")

    uploaded_file = st.file_uploader(
        "Tải ảnh đề bài (nếu có)",
        type=["png", "jpg", "jpeg"]
    )

    typed_problem = st.text_area(
        "Hoặc gõ đề bài vào đây",
        value=st.session_state.problem_text,
        height=120,
        placeholder="Ví dụ: Lan có 24 quyển vở, mẹ mua thêm cho Lan 8 quyển nữa. Hỏi Lan có tất cả bao nhiêu quyển vở?"
    )

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("Bắt đầu bài này ✨"):
            if typed_problem.strip():
                st.session_state.problem_text = typed_problem.strip()
                st.session_state.problem_confirmed = True
                start_problem_session()
                st.rerun()

            elif uploaded_file is not None:
                try:
                    img = Image.open(uploaded_file)
                    st.session_state.pending_image = img

                    image_prompt = """
Hãy đọc đúng nguyên văn đề toán trong ảnh.
Chỉ trả về phần đề bài đã đọc được.
Không giải bài.
Không giải thích thêm.
"""
                    extracted_text = generate_multimodal_response(
                        system_prompt="Bạn là trợ lý đọc đề bài từ ảnh.",
                        image=img,
                        user_input=image_prompt
                    )

                    st.session_state.problem_text = extracted_text.strip()
                    st.session_state.problem_confirmed = False
                    st.rerun()

                except Exception as e:
                    st.error(f"Lỗi khi đọc ảnh: {e}")

            else:
                st.warning("Bạn hãy gõ đề bài hoặc tải ảnh lên trước nhé.")

    with col_b:
        if st.button("Làm bài mới 🧹"):
            reset_session(st)
            st.rerun()

    if st.session_state.problem_text and not st.session_state.problem_confirmed:
        st.divider()
        st.subheader("3) Xác nhận đề bài")

        st.info("Thầy đọc đề như sau:")
        st.text_area(
            "Đề bài đã đọc",
            value=st.session_state.problem_text,
            height=150,
            key="confirm_problem_text"
        )

        col_c, col_d = st.columns(2)

        with col_c:
            if st.button("Đúng rồi ✅"):
                st.session_state.problem_text = st.session_state.confirm_problem_text
                st.session_state.problem_confirmed = True
                start_problem_session()
                st.rerun()

        with col_d:
            if st.button("Lưu đề đã sửa ✏️"):
                st.session_state.problem_text = st.session_state.confirm_problem_text
                st.success("Đã cập nhật đề bài. Nếu đúng rồi, bấm 'Đúng rồi ✅'.")

    if st.session_state.problem_confirmed:
        st.divider()
        st.subheader("4) Học cùng app")

        st.caption(f"Đề bài hiện tại: {st.session_state.problem_text}")

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # --------- 1 NÚT HỖ TRỢ CHÍNH CHO MODE TRẺ: HIỆN NGAY TỪ LƯỢT ĐẦU ----------
        if (
            st.session_state.mode == "child"
            and not st.session_state.is_finished
            and len(st.session_state.chat_history) > 0
        ):
            st.markdown("**Hỗ trợ thêm:**")
            st.caption('Con bí thì bấm **Gợi ý thêm**, không cần gõ "không biết".')

            if st.button("Gợi ý thêm", key="child_help_button"):
                support_level_for_response, allow_full_solution_for_response = get_child_help_response_settings()

                run_followup_turn(
                    user_reply="con cần gợi ý thêm",
                    reply_type_override="student_dont_know",
                    support_level_override=support_level_for_response,
                    allow_full_solution_override=allow_full_solution_for_response,
                    append_user_message=False,
                )
                st.rerun()

        placeholder_text = (
            "Con trả lời ở đây nhé..."
            if st.session_state.mode == "child"
            else "Ba mẹ nhập câu hỏi hoặc tình huống của con ở đây..."
        )

        user_reply = st.chat_input(placeholder_text)

        if user_reply:
            if looks_like_new_problem(user_reply):
                start_new_problem(st, user_reply)
                start_problem_session()
                st.rerun()

            try:
                run_followup_turn(user_reply=user_reply)
                st.rerun()

            except Exception as e:
                st.error(f"Lỗi khi tạo phản hồi: {e}")

        st.divider()
        if st.button("Tạo tóm tắt cho ba mẹ 📘"):
            try:
                summary_context = build_summary_context(
                    problem_text=st.session_state.problem_text,
                    chat_history=st.session_state.chat_history
                )

                summary_text = generate_text_response(
                    system_prompt="Bạn là trợ lý tóm tắt buổi học Toán lớp 3 cho phụ huynh.",
                    user_input=summary_context
                )

                st.session_state.summary = summary_text
                st.rerun()

            except Exception as e:
                st.error(f"Lỗi khi tạo tóm tắt: {e}")

        if st.session_state.summary:
            st.subheader("Tóm tắt cho ba mẹ")
            st.markdown(st.session_state.summary)
