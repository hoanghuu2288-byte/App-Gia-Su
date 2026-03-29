import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. CẤU HÌNH GIAO DIỆN WEB
st.set_page_config(page_title="Gia Sư AI", page_icon="🎓", layout="centered")

# 2. HỆ THỐNG KHÓA CỔNG (PAYWALL)
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
            st.error("Mã bản quyền không chính xác! Ba mẹ vui lòng liên hệ Admin Linh.")

else:
    # --- BẢO MẬT API KEY: TỰ ĐỘNG LẤY TỪ KÉT SẮT ---
    api_key_an = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_an)

    # Luật Thép Sư Phạm
    luat_thep = """
    Bạn là một Thầy Giáo dạy Toán vô cùng kiên nhẫn và vui tính. 
    Luật bắt buộc: 
    1. KHÔNG BAO GIỜ giải ra đáp án cuối cùng.
    2. Ưu tiên dùng các ví dụ trực quan trên cơ thể (ngón tay, bàn tay) hoặc đồ vật thực tế quen thuộc nhất quanh bé để minh họa.
    3. Đọc đề bài -> Khen ngợi -> Gợi ý bằng MỘT câu hỏi đơn giản để học sinh tự suy nghĩ làm bước đầu tiên.
    4. Luôn xưng "Thầy" và gọi "Con", dùng nhiều biểu tượng cảm xúc.
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
            st.rerun()

    # --- KHUNG SƯỜN CHAT ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    col1, col2 = st.columns([1, 4])
    with col1:
        anh_tai_len = st.file_uploader("📸 Gửi ảnh", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        
    cau_hoi = st.chat_input("Con gõ bài toán vào đây nhé...")

    if cau_hoi or anh_tai_len:
        with st.chat_message("user"):
            if anh_tai_len:
                img = Image.open(anh_tai_len)
                st.image(img, caption="Ảnh đề bài con gửi", width=200)
            if cau_hoi:
                st.markdown(cau_hoi)
                
        noi_dung_gui = cau_hoi if cau_hoi else "Thầy ơi giải giúp con bài toán trong ảnh này với ạ!"
        st.session_state.chat_history.append({"role": "user", "content": noi_dung_gui})

        with st.chat_message("assistant"):
            with st.spinner("Thầy đang suy nghĩ..."):
                try:
                    if anh_tai_len:
                        response = model.generate_content([img, noi_dung_gui])
                    else:
                        response = model.generate_content(noi_dung_gui)
                    
                    loi_thay_day = response.text
                    st.markdown(loi_thay_day)
                    st.session_state.chat_history.append({"role": "assistant", "content": loi_thay_day})
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")
