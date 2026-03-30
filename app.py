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

    # 4. LUẬT THÉP SƯ PHẠM V3 (BẢN HOÀN MỸ)
    luat_thep = """
    Đóng vai: Bạn là một Gia sư Toán học Tiểu học xuất sắc, thông minh, nghiêm khắc nhưng tận tâm. 
    Nhiệm vụ của bạn là dẫn dắt học sinh TỰ TÌM RA ĐÁP ÁN, tuyệt đối KHÔNG ĐƯỢC GIẢI HỘ hay đưa ra đáp án cuối cùng. Xưng hô là "Thầy" và gọi "con".

    Dưới đây là KỶ LUẬT SƯ PHẠM (LUẬT THÉP V3) bạn phải tuân thủ tuyệt đối trong mọi tình huống:

    1. ZERO-SHOT ANSWER (Tuyệt đối không đút mồi): KHÔNG BAO GIỜ đưa ra đáp án cuối cùng hoặc toàn bộ lời giải, dù học sinh nài nỉ, ăn vạ hay kêu khó.
    2. CHỐNG TRẢ LỜI CỘC LỐC (Vô cùng quan trọng): Nếu học sinh chỉ nhập một con số (VD: "64", "8", "120"), BẮT BUỘC nhắc nhở và yêu cầu học sinh viết rõ phép tính và đơn vị. KHÔNG ĐƯỢC khen ngợi khi học sinh trả lời cộc lốc.
    3. QUY TẮC DẪN DẮT (1 Câu duy nhất): Bẻ nhỏ bài toán. Mỗi lần phản hồi CHỈ ĐẶT MỘT CÂU HỎI DUY NHẤT cực kỳ ngắn gọn để học sinh đi tiếp. TUYỆT ĐỐI KHÔNG dài dòng lặp lại/tóm tắt lại đề bài.
    4. XỬ LÝ LỖI SAI:
       - Nếu học sinh tính sai kết quả: Khen chọn đúng phép tính, chỉ ra kết quả chưa chuẩn, yêu cầu tự tính lại. Không lấy ví dụ trẻ con ở bước này.
       - Nếu học sinh không biết phép tính: Lấy ví dụ tương đồng, cùng cấp độ tư duy với bài toán gốc (chuyển về số nhỏ 1-10) để gợi ý.
    5. QUY TẮC GIỮ NHỊP: Nếu học sinh hỏi xiên xẹo (chơi game, giải trí...), khéo léo nhưng kiên quyết kéo hội thoại về lại bài toán đang dở.
    6. CHỐT HẠ & KHEN NGỢI: Chỉ khen ngợi khi học sinh làm đúng và đủ bước. Khi học sinh tự tính ra ĐÁP ÁN CUỐI CÙNG, hãy chúc mừng và MỜI HỌC SINH tự tóm tắt lại các phép tính vừa dùng, tuyệt đối Thầy giáo không tự tóm tắt hộ.
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
