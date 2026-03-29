import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. CẤU HÌNH GIAO DIỆN WEB
st.set_page_config(page_title="Gia Sư AI", page_icon="🎓", layout="centered")

# 2. HỆ THỐNG KHÓA CỔNG
if "dang_nhap_thanh_cong" not in st.session_state:
    st.session_state.dang_nhap_thanh_cong = False

if not st.session_state.dang_nhap_thanh_cong:
    st.title("🔒 Cổng Đăng Nhập Gia Sư AI")
    st.info("Chào ba mẹ! Vui lòng nhập mã bản quyền để kích hoạt Thầy giáo AI cho con nhé.")
    
    mat_khau = st.text_input("Nhập mã bản quyền:", type="password")
    if st.button("Mở Khóa 🚀"):
        if mat_khau == "vip123": 
            st.session_state.dang_nhap_thanh_cong = True
            st.rerun() 
        else:
            st.error("Mã bản quyền không chính xác!")

else:
    # 3. KẾT NỐI KÉT SẮT LẤY CHÌA KHÓA
    api_key_an = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_an)

    # 4. LUẬT THÉP SƯ PHẠM (ĐÃ NÂNG CẤP)
    luat_thep = """
    Bạn là một Thầy Giáo dạy Toán thông minh và dứt khoát. 
    Luật bắt buộc: 
    1. Đọc kỹ "Lịch sử trò chuyện" để biết học sinh đang làm đến bước nào. KHÔNG hỏi lại những gì học sinh đã trả lời đúng.
    2. Nếu học sinh trả lời ĐÚNG một bước: Khen ngợi ngắn gọn (1 câu) -> Đặt câu hỏi gợi ý ngay sang BƯỚC TIẾP THEO của bài toán. (Ví dụ: "Đúng rồi! Vậy bây giờ có thêm 3 xe nữa thì sao nhỉ?"). Tuyệt đối không giải thích dông dài lại bước đã làm đúng.
    3. Nếu học sinh làm SAI hoặc nói không biết: Mới dùng ví dụ trực quan (kẹo, ngón tay) để hướng dẫn lại.
    4. KHÔNG BAO GIỜ giải ra đáp án cuối cùng. Xưng "Thầy", gọi "Con".
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=luat_thep
    )

    st.title("🎓 Gia Sư Toán Học Trí Tuệ Nhân Tạo")
    
    col_trong, col_nut = st.columns([4, 1])
    with col_nut:
        if st.button("Đăng xuất 🚪"):
            st.session_state.dang_nhap_thanh_cong = False
            st.session_state.chat_history = []
            st.rerun()

    # 5. KHUNG SƯỜN CHAT VÀ TRÍ NHỚ
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    col1, col2 = st.columns([1, 4])
    with col1:
        anh_tai_len = st.file_uploader("📸", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        
    cau_hoi = st.chat_input("Con gõ bài toán hoặc câu trả lời vào đây nhé...")

    if cau_hoi or anh_tai_len:
        with st.chat_message("user"):
            if anh_tai_len:
                img = Image.open(anh_tai_len)
                st.image(img, caption="Ảnh gửi lên", width=200)
            if cau_hoi:
                st.markdown(cau_hoi)
                
        noi_dung_gui = cau_hoi if cau_hoi else "Thầy ơi xem giúp con ảnh này!"
        st.session_state.chat_history.append({"role": "user", "content": noi_dung_gui})

        # --- HỆ THỐNG TRUYỀN TRÍ NHỚ CHO AI ---
        ngu_canh_chat = "Lịch sử trò chuyện từ trước đến nay:\n"
        for msg in st.session_state.chat_history:
            vai_tro = "Học sinh" if msg["role"] == "user" else "Thầy giáo"
            ngu_canh_chat += f"- {vai_tro}: {msg['content']}\n"
        ngu_canh_chat += "\nNhiệm vụ: Dựa vào lịch sử trên, hãy trả lời câu mới nhất của Học sinh theo đúng Luật Thép."

        with st.chat_message("assistant"):
            with st.spinner("Thầy đang suy nghĩ..."):
                try:
                    if anh_tai_len:
                        response = model.generate_content([img, ngu_canh_chat])
                    else:
                        response = model.generate_content(ngu_canh_chat)
                    
                    loi_thay_day = response.text
                    st.markdown(loi_thay_day)
                    st.session_state.chat_history.append({"role": "assistant", "content": loi_thay_day})
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")
