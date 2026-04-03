# eval_cases.py

from dataclasses import dataclass, field
from typing import List


@dataclass
class TurnSpec:
    user: str
    must_have: List[str] = field(default_factory=list)
    must_not_have: List[str] = field(default_factory=list)


@dataclass
class EvalCase:
    id: str
    mode: str  # "child" | "parent"
    category: str
    problem: str
    support_level: str = "goi_y"

    opening_must_have: List[str] = field(default_factory=list)
    opening_must_not_have: List[str] = field(default_factory=list)

    turns: List[TurnSpec] = field(default_factory=list)

    transcript_must_have: List[str] = field(default_factory=list)
    transcript_must_not_have: List[str] = field(default_factory=list)

    final_must_have: List[str] = field(default_factory=list)
    final_must_not_have: List[str] = field(default_factory=list)

    min_pass_ratio: float = 0.72


def get_eval_cases() -> List[EvalCase]:
    return [
        # =====================================================
        # CHILD MODE
        # =====================================================
        EvalCase(
            id="child_rut_ve_don_vi_01",
            mode="child",
            category="rut_ve_don_vi",
            problem="Có 6 hộp bút như nhau đựng tất cả 48 chiếc bút. Hỏi 9 hộp như thế đựng bao nhiêu chiếc bút?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            opening_must_not_have=["Đáp số: 72"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["1 hộp"]),
                TurnSpec(user="__HINT__", must_have=["48", "6"]),
                TurnSpec(user="72", must_have=["72"]),
            ],
            transcript_must_have=["Rút về đơn vị", "1 hộp", "9 hộp"],
            final_must_have=["72", "chiếc bút", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chia_deu_01",
            mode="child",
            category="chia_deu",
            problem="36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="không biết", must_have=["phép chia"]),
                TurnSpec(user="6", must_have=["6"]),
            ],
            transcript_must_have=["chia đều"],
            final_must_have=["6", "chai", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_doi_don_vi_01",
            mode="child",
            category="doi_don_vi",
            problem="Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["đơn vị", "cm"]),
                TurnSpec(user="325", must_have=["325"]),
                TurnSpec(user="__HINT__", must_have=["trừ"]),
                TurnSpec(user="250", must_have=["250"]),
            ],
            transcript_must_have=["Đổi đơn vị", "cùng một đơn vị"],
            final_must_have=["250", "cm", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_nhan_roi_tru_01",
            mode="child",
            category="nhan_roi_tru",
            problem="Bác Hùng dự tính xây một ngôi nhà hết 78 000 viên gạch. Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. Hỏi theo dự tính, bác Hùng còn phải mua bao nhiêu viên gạch nữa?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["đã mua"]),
                TurnSpec(user="54000", must_have=["54 000"]),
                TurnSpec(user="__HINT__", must_have=["còn lại", "trừ"]),
                TurnSpec(user="24000", must_have=["24 000"]),
            ],
            transcript_must_have=["phép nhân", "phép trừ"],
            final_must_have=["24 000", "viên gạch", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_nhan_roi_tru_02",
            mode="child",
            category="nhan_roi_tru",
            problem="Một cửa hàng có 95 quyển vở. Người ta xếp đều vào 5 chồng, mỗi chồng lấy ra bán 7 quyển. Hỏi sau khi bán, cửa hàng còn lại bao nhiêu quyển vở?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="không biết", must_have=["đã bán"]),
                TurnSpec(user="35", must_have=["35"]),
                TurnSpec(user="60", must_have=["60"]),
            ],
            transcript_must_have=["đã bán", "còn lại"],
            final_must_have=["60", "quyển vở", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chu_vi_hinh_vuong_01",
            mode="child",
            category="chu_vi_hinh_vuong",
            problem="Người ta uốn một đoạn dây thép vừa đủ thành một hình vuông có cạnh 6 cm. Tính độ dài đoạn dây đó.",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="4", must_have=["4 cạnh"]),
                TurnSpec(user="24", must_have=["24"]),
            ],
            transcript_must_have=["Chu vi hình vuông"],
            final_must_have=["24", "cm", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chu_vi_hcn_01",
            mode="child",
            category="chu_vi_hinh_chu_nhat",
            problem="Một hình chữ nhật có chiều dài 12 cm, chiều rộng 7 cm. Tính chu vi hình chữ nhật đó.",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="19", must_have=["19"]),
                TurnSpec(user="38", must_have=["38"]),
            ],
            transcript_must_have=["Chu vi hình chữ nhật"],
            final_must_have=["38", "cm", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_gap_len_01",
            mode="child",
            category="gap_len",
            problem="Lan có 8 bông hoa. Mẹ cho Lan số hoa gấp 4 lần số hoa Lan có, rồi Lan đem tặng bạn 9 bông. Hỏi Lan còn lại bao nhiêu bông hoa?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["gấp 4"]),
                TurnSpec(user="32", must_have=["32"]),
                TurnSpec(user="40", must_have=["40"]),
                TurnSpec(user="31", must_have=["31"]),
            ],
            transcript_must_have=["gấp 4", "tặng", "còn lại"],
            final_must_have=["31", "bông hoa", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_so_lien_truoc_01",
            mode="child",
            category="so_lien_truoc",
            problem="Khoanh vào số liền trước của số 9999.",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["trừ 1"]),
                TurnSpec(user="9998", must_have=["9998"]),
            ],
            transcript_must_have=["Số liền trước"],
            final_must_have=["9998", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_so_lien_sau_01",
            mode="child",
            category="so_lien_sau",
            problem="Số liền sau của số lớn nhất có 4 chữ số là số nào?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="10000", must_have=["10 000"]),
            ],
            transcript_must_have=["Số liền sau"],
            final_must_have=["10 000", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_tim_so_bi_tru_01",
            mode="child",
            category="tim_thanh_phan_chua_biet",
            problem="Một số bị trừ đi 125 thì được 348. Tìm số đó.",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["hiệu", "số trừ"]),
                TurnSpec(user="473", must_have=["473"]),
            ],
            transcript_must_have=["Tìm thành phần chưa biết"],
            final_must_have=["473", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_chuoi_thao_tac_01",
            mode="child",
            category="chuoi_thao_tac",
            problem="420 -> bớt 120 -> [ô trống] -> chia 5 -> [ô trống]",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="300", must_have=["300"]),
                TurnSpec(user="60", must_have=["60"]),
            ],
            transcript_must_have=["Chuỗi thao tác", "ô trước", "ô sau"],
            final_must_have=["60", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_thieu_don_vi_01",
            mode="child",
            category="thieu_don_vi",
            problem="36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="6", must_have=["6"]),
                TurnSpec(user="6", must_have=["chai"]),
            ],
            transcript_must_have=["chai"],
            final_must_have=["6", "chai", "Kiến thức cần nhớ"],
        ),
        EvalCase(
            id="child_xin_dap_an_v2_01",
            mode="child",
            category="xin_dap_an_v2",
            problem="36 chai chia đều vào 6 khay. Hỏi mỗi khay có bao nhiêu chai?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="cho con đáp án", must_not_have=["Đáp số: 6 chai"]),
                TurnSpec(user="__HINT__", must_have=["phép chia"]),
                TurnSpec(user="__HINT__", must_have=["36", "6"]),
                TurnSpec(user="6", must_have=["6"]),
            ],
            transcript_must_have=["phép chia"],
            final_must_have=["6", "chai", "Kiến thức cần nhớ"],
        ),

        EvalCase(
            id="child_geometry_from_image_01",
            mode="child",
            category="geometry_from_image",
            problem="""Câu 4: (1 điểm) Cho hình vẽ. Từ vị trí ong vàng đến vườn hoa nào là xa nhất?

Dữ kiện nhìn thấy trong hình:
- Đường đến Vườn hoa hồng: 42890 m
- Đường đến Vườn hoa lan: 35000 m
- Đường đến Vườn hoa cúc: 45050 m
- Đường đến Vườn hoa hướng dương: 25090 m

Các lựa chọn:
A. Vườn hoa hồng
B. Vườn hoa lan
C. Vườn hoa cúc
D. Vườn hoa hướng dương""",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Cách nghĩ nhanh"],
            turns=[
                TurnSpec(user="__HINT__", must_have=["xa nhất"]),
                TurnSpec(user="C", must_have=["Vườn hoa cúc"]),
            ],
            transcript_must_have=["45050", "Vườn hoa cúc"],
            final_must_have=["Vườn hoa cúc", "Kiến thức cần nhớ"],
        ),

        # =====================================================
        # PARENT MODE
        # =====================================================
        EvalCase(
            id="parent_rut_ve_don_vi_01",
            mode="parent",
            category="rut_ve_don_vi",
            problem="Có 6 hộp bút như nhau đựng tất cả 48 chiếc bút. Hỏi 9 hộp như thế đựng bao nhiêu chiếc bút?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["Con làm phép tính gì nào", "con nhé"],
            transcript_must_have=["Đáp số", "72"],
            final_must_have=["72"],
        ),
        EvalCase(
            id="parent_doi_don_vi_01",
            mode="parent",
            category="doi_don_vi",
            problem="Một cuộn dây dài 3 m 25 cm, cắt đi 75 cm. Hỏi còn lại bao nhiêu xăng-ti-mét?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["Con làm phép tính gì nào", "con nhé"],
            transcript_must_have=["250", "cm"],
            final_must_have=["250", "cm"],
        ),
        EvalCase(
            id="parent_nhan_roi_tru_01",
            mode="parent",
            category="nhan_roi_tru",
            problem="Bác Hùng dự tính xây một ngôi nhà hết 78 000 viên gạch. Bác Hùng đã mua 3 lần, mỗi lần 18 000 viên gạch. Hỏi theo dự tính, bác Hùng còn phải mua bao nhiêu viên gạch nữa?",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con", "Lời giải mẫu ngắn"],
            opening_must_not_have=["con nhé", "Con làm phép tính gì nào"],
            transcript_must_have=["24 000"],
            final_must_have=["24 000", "viên gạch"],
        ),
        EvalCase(
            id="parent_hinh_hoc_01",
            mode="parent",
            category="chu_vi_hinh_vuong",
            problem="Người ta uốn một đoạn dây thép vừa đủ thành một hình vuông có cạnh 6 cm. Tính độ dài đoạn dây đó.",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["con nhé", "Con làm phép tính gì nào"],
            transcript_must_have=["24", "cm"],
            final_must_have=["24", "cm"],
        ),
        EvalCase(
            id="parent_geometry_from_image_01",
            mode="parent",
            category="geometry_from_image",
            problem="""Câu 4: (1 điểm) Cho hình vẽ. Từ vị trí ong vàng đến vườn hoa nào là xa nhất?

Dữ kiện nhìn thấy trong hình:
- Đường đến Vườn hoa hồng: 42890 m
- Đường đến Vườn hoa lan: 35000 m
- Đường đến Vườn hoa cúc: 45050 m
- Đường đến Vườn hoa hướng dương: 25090 m

Các lựa chọn:
A. Vườn hoa hồng
B. Vườn hoa lan
C. Vườn hoa cúc
D. Vườn hoa hướng dương""",
            opening_must_have=["Dạng bài", "Kiến thức dùng", "Hướng làm cả bài", "Ba mẹ nên hỏi con"],
            opening_must_not_have=["con nhé", "Con làm phép tính gì nào"],
            transcript_must_have=["45 050", "Vườn hoa cúc"],
            final_must_have=["Vườn hoa cúc"],
        ),
    ]


def get_case_map():
    return {case.id: case for case in get_eval_cases()}
