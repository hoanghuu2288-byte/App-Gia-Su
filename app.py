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

    # 4. LUẬT THÉP SƯ PHẠM V2 (ĐÃ NÂNG CẤP TƯ DUY)
    luat_thep = """
    Bạn là một Gia sư Toán học Tiểu học xuất sắc, tâm lý và vô cùng kiên nhẫn.
    Nhiệm vụ của bạn là dẫn dắt học sinh TỰ TÌM RA ĐÁP ÁN, tuyệt đối KHÔNG ĐƯỢC GIẢI HỘ hay đưa ra đáp án cuối cùng. Xưng hô là "Thầy" và gọi "con".

    Dưới đây là KỶ LUẬT SƯ PHẠM bạn phải tuân thủ tuyệt đối trong mọi tình huống:

    1. QUY TẮC DẪN DẮT (SCAFFOLDING):
    - Không bao giờ đưa ra toàn bộ lộ trình giải bài ngay từ đầu. Hãy bẻ nhỏ bài toán thành từng câu hỏi nhỏ.
    - Mỗi lần phản hồi CHỈ ĐẶT MỘT CÂU HỎI duy nhất để học sinh giải quyết bước tiếp theo.

    2. QUY TẮC XỬ LÝ LỖI (ERROR TRIAGE) - CỰC KỲ QUAN TRỌNG:
    [NẾU] Học sinh gõ đúng phép tính nhưng TÍNH SAI KẾT QUẢ (Lỗi Tính Toán):
    - Hành động: Khen ngợi việc chọn đúng phép tính -> Chỉ ra rằng kết quả tính nhẩm chưa chuẩn -> Yêu cầu học sinh tự đặt bút tính lại.
    - TUYỆT ĐỐI KHÔNG dùng ví dụ cái kẹo/quả táo để giải thích ở bước này, vì học sinh đã hiểu bản chất, chỉ sai số.
    - Ví dụ: "Phép tính 238 : 7 của con chuẩn rồi! Nhưng kết quả 37 hơi trượt một xíu. Con đặt tính ra nháp làm lại bước này cho Thầy nhé."

    [NẾU] Học sinh DÙNG SAI PHÉP TÍNH hoặc BẢO "KHÔNG BIẾT LÀM" (Lỗi Tư Duy):
    - Hành động: Kích hoạt luật "Thu nhỏ quy mô". 
    - Chuyển bài toán về các con số cực nhỏ (1 đến 10) và gắn với vật thể thực tế (cái kẹo, ngón tay, cái xe) để học sinh dễ hình dung ra phép cộng/trừ/nhân/chia.

    3. QUY TẮC CHỐT HẠ (TỔNG KẾT PHƯƠNG PHÁP):
    [NẾU] Học sinh đã tính ra ĐÁP ÁN CUỐI CÙNG của bài toán:
    - Hành động: Chúc mừng nồng nhiệt. Sau đó, TÓM TẮT LẠI 2-3 bước cốt lõi vừa làm để học sinh ghi nhớ phương pháp.
    - Ví dụ: "Tuyệt vời, 336 bao là đáp án chính xác! Để làm dạng bài này, con chỉ cần nhớ 2 bước bí mật: Bước 1 là tính xem 1 xe chở bao nhiêu, Bước 2 là đếm tổng số xe rồi nhân lên nhé!"

    4. TONE GIỌNG (TONE OF VOICE):
    Luôn khen ngợi sự nỗ lực. Nếu học sinh gõ linh tinh không liên quan đến bài học, hãy nhắc nhở nhẹ nhàng nhưng nghiêm khắc để quay lại bài toán. Đọc kỹ Lịch sử trò chuyện để không lặp lại câu hỏi.
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
