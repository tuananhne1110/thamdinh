import re
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

# Cơ quan đăng ký cư trú
def kiem_tra_ten_co_quan_dang_ky(co_quan: str) -> str:
    xa_phuong_thi_tran = any(x in co_quan for x in ["xã", "phường", "thị trấn"])
    huyen_thanhpho = any(x in co_quan for x in ["quận", "huyện", "thị xã", "thành phố"])
    if not co_quan.startswith("công an"):
        return "Tên cơ quan phải bắt đầu bằng 'Công an'"
    elif not (xa_phuong_thi_tran or huyen_thanhpho):
        return "Tên cơ quan phải có cấp hành chính (xã, phường, thị trấn, quận, huyện, thị xã, thành phố)"
    else:
        return "Đạt"

def validate_ho_ten(ho_ten: str) -> str:
    print("[DEBUG] validate_ho_ten input:", repr(ho_ten))
    ho_ten = ho_ten.strip()
    parts = ho_ten.split()
    if not ho_ten:
        print("[DEBUG] validate_ho_ten: empty")
        return "Họ tên không được để trống"
    if len(ho_ten) < 3:
        print("[DEBUG] validate_ho_ten: quá ngắn")
        return "Họ tên quá ngắn"
    if len(parts) < 2:
        print("[DEBUG] validate_ho_ten: ít hơn 2 từ")
        return "Họ tên phải có ít nhất 2 từ"
    if not re.fullmatch(r"[a-zA-ZÀ-ỹ\s'-]+", ho_ten):
        print("[DEBUG] validate_ho_ten: regex không khớp", repr(ho_ten))
        return "Họ tên chứa ký tự không hợp lệ"
    print("[DEBUG] validate_ho_ten: Đạt")
    return "Đạt"

def validate_gioi_tinh(gioi_tinh: str) -> str:
    if not gioi_tinh:
        return "Giới tính không được để trống"
    elif gioi_tinh in ["nam", "nữ"]:
        return "Đạt"
    else:
        return "Giới tính phải là 'nam' hoặc 'nữ'"

def validate_ngay_thang(date_str: str, fmt: str = "%d/%m/%Y") -> Tuple[bool, str]:
    if not date_str or date_str.strip() == "":
        return False, "Ngày sinh không được để trống"
    try:
        datetime.strptime(date_str, fmt)
        return True, "Đạt"
    except ValueError:
        return False, "Ngày sinh không đúng định dạng dd/mm/yyyy"

def is_valid_cmnd_or_sdd(value: str) -> bool:
    return bool(re.fullmatch(r"\d{12}$", value))

def is_valid_phone(phone: str) -> bool:
    return bool(re.match(r"^0(3[2-9]|5[6|8|9]|7[0|6-9]|8[1-6|8|9]|9[0-9])\d{7}$", phone))

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)*\.[a-zA-Z]{2,}$", email))

def tinh_tuoi(ngay_sinh: str) -> int:
    try:
        dob = datetime.strptime(ngay_sinh, "%d/%m/%Y")
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return -1

def kiem_tra_so_dinh_danh(ngay_sinh: str, so_dinh_danh: str) -> str:
    so_dinh_danh = so_dinh_danh.strip()
    tuoi = tinh_tuoi(ngay_sinh)
    if tuoi == -1:
        return "Không xác định được tuổi"
    if tuoi >= 14:
        if not is_valid_cmnd_or_sdd(so_dinh_danh):
            return "Số định danh phải đủ 12 số cho người từ 14 tuổi trở lên"
        else:
            return "Đạt"
    else:
        if so_dinh_danh and not is_valid_cmnd_or_sdd(so_dinh_danh):
            return "Số định danh phải đủ 12 số nếu có"
        else:
            return "Đạt"

def kiem_tra_ngay_sinh_va_so_dinh_danh(ngay_sinh: str, so_dinh_danh: str) -> Tuple[str, str]:
    is_valid_date, msg_date = validate_ngay_thang(ngay_sinh)
    if not is_valid_date:
        return msg_date, ""
    msg_sdd = kiem_tra_so_dinh_danh(ngay_sinh, so_dinh_danh)
    return msg_date, msg_sdd

QUAN_HE_HOP_LE_VOI_CHU_HO = {
    "vợ", "chồng", "con", "con ruột", "con nuôi", "cha",  "bố", "mẹ", "cháu ruột",
    "anh", "chị", "em", "ông", "bà", "người ở thuê", "người ở nhờ",
    "người ở mượn", "cùng ở thuê", "cùng ở nhờ", "cùng ở mượn",
    "bạn bè ở chung", "người giúp việc", "người chăm sóc",
    "người giám hộ", "người được giám hộ",
    "ông nội", "bà nội", "ông ngoại", "bà ngoại",
    "cô", "dì", "chú", "bác",
    "cháu"
}

