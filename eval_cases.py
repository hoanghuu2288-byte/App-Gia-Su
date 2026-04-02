# eval_cases.py

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalCase:
    id: str
    mode: str  # "child" | "parent"
    category: str
    problem: str
    support_level: str = "goi_y"
    student_turns: List[str] = field(default_factory=list)
    opening_must_have: List[str] = field(default_factory=list)
    opening_must_not_have: List[str] = field(default_factory=list)
    final_must_have: List[str] = field(default_factory=list)
    final_must_not_have: List[str] = field(default_factory=list)


def get_eval_cases() -> List[EvalCase]:
    return [
        # =========================
        # MODE TRẺ
        # =========================
        EvalCase(
            id="child_rut_ve_don_vi_01",
            mode="child",
            category="rut_ve_don_vi",
            problem="Có 6 hộp bút như nhau đựng tất cả 48 chiếc bút. Hỏi 9 hộp như thế đựng bao nhiêu chiếc bút?",
            student_turns=["__HINT__", "__HINT__", "72"],
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh", "Rút về đơn vị"],
            opening_must_not_have=["Đáp số", "đáp án ngay"],
            final_must_have=["72", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chia_deu_01",
            mode="child",
            category="chia_deu",
            problem="36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?",
            student_turns=["không biết", "6"],
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["6", "chai", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_doi_don_vi_01",
            mode="child",
            category="doi_don_vi",
            problem="Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?",
            student_turns=["__HINT__", "325", "__HINT__", "250"],
            opening_must_have=["Đổi đơn vị rồi tính", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["250", "cm", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_nhan_roi_tru_01",
            mode="child",
            category="nhan_roi_tru",
            problem="Bác Hùng dự tính xây một ngôi nhà hết 78 000 viên gạch. Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. Hỏi theo dự tính, bác Hùng còn phải mua bao nhiêu viên gạch nữa?",
            student_turns=["__HINT__", "54000", "__HINT__", "24000"],
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["24 000", "viên gạch", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_nhan_roi_tru_02",
            mode="child",
            category="nhan_roi_tru",
            problem="Một cửa hàng có 95 quyển vở. Người ta xếp đều vào 5 chồng, mỗi chồng lấy ra bán 7 quyển. Hỏi sau khi bán, cửa hàng còn lại bao nhiêu quyển vở?",
            student_turns=["không biết", "__HINT__", "35", "__HINT__", "60"],
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["60", "quyển vở", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chu_vi_hinh_vuong_01",
            mode="child",
            category="chu_vi_hinh_vuong",
            problem="Người ta uốn một đoạn dây thép vừa đủ thành một hình vuông có cạnh 6 cm. Tính độ dài đoạn dây đó.",
            student_turns=["4", "24"],
            opening_must_have=["Chu vi hình vuông", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["24", "cm", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chu_vi_hcn_01",
            mode="child",
            category="chu_vi_hinh_chu_nhat",
            problem="Một hình chữ nhật có chiều dài 12 cm, chiều rộng 7 cm. Tính chu vi hình chữ nhật đó.",
            student_turns=["19", "38"],
            opening_must_have=["Chu vi hình chữ nhật", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["38", "cm", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_gap_len_01",
            mode="child",
            category="gap_len",
            problem="Lan có 8 bông hoa. Mẹ cho Lan số hoa gấp 4 lần số hoa Lan có, rồi Lan đem tặng bạn 9 bông. Hỏi Lan còn lại bao nhiêu bông hoa?",
            student_turns=["__HINT__", "32", "40", "31"],
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["31", "bông hoa", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_so_lien_truoc_01",
            mode="child",
            category="so_lien_truoc",
            problem="Khoanh vào số liền trước của số 9999.",
            student_turns=["__HINT__", "9998"],
            opening_must_have=["Số liền trước", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["9998", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_so_lien_sau_01",
            mode="child",
            category="so_lien_sau",
            problem="Số liền sau của số lớn nhất có 4 chữ số là số nào?",
            student_turns=["10000"],
            opening_must_have=["Số liền sau", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["10 000", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_tim_so_bi_tru_01",
            mode="child",
            category="tim_thanh_phan_chua_biet",
            problem="Một số bị trừ đi 125 thì được 348. Tìm số đó.",
            student_turns=["__HINT__", "473"],
            opening_must_have=["Tìm thành phần chưa biết", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["473", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chuoi_thao_tac_01",
            mode="child",
            category="chuoi_thao_tac",
            problem="420 -> bớt 120 -> [ô trống] -> chia 5 -> [ô trống]",
            student_turns=["300", "60"],
            opening_must_have=["Chuỗi thao tác", "Kiến thức dùng", "Cách nghĩ nhanh"],
            final_must_have=["60", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_xin_dap_an_01",
            mode="child",
            category="xin_dap_an",
            problem="36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?",
            student_turns=["cho con đáp án", "__HINT__", "6"],
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            opening_must_not_have=["Đáp số:"],
            final_must_have=["6", "chai", "Kiến thức cần nhớ"],
        ),

        # =========================
        # MODE PHỤ HUYNH
        # =========================
        EvalCase(
            id="parent_rut_ve_don_vi_01",
            mode="parent",
            category="rut_ve_don_vi",
            problem="Có 6 hộp bút như nhau đựng tất cả 48 chiếc bút. Hỏi 9 hộp như thế đựng bao nhiêu chiếc bút?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["Con làm phép tính gì nào", "con nhé"],
            final_must_have=["Đáp số", "72"],
        ),
        EvalCase(
            id="parent_doi_don_vi_01",
            mode="parent",
            category="doi_don_vi",
            problem="Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["Con làm phép tính gì nào", "con nhé"],
            final_must_have=["250", "cm"],
        ),
        EvalCase(
            id="parent_nhan_roi_tru_01",
            mode="parent",
            category="nhan_roi_tru",
            problem="Bác Hùng dự tính xây một ngôi nhà hết 78 000 viên gạch. Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. Hỏi theo dự tính, bác Hùng còn phải mua bao nhiêu viên gạch nữa?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con", "Lời giải mẫu ngắn"],
            opening_must_not_have=["con nhé", "Con làm phép tính gì nào"],
            final_must_have=["24 000", "viên gạch"],
        ),
        EvalCase(
            id="parent_hinh_hoc_01",
            mode="parent",
            category="chu_vi_hinh_vuong",
            problem="Người ta uốn một đoạn dây thép vừa đủ thành một hình vuông có cạnh 6 cm. Tính độ dài đoạn dây đó.",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["con nhé", "Con làm phép tính gì nào"],
            final_must_have=["24", "cm"],
        ),
    ]
