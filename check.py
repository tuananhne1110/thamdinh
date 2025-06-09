import cv2
import pytesseract
from paddleocr import PaddleOCR
import numpy as np
import argparse  # Thêm import argparse

# Hàm tiền xử lý ảnh
def preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Không thể đọc ảnh từ đường dẫn cung cấp")
    
    # Chuyển sang ảnh xám
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Tăng độ tương phản
    gray = cv2.equalizeHist(gray)
    
    # Ngưỡng thích nghi với tham số động
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5)
    
    # Khử nhiễu
    denoised = cv2.fastNlMeansDenoising(thresh, None, 20, 7, 21)
    return denoised

# Hàm gộp các vùng văn bản gần nhau
def merge_regions(regions, threshold=10):
    merged = []
    for i, (x1, y1, x2, y2) in enumerate(regions):
        if not merged:
            merged.append([x1, y1, x2, y2])
        else:
            merged_box = merged[-1]
            if abs(y1 - merged_box[3]) < threshold and abs(x1 - merged_box[2]) < threshold:
                merged_box[2] = max(merged_box[2], x2)
                merged_box[3] = max(merged_box[3], y2)
            else:
                merged.append([x1, y1, x2, y2])
    return [(x1, y1, x2, y2) for x1, y1, x2, y2 in merged]

# Hàm nhận diện văn bản cho các vùng tự động phát hiện
def ocr_on_detected_regions(image_path):
    # Khởi tạo PaddleOCR một lần
    ocr = PaddleOCR(use_angle_cls=True, lang='vi', show_log=False)
    
    # Tiền xử lý ảnh
    processed_img = preprocess_image(image_path)
    
    # Phát hiện vùng văn bản
    result = ocr.ocr(image_path, cls=True)
    if not result or not result[0]:
        print("Không phát hiện được vùng văn bản nào")
        return
    
    # Lấy và gộp vùng văn bản
    regions = [(int(line[0][0][0]), int(line[0][0][1]), int(line[0][2][0]), int(line[0][2][1])) 
               for line in result[0]]
    regions = merge_regions(regions)
    
    # Nhận diện văn bản bằng PaddleOCR
    for (x_min, y_min, x_max, y_max) in regions:
        roi = processed_img[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            continue
        result = ocr.ocr(roi, cls=True)
        text = result[0][1][0] if result and result[0] else ""
        print(f"Vùng ({x_min}, {y_min}, {x_max}, {y_max}): {text}")

# Hàm phân tích đối số dòng lệnh
def parse_args():
    parser = argparse.ArgumentParser(description="OCR tự động nhận diện văn bản")
    parser.add_argument("image_path", help="Đường dẫn ảnh cần nhận diện văn bản")
    return parser.parse_args()

# Hàm chính
def main():
    args = parse_args()  # Gọi hàm parse_args
    try:
        ocr_on_detected_regions(args.image_path)
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()