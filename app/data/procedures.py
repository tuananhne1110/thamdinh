# Định nghĩa cấu trúc thủ tục hành chính
# Mỗi thủ tục có thể có nhiều trường hợp con (cases)

PROCEDURES = {
    "dang_ky_tam_tru": {
        "name": "Đăng ký tạm trú",
        "description": "Thủ tục đăng ký tạm trú cho công dân",
        "cases": {
            "thuong": {
                "name": "Hồ sơ đăng ký tạm trú thông thường",
                "description": "Áp dụng cho công dân đăng ký tạm trú thông thường",
                "required_documents": [
                    {
                        "name": "Tờ khai thay đổi thông tin cư trú",
                        "code": "CT01",
                        "file_type": "form",
                        "required": True,
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    },
                    {
                        "name": "Giấy tờ, tài liệu chứng minh chỗ ở hợp pháp",
                        "code": "chung_minh_cho_o",
                        "file_type": "document",
                        "required": True,
                        "alternatives": ["residence_proof", "property_certificate", "contract", "confirmation_letter"],
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    }
                ]
            },
            "don_vi_dong_quan": {
                "name": "Đăng ký tạm trú tại nơi đơn vị đóng quân trong Công an nhân dân",
                "description": "Áp dụng cho cán bộ chiến sĩ trong Công an nhân dân",
                "required_documents": [
                    {
                        "name": "Tờ khai thay đổi thông tin cư trú",
                        "code": "CT01",
                        "file_type": "form",
                        "required": True,
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    },
                    {
                        "name": "Giấy giới thiệu của Thủ trưởng đơn vị quản lý trực tiếp",
                        "code": "giay_gioi_thieu",
                        "file_type": "document",
                        "required": True,
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    }
                ]
            },
            "theo_danh_sach": {
                "name": "Đăng ký tạm trú theo danh sách",
                "description": "Áp dụng cho đăng ký tạm trú theo danh sách tập thể",
                "required_documents": [
                    {
                        "name": "Tờ khai thay đổi thông tin cư trú (của từng người)",
                        "code": "CT01",
                        "file_type": "form",
                        "required": True,
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    },
                    {
                        "name": "Văn bản đề nghị đăng ký tạm trú kèm danh sách người tạm trú",
                        "code": "van_ban_de_nghi",
                        "file_type": "document",
                        "required": True,
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    }
                ]
            }
        }
    },
    "dang_ky_thuong_tru": {
        "name": "Đăng ký thường trú",
        "description": "Thủ tục đăng ký thường trú cho công dân",
        "cases": {
            "thuong": {
                "name": "Đăng ký thường trú thông thường",
                "description": "Áp dụng cho công dân đăng ký thường trú thông thường",
                "required_documents": [
                    {
                        "name": "Tờ khai thay đổi thông tin cư trú",
                        "code": "CT01",
                        "file_type": "form",
                        "required": True,
                        "quantity": {
                            "original": 1,
                            "copy": 0
                        }
                    }
                ]
            }
        }
    }
}

def get_procedure_list():
    """Trả về danh sách các thủ tục dưới dạng dict (id, name)"""
    return [{"id": k, "name": v["name"]} for k, v in PROCEDURES.items()]

def get_procedure_cases(procedure_id):
    """Trả về danh sách các trường hợp của một thủ tục"""
    if procedure_id in PROCEDURES:
        return [{"id": k, "name": v["name"]} for k, v in PROCEDURES[procedure_id]["cases"].items()]
    return []

def get_required_documents(procedure_id, case_id):
    """Trả về danh sách giấy tờ cần thiết cho một trường hợp cụ thể"""
    if procedure_id in PROCEDURES and case_id in PROCEDURES[procedure_id]["cases"]:
        return PROCEDURES[procedure_id]["cases"][case_id]["required_documents"]
    return []

def get_procedure_details(procedure_id, case_id=None):
    """Trả về thông tin chi tiết về thủ tục/trường hợp"""
    if procedure_id not in PROCEDURES:
        return None
        
    result = {
        "id": procedure_id,
        "name": PROCEDURES[procedure_id]["name"],
        "description": PROCEDURES[procedure_id]["description"],
    }
    
    if case_id and case_id in PROCEDURES[procedure_id]["cases"]:
        result["case"] = {
            "id": case_id,
            "name": PROCEDURES[procedure_id]["cases"][case_id]["name"],
            "description": PROCEDURES[procedure_id]["cases"][case_id]["description"],
            "required_documents": PROCEDURES[procedure_id]["cases"][case_id]["required_documents"]
        }
    
    return result 