# grade3_math_master.py

GRADE3_MATH_MASTER = {
    "direct_calculation_add_subtract": {
        "major_type": "direct_calculation",
        "sub_type": "add_subtract",
        "label": "Tính trực tiếp cộng / trừ",
        "keywords": ["tính", "+", "-", "đặt tính", "tính nhẩm"],
        "knowledge_used": "Phép cộng hoặc phép trừ",
        "flow_type": "direct_calculation",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc đây là phép cộng hay phép trừ, không giải hộ.",
            "tung_buoc": "Nhắc làm theo từng hàng nếu cần.",
            "cach_giai": "Có thể trình bày phép tính đầy đủ."
        },
        "common_errors": [
            "Quên nhớ",
            "Quên mượn",
            "Tính nhầm theo hàng"
        ],
    },

    "direct_calculation_multiply_divide": {
        "major_type": "direct_calculation",
        "sub_type": "multiply_divide",
        "label": "Tính trực tiếp nhân / chia",
        "keywords": ["nhân", "chia", ":", "×", "x"],
        "knowledge_used": "Bảng nhân, bảng chia",
        "flow_type": "direct_calculation",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc bảng nhân / chia liên quan.",
            "tung_buoc": "Cho học sinh nhẩm hoặc lần theo bảng.",
            "cach_giai": "Có thể nêu phép tính và kết quả."
        },
        "common_errors": [
            "Nhầm bảng nhân",
            "Chia sai",
            "Nhìn nhầm phép tính"
        ],
    },

    "compare_largest_smallest": {
        "major_type": "compare_numbers",
        "sub_type": "largest_smallest",
        "label": "Tìm số lớn nhất / nhỏ nhất",
        "keywords": ["lớn nhất", "bé nhất", "nhỏ nhất", "xa nhất", "ngắn nhất"],
        "knowledge_used": "So sánh các số theo từng hàng",
        "flow_type": "compare_numbers",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc tìm số lớn nhất hoặc nhỏ nhất trước.",
            "tung_buoc": "Cho so từng cặp hoặc nhìn hàng lớn nhất.",
            "cach_giai": "Có thể nêu cách so và chốt đối tượng đúng."
        },
        "common_errors": [
            "Tìm đúng số nhưng quên đối tượng",
            "So nhầm hàng"
        ],
    },

    "one_step_word_problem_add": {
        "major_type": "word_problem_one_step",
        "sub_type": "add",
        "label": "Bài toán có lời văn 1 bước - thêm vào / gộp lại",
        "keywords": ["thêm", "tất cả", "cả hai", "gộp", "tổng cộng"],
        "knowledge_used": "Phép cộng",
        "flow_type": "one_step_word_problem",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ gợi ý bài đang hỏi tổng cộng hay thêm vào.",
            "tung_buoc": "Nhắc số nào cộng với số nào.",
            "cach_giai": "Nêu phép cộng và câu trả lời."
        },
        "common_errors": [
            "Dùng nhầm phép trừ"
        ],
    },

    "one_step_word_problem_subtract": {
        "major_type": "word_problem_one_step",
        "sub_type": "subtract",
        "label": "Bài toán có lời văn 1 bước - bớt đi / còn lại",
        "keywords": ["còn lại", "bớt", "cắt đi", "cho đi", "bán đi"],
        "knowledge_used": "Phép trừ",
        "flow_type": "one_step_word_problem",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ gợi ý bài đang hỏi phần còn lại.",
            "tung_buoc": "Nhắc số ban đầu và số bị bớt.",
            "cach_giai": "Nêu phép trừ và câu trả lời."
        },
        "common_errors": [
            "Lấy ngược số",
            "Không đọc kỹ câu hỏi"
        ],
    },

    "multi_step_find_missing": {
        "major_type": "multi_step",
        "sub_type": "find_missing_after_intermediate",
        "label": "Bài nhiều bước - tìm phần đã có rồi tìm phần còn thiếu",
        "keywords": ["mỗi lần", "đã mua", "còn phải", "còn thiếu", "dự tính"],
        "knowledge_used": "Phép nhân rồi phép trừ, hoặc cộng rồi trừ",
        "flow_type": "multi_step",
        "show_plan_steps": True,
        "plan_steps": [
            "Tìm phần đã có hoặc đã làm xong",
            "Tìm phần còn thiếu hoặc còn lại"
        ],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc đang đi 2 bước, không cho phép tính ngay.",
            "tung_buoc": "Hỏi rõ bước 1 trước rồi mới sang bước 2.",
            "cach_giai": "Trình bày đủ 2 bước."
        },
        "common_errors": [
            "Quên bước trung gian",
            "Trừ sai",
            "Dùng nhầm phép tính đầu tiên"
        ],
    },

    "unit_conversion_then_calculate": {
        "major_type": "unit_conversion",
        "sub_type": "convert_then_calculate",
        "label": "Đổi đơn vị rồi tính",
        "keywords": ["m", "cm", "kg", "g", "đổi", "xăng-ti-mét", "ki-lô-gam"],
        "knowledge_used": "Đổi về cùng đơn vị trước rồi mới tính",
        "flow_type": "unit_conversion",
        "show_plan_steps": True,
        "plan_steps": [
            "Đổi về cùng đơn vị",
            "Làm phép tính"
        ],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc phải đổi về cùng đơn vị trước.",
            "tung_buoc": "Làm xong bước đổi rồi mới sang phép tính.",
            "cach_giai": "Trình bày bước đổi rồi bước tính."
        },
        "common_errors": [
            "Không đổi đơn vị",
            "Đổi sai",
            "Tính luôn khi đơn vị chưa giống nhau"
        ],
    },

    "unit_rate_find_one_then_many": {
        "major_type": "unit_rate",
        "sub_type": "find_one_then_many",
        "label": "Rút về đơn vị",
        "keywords": ["như nhau", "tất cả", "mấy hộp", "mấy khay", "mấy gói", "mấy chồng"],
        "knowledge_used": "Chia để tìm 1 phần, rồi nhân để tìm nhiều phần",
        "flow_type": "unit_rate",
        "show_plan_steps": True,
        "plan_steps": [
            "Tìm 1 phần",
            "Tìm nhiều phần"
        ],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc tìm 1 phần trước.",
            "tung_buoc": "Làm phép chia trước rồi mới nhân.",
            "cach_giai": "Trình bày đủ 2 bước."
        },
        "common_errors": [
            "Nhân luôn không qua bước tìm 1 phần",
            "Nhầm chia với nhân"
        ],
    },

    "geometry_identification_circle_parts": {
        "major_type": "geometry_identification",
        "sub_type": "circle_parts",
        "label": "Nhận biết tâm, bán kính, đường kính",
        "keywords": ["tâm", "bán kính", "đường kính", "hình tròn"],
        "knowledge_used": "Phân biệt tâm, bán kính, đường kính",
        "flow_type": "geometry_identification",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": None,
        "support_rules": {
            "goi_y": "Chỉ nhắc nhìn điểm ở giữa hoặc đoạn đi qua tâm.",
            "tung_buoc": "Nhận ra tâm trước rồi mới xét đoạn thẳng.",
            "cach_giai": "Giải thích rõ tâm, bán kính, đường kính."
        },
        "common_errors": [
            "Nhầm bán kính với đường kính",
            "Không xác định được tâm"
        ],
    },

    "multiple_choice_general": {
        "major_type": "multiple_choice",
        "sub_type": "general",
        "label": "Trắc nghiệm - chọn đáp án đúng",
        "keywords": ["chọn đáp án đúng", "khẳng định đúng", "câu nào đúng", "phương án đúng"],
        "knowledge_used": "Đọc từng đáp án và kiểm tra",
        "flow_type": "multiple_choice",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": "check_each_option",
        "support_rules": {
            "goi_y": "Chỉ nhắc mình xét từng đáp án một.",
            "tung_buoc": "Xét A rồi B rồi C rồi D.",
            "cach_giai": "Giải thích từng đáp án đúng/sai ngắn gọn."
        },
        "common_errors": [
            "Chọn theo cảm giác",
            "Không kiểm tra từng đáp án"
        ],
    },

    "multiple_choice_geometry_circle": {
        "major_type": "multiple_choice",
        "sub_type": "geometry_circle",
        "label": "Trắc nghiệm hình học - tâm, bán kính, đường kính",
        "keywords": ["chọn khẳng định đúng", "tâm hình tròn", "OQ", "OP", "MN"],
        "knowledge_used": "Phân biệt tâm, bán kính, đường kính và xét từng đáp án",
        "flow_type": "multiple_choice",
        "show_plan_steps": False,
        "plan_steps": [],
        "multiple_choice_strategy": "check_each_option",
        "support_rules": {
            "goi_y": "Chỉ xét từng đáp án, không tự loại hết quá sớm.",
            "tung_buoc": "Xét A đúng hay sai, rồi mới sang B, C, D.",
            "cach_giai": "Nêu ngắn gọn vì sao từng đáp án đúng/sai."
        },
        "common_errors": [
            "Tự chốt đáp án quá sớm",
            "Nhầm đường kính với bán kính"
        ],
    },
}


def get_problem_blueprint(problem_type: str) -> dict:
    return GRADE3_MATH_MASTER.get(problem_type, {})


def list_all_problem_types() -> list[str]:
    return list(GRADE3_MATH_MASTER.keys())
