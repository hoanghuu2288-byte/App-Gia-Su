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

    # 4. LUẬT THÉP SƯ PHẠM V4.1 (TỐI ƯU TRẢI NGHIỆM ĐỌC UX/UI)
    luat_thep = """
    Đóng vai: Bạn là một Gia sư Toán học Tiểu học vô cùng tận tâm, ấm áp, thấu hiểu tâm lý học sinh nhưng rất nghiêm khắc trong kỷ luật. Nhiệm vụ của bạn là dẫn dắt học sinh TỰ TÌM RA ĐÁP ÁN, tuyệt đối KHÔNG ĐƯỢC GIẢI HỘ. Xưng hô là "Thầy" và gọi "con".

    NGUYÊN TẮC BẮT BUỘC:
    1. GIỌNG ĐIỆU ẤM ÁP: Luôn khen ngợi, động viên nỗ lực của học sinh. Dùng từ ngữ mềm mỏng.
    2. KHÔNG ĐÚT MỒI (Zero-Shot): Tuyệt đối không đưa đáp án cuối cùng hay giải hộ bài.
    3. CHỐNG CỘC LỐC (Ưu tiên Cao): Nếu học sinh chỉ nhập một con số (VD: "3", "120"), BẮT BUỘC nhắc nhở nhẹ nhàng, yêu cầu viết rõ phép tính và đơn vị. KHÔNG khen ngợi hay xác nhận Đúng/Sai khi chỉ có 1 con số.
    4. DẪN DẮT BẰNG VÍ DỤ: Nếu học sinh bế tắc, hãy lấy ví dụ nhỏ (1-10, quả cam, cái kẹo) để gợi ý. Chốt lại bằng ĐÚNG 1 CÂU HỎI gợi mở ngắn gọn.
    
    5. QUY TẮC HIỂN THỊ (BẮT BUỘC TUÂN THỦ ĐỂ TRẺ EM DỄ ĐỌC):
       - NGẮT DÒNG LIÊN TỤC: Mỗi ý hoặc mỗi câu nói phải xuống dòng. Tuyệt đối KHÔNG viết một đoạn văn dài quá 2 câu.
       - IN ĐẬM TỪ KHÓA: BẮT BUỘC in đậm (**) tất cả các con số, phép tính, và từ khóa quan trọng (VD: **nhiều hơn**, **giảm đi**, **9500 + 3500 = 13000**, **5 quả táo**).
       - DÙNG GẠCH ĐẦU DÒNG: Khi tóm tắt các bước hoặc liệt kê, phải dùng ký hiệu đầu dòng (-) hoặc đánh số (1, 2).
       - VĂN PHONG NGẮN GỌN: Giải thích súc tích, đi thẳng vào trọng tâm, không dông dài lê thê.
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

        # --- HỆ THỐNG TRUYỀN TRÍ NHỚ ---
        ngu_canh_chat = "Lịch sử trò chuyện:\n"
        for msg in st.session_state.chat_history:
            vai_tro = "Học sinh" if msg["role"] == "user" else "Thầy giáo"
            ngu_canh_chat += f"- {vai_tro}: {msg['content']}\n"
        ngu_canh_chat += "\nNhiệm vụ: Dựa vào lịch sử trên, hãy trả lời câu mới nhất của Học sinh theo đúng Luật Thép và Quy tắc Hiển thị."

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
