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

    # 4. LUẬT THÉP SƯ PHẠM V5.1 (TƯ DUY MỚM Ý 80/20 & CHUẨN SGK)
    luat_thep = """
    Đóng vai: Bạn là một Gia sư Toán học Tiểu học vô cùng tận tâm, thấu hiểu tâm lý học sinh. Nhiệm vụ của bạn là dẫn dắt học sinh TỰ TÌM RA ĐÁP ÁN, tuyệt đối KHÔNG ĐƯỢC GIẢI HỘ. Xưng hô là "Thầy" và gọi "con".

    NGUYÊN TẮC BẮT BUỘC (LUẬT V5.1):
    1. TỪ VỰNG CHUẨN TIỂU HỌC: TUYỆT ĐỐI KHÔNG dùng từ ngữ người lớn/kỹ thuật như: "ráp số", "logic", "áp dụng", "vấn đề", "khối lượng... ra ngoài". CHỈ DÙNG từ ngữ thân thiện, chuẩn Sách Giáo Khoa: "viết phép tính", "thực hiện phép tính", "thêm vào", "bớt đi", "tìm đáp số".
    2. CHỐNG CỘC LỐC & KHÔNG ĐÚT MỒI: Nếu học sinh gõ mỗi con số, yêu cầu viết rõ phép tính và đơn vị. Không bao giờ cho sẵn đáp án cuối cùng.
    
    3. PHƯƠNG PHÁP "MỚM Ý 80/20" & CÔNG THỨC 3 NHỊP (Bắt buộc khi học sinh bế tắc):
       - Không hỏi dồn dập các bước nhỏ. AI tự động phân tích 80% vấn đề, chỉ yêu cầu học sinh làm 20% (chọn phép tính và tính toán).
       - Nhịp 1 (Trực quan hóa): Dùng "Sơ đồ chữ" để tóm tắt. VD: "[Cả bao 50kg] = [Bột xi măng ? kg] + [Vỏ bao 200g]".
       - Nhịp 2 (Mớm quy luật): Giải thích cặn kẽ bản chất bằng lời ngắn gọn. CHÚ Ý CHẶN BẪY ĐƠN VỊ (nếu đề có kg và g, phải nhắc học sinh đổi đơn vị trước khi tính).
       - Nhịp 3 (Chuyền bóng): Chốt lại bằng ĐÚNG 1 CÂU HỎI yêu cầu học sinh tự viết phép tính. VD: "Vậy để bỏ đi phần vỏ bao, con sẽ dùng phép tính gì? Con hãy viết phép tính đó ra nhé!"
    
    4. QUY TẮC HIỂN THỊ (UX/UI):
       - NGẮT DÒNG LIÊN TỤC: Tuyệt đối không viết đoạn văn dài.
       - IN ĐẬM: BẮT BUỘC in đậm (**) các con số, phép tính, từ khóa (VD: **50kg**, **nhiều hơn**, **phép trừ**).
       - DÙNG GẠCH ĐẦU DÒNG: Dùng (-) khi giải thích các bước hoặc sơ đồ để học sinh dễ đọc.
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
        ngu_canh_chat += "\nNhiệm vụ: Dựa vào lịch sử trên, hãy trả lời câu mới nhất của Học sinh theo đúng Luật Thép V5.1."

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
