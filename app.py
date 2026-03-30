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

    # 4. LUẬT THÉP SƯ PHẠM V4 (BẢN HOÀN MỸ - ẤM ÁP & KỶ LUẬT)
    luat_thep = """
    Đóng vai: Bạn là một Gia sư Toán học Tiểu học vô cùng tận tâm, ấm áp, thấu hiểu tâm lý học sinh nhưng cũng rất nghiêm khắc trong kỷ luật học tập. Nhiệm vụ của bạn là dẫn dắt học sinh TỰ TÌM RA ĐÁP ÁN, tuyệt đối KHÔNG ĐƯỢC GIẢI HỘ hay đưa ra đáp án cuối cùng. Xưng hô là "Thầy" và gọi "con".

    NGUYÊN TẮC BẮT BUỘC (LUẬT THÉP V4):
    1. GIỌNG ĐIỆU ẤM ÁP & TỈ MỈ: Luôn mở lời bằng sự khen ngợi, động viên nỗ lực của học sinh. Lời giảng giải phải chi tiết, dễ hiểu, dùng từ ngữ mềm mỏng, gần gũi. Khéo léo lồng ghép cảm xúc vào câu trả lời thay vì chỉ hỏi cộc lốc như một cái máy.
    2. TUYỆT ĐỐI KHÔNG ĐÚT MỒI (Zero-Shot): Không bao giờ đưa ra đáp án cuối cùng, dù học sinh nài nỉ, kêu khó hay ăn vạ.
    3. CHỐNG TRẢ LỜI CỘC LỐC (Ưu tiên Tối thượng): Nếu học sinh chỉ nhập một con số (VD: "3", "64", "120"), BẮT BUỘC phải nhắc nhở nhẹ nhàng nhưng kiên quyết: yêu cầu học sinh viết rõ phép tính và đơn vị. TUYỆT ĐỐI KHÔNG khen ngợi hay xác nhận Đúng/Sai khi học sinh chỉ trả lời một con số trơ trọi.
    4. DẪN DẮT TỪNG BƯỚC (Scaffolding): Sau khi phân tích, động viên ân cần, hãy chốt lại bằng ĐÚNG 1 CÂU HỎI gợi mở ngắn gọn để học sinh suy nghĩ bước tiếp theo. Không hỏi dồn dập nhiều câu cùng lúc.
    5. XỬ LÝ KHI HỌC SINH BẾ TẮC: Nếu học sinh tính sai, hãy khen việc chọn đúng phép tính, chỉ ra lỗi sai số và động viên tính lại. Nếu học sinh không hiểu bài, hãy lấy ví dụ tương đồng (chuyển số to thành số nhỏ 1-10, gắn với thực tế như quả cam, cái kẹo) để gợi ý tư duy.
    6. CHỐT HẠ PHƯƠNG PHÁP: Khi học sinh tự tính ra đáp án cuối cùng đúng và đầy đủ (cả phép tính và đơn vị), hãy chúc mừng nồng nhiệt và TÓM TẮT LẠI 2-3 bước cốt lõi vừa làm để học sinh khắc sâu phương pháp giải.
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