def kiem_tra_thong_tin_chu_ho(ho_ten_chu_ho: str, quan_he_voi_chu_ho: str, so_dinh_danh_chu_ho: str, ho_ten_nguoi_ke_khai: str, so_dinh_danh: str) -> dict:
    ket_qua = {}
    ket_qua["Họ tên chủ hộ"] = validate_ho_ten(ho_ten_chu_ho)
    la_trung_ten = ho_ten_chu_ho.lower() == ho_ten_nguoi_ke_khai.lower()
    if not quan_he_voi_chu_ho:
        ket_qua["Quan hệ với chủ hộ"] = "Không được để trống"
    elif quan_he_voi_chu_ho == "chủ hộ":
        ket_qua["Quan hệ với chủ hộ"] = "Đạt"
    elif quan_he_voi_chu_ho in QUAN_HE_HOP_LE_VOI_CHU_HO:
        ket_qua["Quan hệ với chủ hộ"] = "Đạt"
    else:
        ket_qua["Quan hệ với chủ hộ"] = "Quan hệ không hợp lệ"
    if la_trung_ten and so_dinh_danh_chu_ho == so_dinh_danh and quan_he_voi_chu_ho != "chủ hộ":
        ket_qua["Quan hệ với chủ hộ"] = "Nếu tên và số định danh trùng thì quan hệ phải là 'chủ hộ'"
    if not so_dinh_danh_chu_ho:
        ket_qua["Số định danh chủ hộ"] = "Không được để trống"
    elif so_dinh_danh_chu_ho == so_dinh_danh:
        ket_qua["Số định danh chủ hộ"] = "Trùng với số định danh người kê khai"
    elif quan_he_voi_chu_ho == "chủ hộ":
        ket_qua["Số định danh chủ hộ"] = "Đạt"
    elif is_valid_cmnd_or_sdd(so_dinh_danh_chu_ho):
        ket_qua["Số định danh chủ hộ"] = "Đạt"
    else:
        ket_qua["Số định danh chủ hộ"] = "Số định danh chủ hộ không hợp lệ"
    return ket_qua

def get_field_value(fields: dict, key: str, previous_value: str = "") -> str:
    """Get normalized value from fields dict, fallback to previous value if empty"""
    value = fields.get(key, "")
    if isinstance(value, dict):
        value = str(value.get("value", "")).strip()
    else:
        value = str(value).strip()
    return value if value else previous_value

def map_ocr_to_hoso(ocr_data: dict) -> dict:
    """Map OCR data to validator format"""
    print("[DEBUG] map_ocr_to_hoso input:", ocr_data)
    
    # Lấy giá trị từ lần đầu nếu có
    previous_values = {
        "ten_co_quan_dang_ky": ocr_data.get("previous_ten_co_quan_dang_ky", ""),
        "ho_ten_nguoi_ke_khai": ocr_data.get("previous_ho_ten_nguoi_ke_khai", ""),
        "ngay_sinh": ocr_data.get("previous_ngay_sinh", ""),
        "gioi_tinh": ocr_data.get("previous_gioi_tinh", ""),
        "so_dinh_danh": ocr_data.get("previous_so_dinh_danh", ""),
        "so_dien_thoai": ocr_data.get("previous_so_dien_thoai", ""),
        "email": ocr_data.get("previous_email", ""),
        "ho_ten_chu_ho": ocr_data.get("previous_ho_ten_chu_ho", ""),
        "quan_he_voi_chu_ho": ocr_data.get("previous_quan_he_voi_chu_ho", ""),
        "so_dinh_danh_chu_ho": ocr_data.get("previous_so_dinh_danh_chu_ho", ""),
        "noi_dung_de_nghi": ocr_data.get("previous_noi_dung_de_nghi", "")
    }
    
    mapped = {
        "ten_co_quan_dang_ky": get_field_value(ocr_data, "Tên cơ quan đăng ký cư trú", previous_values["ten_co_quan_dang_ky"]),
        "ho_ten_nguoi_ke_khai": get_field_value(ocr_data, "Họ, chữ đệm và tên", previous_values["ho_ten_nguoi_ke_khai"]),
        "ngay_sinh": get_field_value(ocr_data, "Ngày, tháng, năm sinh", previous_values["ngay_sinh"]),
        "gioi_tinh": get_field_value(ocr_data, "Giới tính", previous_values["gioi_tinh"]).lower(),
        "so_dinh_danh": get_field_value(ocr_data, "Số định danh cá nhân", previous_values["so_dinh_danh"]),
        "so_dien_thoai": get_field_value(ocr_data, "Số điện thoại", previous_values["so_dien_thoai"]),
        "email": get_field_value(ocr_data, "Email", previous_values["email"]),
        "ho_ten_chu_ho": get_field_value(ocr_data, "Họ, chữ đệm và tên chủ hộ", previous_values["ho_ten_chu_ho"]),
        "quan_he_voi_chu_ho": get_field_value(ocr_data, "Quan hệ với chủ hộ", previous_values["quan_he_voi_chu_ho"]).lower(),
        "so_dinh_danh_chu_ho": get_field_value(ocr_data, "Số định danh cá nhân của chủ hộ", previous_values["so_dinh_danh_chu_ho"]),
        "noi_dung_de_nghi": get_field_value(ocr_data, "Nội dung đề nghị", previous_values["noi_dung_de_nghi"]),
        "thanh_vien_thay_doi": [
            {
                "ho_ten": get_field_value(tv, "Họ, chữ đệm và tên"),
                "ngay_sinh": get_field_value(tv, "Ngày, tháng, năm sinh"),
                "gioi_tinh": get_field_value(tv, "Giới tính").lower(),
                "so_dinh_danh": get_field_value(tv, "Số định danh cá nhân"),
                "quan_he_voi_chu_ho": get_field_value(tv, "Quan hệ với chủ hộ").lower()
            }
            for tv in ocr_data.get("Những thành viên trong hộ gia đình cùng thay đổi", [])
        ]
    }
    print("[DEBUG] map_ocr_to_hoso output:", mapped)
    return mapped

