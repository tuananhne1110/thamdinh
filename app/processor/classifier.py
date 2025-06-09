from ultralytics import YOLO

def classify_document(text):
    if "Giấy xác nhận" in text:
        return "giay_xac_nhan"
    elif "Đơn xin tạm trú" in text:
        return "don_xin_tam_tru"
    elif "Căn cước công dân" in text or "CMND" in text:
        return "cmt_cccd"
    elif "Sổ hộ khẩu" in text:
        return "so_ho_khau"
    return "khac"


try:
    model = YOLO(r'app\models\best.pt')
    print("Model loaded successfully!")
    print("Model classes:", model.names)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None