def validate_thanh_vien(thanh_vien: dict) -> dict:
    result = {}
    ho_ten = thanh_vien.get("ho_ten", "").strip()
    result["Họ, chữ đệm và tên"] = validate_ho_ten(ho_ten)
    ngay_sinh = thanh_vien.get("ngay_sinh", "").strip()
    so_dinh_danh = thanh_vien.get("so_dinh_danh", "").strip()
    msg_ngay_sinh, msg_sdd = kiem_tra_ngay_sinh_va_so_dinh_danh(ngay_sinh,so_dinh_danh)
    result["Ngày sinh"] = msg_ngay_sinh
    gioi_tinh = thanh_vien.get("gioi_tinh","").strip().lower()
    result["Giới tính"] = validate_gioi_tinh(gioi_tinh)
    result["Số định danh cá nhân"] = msg_sdd
    qh_chu_ho = thanh_vien.get("quan_he_voi_chu_ho", "").strip().lower()
    if not qh_chu_ho:
        result["Quan hệ với chủ hộ"] = "Không được để trống"
    elif qh_chu_ho not in QUAN_HE_HOP_LE_VOI_CHU_HO:
        result["Quan hệ với chủ hộ"] = "Quan hệ không hợp lệ"
    else:
        result["Quan hệ với chủ hộ"] = "Đạt"
    return result

def normalize_name(name: str) -> str:
    return ' '.join(name.strip().lower().split())

def validate_ho_so(ho_so: dict) -> dict:
    print("[DEBUG] validate_ho_so input:", ho_so)
    ket_qua = {}
    co_quan = ho_so.get("ten_co_quan_dang_ky", "").lower().strip()
    ket_qua["Tên cơ quan đăng ký cư trú"] = kiem_tra_ten_co_quan_dang_ky(co_quan)
    ho_ten_nguoi_ke_khai = ho_so.get("ho_ten_nguoi_ke_khai", "")
    ket_qua["Họ tên người kê khai"] = validate_ho_ten(ho_ten_nguoi_ke_khai)
    ngay_sinh = ho_so.get("ngay_sinh", "").strip()
    so_dinh_danh = ho_so.get("so_dinh_danh","").strip()
    msg_ngay_sinh, msg_sdd = kiem_tra_ngay_sinh_va_so_dinh_danh(ngay_sinh, so_dinh_danh)
    ket_qua["Ngày sinh"] = msg_ngay_sinh
    gioi_tinh = ho_so.get("gioi_tinh","").strip().lower()
    ket_qua["Giới tính"] = validate_gioi_tinh(gioi_tinh)
    ket_qua["Số định danh cá nhân"] = msg_sdd
    phone = ho_so.get("so_dien_thoai", "")
    if not phone:
        ket_qua["Số điện thoại"] = "Không được để trống"
    elif not is_valid_phone(phone):
        ket_qua["Số điện thoại"] = "Số điện thoại không hợp lệ"
    else:
        ket_qua["Số điện thoại"] = "Đạt"
    email = ho_so.get("email", "")
    if email and not is_valid_email(email):
        ket_qua["Email"] = "Email không hợp lệ"
    else:
        ket_qua["Email"] = "Đạt"
    ho_ten_chu_ho = ho_so.get("ho_ten_chu_ho", "").strip()
    quan_he_voi_chu_ho = ho_so.get("quan_he_voi_chu_ho", "").strip().lower()
    so_dinh_danh_chu_ho = ho_so.get("so_dinh_danh_chu_ho", "").strip()
    ket_qua_chu_ho = kiem_tra_thong_tin_chu_ho(ho_ten_chu_ho, quan_he_voi_chu_ho, so_dinh_danh_chu_ho, ho_ten_nguoi_ke_khai, so_dinh_danh)
    ket_qua.update(ket_qua_chu_ho)
    ds_tv = ho_so.get("thanh_vien_thay_doi", [])
    ket_qua["Thành viên thay đổi"] = []
    for i, tv in enumerate(ds_tv):
        ket_qua["Thành viên thay đổi"].append(validate_thanh_vien(tv))
    print("[DEBUG] validate_ho_so output:", ket_qua)
    return ket_qua

def validate_ho_so_from_ocr(ocr_data: dict) -> dict:
    ho_so_data = map_ocr_to_hoso(ocr_data)
    return validate_ho_so(ho_so_data)