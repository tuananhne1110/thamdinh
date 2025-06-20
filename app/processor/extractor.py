import os
import cv2
import numpy as np
import pytesseract
from paddleocr import PaddleOCR
from PIL import Image
import pdf2image
from typing import Dict, List, Optional, Tuple, Any
import docx2txt
import re
from docx import Document
from docx.document import Document as _Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from PyPDF2 import PdfReader
import tempfile
from .llm import LLMExtractor
from concurrent.futures import ThreadPoolExecutor
import logging
import paddle
import time

# Set up logging (change level to logging.INFO or WARNING in production)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def profile_time(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[PROFILE] {func.__qualname__} took {elapsed:.3f}s")
        return result
    return wrapper

class OCRPipeline:
    def __init__(self):
        # Create processing directory inside uploads directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.uploads_dir = os.path.join(self.base_dir, "uploads")
        self.processing_dir = os.path.join(self.uploads_dir, "processing")
        
        # Create directories if they don't exist
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.processing_dir, exist_ok=True)
        
        # Define file paths
        self.file_image = os.path.join(self.processing_dir, "image.png")
        self.file_without_table = os.path.join(self.processing_dir, "without_table.png")
        self.file_without_ids_table = os.path.join(self.processing_dir, "without_ids_table.png")
        self.file_contour_table = os.path.join(self.processing_dir, "contour_table.png")
        self.file_contour_ids = os.path.join(self.processing_dir, "contour_ids.png")
        self.file_cropped_table = os.path.join(self.processing_dir, "cropped_table.png")
        self.file_cropped_ids = [os.path.join(self.processing_dir, f"cropped_id_{i}.png") for i in range(2)]
        
        # Initialize OCR engine
        # PaddleOCR 3.x: KHÔNG truyền use_gpu vào constructor
        self.ocr_engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang='vi'
        )
        # Log thiết bị Paddle đang sử dụng
        logger.warning(f"[Paddle] Using device: {paddle.get_device()}")

    @profile_time
    def process_file(self, file_path: str) -> str:
        try:
            # Ensure processing directory exists
            os.makedirs(self.processing_dir, exist_ok=True)
            
            # Verify file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Input file not found: {file_path}")
            
            ext = os.path.splitext(file_path)[1].lower()
            images = []
            if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                images = [file_path]
            elif ext == '.pdf':
                images = self._pdf_to_images(file_path)
            elif ext in ['.doc', '.docx']:
                images = self._docx_to_images(file_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            
            # Song song hóa OCR nhiều ảnh/trang
            with ThreadPoolExecutor() as executor:
                all_text = list(executor.map(self._ocr_pipeline_on_image, images))
            return '\n'.join(all_text)
        except Exception as e:
            logger.error(f"Error in process_file: {str(e)}")
            raise

    @profile_time
    def _pdf_to_images(self, pdf_path: str):
        from pdf2image import convert_from_path
        pil_images = convert_from_path(pdf_path, dpi=200)  # Giảm DPI để tăng tốc
        image_paths = []
        for idx, img in enumerate(pil_images):
            out_path = os.path.join(self.processing_dir, f"pdf_page_{idx}.png")
            img.save(out_path)
            image_paths.append(out_path)
        return image_paths

    @profile_time
    def _docx_to_images(self, docx_path: str):
        # Chuyển docx thành text, render text ra ảnh trắng đen đơn giản (tạm thời)
        # Nếu muốn đẹp hơn thì dùng giải pháp render docx->pdf->image
        text = docx2txt.process(docx_path)
        from PIL import ImageDraw, ImageFont
        img = Image.new('RGB', (1654, 2339), color='white')  # A4 300dpi
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = None
        d.text((10,10), text, fill=(0,0,0), font=font)
        out_path = os.path.join(self.processing_dir, "docx_page_0.png")
        img.save(out_path)
        return [out_path]

    @profile_time
    def _ocr_pipeline_on_image(self, image_path: str) -> str:
        # Áp dụng pipeline crop_table, crop_ids, ocr_without_ids_table, ocr_ids, ocr_table
        self.crop_table(image_path)
        self.crop_ids()
        text_body = self.ocr_without_ids_table()
        text_ids = self.ocr_ids()
        text_table = self.ocr_table()
        return text_ids + "\n" + text_body + "\n" + text_table

    # Các hàm crop_table, crop_ids, ocr_without_ids_table, ocr_ids, ocr_table, merge_boxes_line_by_line, boxes_to_rect, merge_rects_in_line, merge_group giữ nguyên như ocr.py
    @profile_time
    def crop_table(self, filename):
        img = cv2.imread(filename)
        img = self._resize_image_if_needed(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_h, iterations=2)
        vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_v, iterations=2)
        table_mask = cv2.add(horizontal_lines, vertical_lines)
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        found = False
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 50 and h > 50:
                table_roi = img[y:y + h, x:x + w]
                # Ghi file cho PaddleOCR predict table
                self.cropped_table_path = self._write_temp_image(table_roi, 'cropped_table.png')
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                cv2.drawContours(mask, [contour], -1, color=255, thickness=cv2.FILLED)
                img_without_table = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
                mask_bottom = np.zeros_like(gray)
                height, _ = gray.shape
                mask_bottom[y + h :, :] = 25
                inpainted = cv2.inpaint(img_without_table, mask_bottom, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
                self.img_without_table = inpainted
                found = True
                break
        if not found:
            self.img_without_table = img
            self.cropped_table_path = None

    @profile_time
    def crop_ids(self):
        img = self.img_without_table
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bin_img = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
        horizontal = bin_img.copy()
        horizontal_size = horizontal.shape[1] // 20
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
        horizontal = cv2.erode(horizontal, h_kernel)
        horizontal = cv2.dilate(horizontal, h_kernel)
        contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bounding_boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            bounding_boxes.append((x, y, w, h))
        sorted_boxes = sorted(bounding_boxes, key=lambda b: b[1] + b[3] // 2)
        dy_pairs = []
        for i in range(len(sorted_boxes) - 1):
            box1 = sorted_boxes[i]
            box2 = sorted_boxes[i + 1]
            y1_center = box1[1] + box1[3] // 2
            y2_center = box2[1] + box2[3] // 2
            dy = abs(y2_center - y1_center)
            dy_pairs.append((dy, box1, box2))
        dy_pairs = sorted(dy_pairs, key=lambda x: x[0])
        top_2_pairs = dy_pairs[:2]
        self.cropped_ids_paths = []
        found = False
        for idx, (_, b1, b2) in enumerate(top_2_pairs):
            x1 = min(b1[0], b2[0])
            x2 = max(b1[0] + b1[2], b2[0] + b2[2])
            y1 = min(b1[1], b2[1])
            y2 = max(b1[1] + b1[3], b2[1] + b2[3])
            cropped = img[y1:y2, x1:x2]
            # Ghi file cho PaddleOCR predict số định danh
            path = self._write_temp_image(cropped, f'cropped_id_{idx}.png')
            self.cropped_ids_paths.append(path)
            img[y1:y2, x1:x2] = 255
            found = True
        self.img_without_ids_table = img

    @profile_time
    def ocr_without_ids_table(self):
        img = self.img_without_ids_table
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(
            gray,
            lang="vie",
            config="--oem 3 --psm 6 -l vie textord_heavy_nr=1"
        )
        return text

    @profile_time
    def ocr_table(self):
        path = getattr(self, 'cropped_table_path', None)
        if path is None:
            return ''
        ocr_result = self.ocr_engine.predict(input=path)
        img = cv2.imread(path)
        boxes = ocr_result[0]["rec_polys"]
        merged_boxes = self.merge_boxes_line_by_line(boxes)
        cropped_images = []
        for box in merged_boxes:
            x1, y1, x2, y2 = box
            cropped = img[y1:y2, x1:x2]
            cropped_images.append(cropped)
        text_table = ""
        for img in cropped_images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            text_cell = pytesseract.image_to_string(
                gray,
                lang="vie",
                config="--oem 3 --psm 6 -l vie textord_heavy_nr=1"
            )
            text_table += "\n" + text_cell.strip()
        return text_table

    @profile_time
    def ocr_ids(self):
        text_ids = ""
        for idx, path in enumerate(getattr(self, 'cropped_ids_paths', [])):
            if idx == 0:
                text_ids += "\n4. Số định danh cá nhân: "
            else:
                text_ids += "\n9. Số định danh cá nhân của chủ hộ: "
            ocr_result = self.ocr_engine.predict(input=path)
            for number in ocr_result[0]["rec_texts"]:
                text_ids += number
        return text_ids

    def merge_boxes_line_by_line(self, boxes, x_thresh=10, y_thresh=10):
        rects = self.boxes_to_rect(boxes)
        rects = sorted(rects, key=lambda r: (r[1] + r[3]) // 2)
        merged = []
        current_line = []
        for rect in rects:
            if not current_line:
                current_line.append(rect)
                continue
            y_center = (rect[1] + rect[3]) // 2
            last_y_center = (current_line[0][1] + current_line[0][3]) // 2
            if abs(y_center - last_y_center) < y_thresh:
                current_line.append(rect)
            else:
                merged += self.merge_rects_in_line(current_line, x_thresh)
                current_line = [rect]
        if current_line:
            merged += self.merge_rects_in_line(current_line, x_thresh)
        return np.array(merged, dtype=np.int32)

    def boxes_to_rect(self, boxes):
        rects = []
        for box in boxes:
            x_min = box[:, 0].min()
            y_min = box[:, 1].min()
            x_max = box[:, 0].max()
            y_max = box[:, 1].max()
            rects.append([x_min, y_min, x_max, y_max])
        return np.array(rects, dtype=np.int32)

    def merge_rects_in_line(self, rects, x_thresh):
        rects = sorted(rects, key=lambda r: r[0])
        merged = []
        group = [rects[0]]
        for i in range(1, len(rects)):
            if rects[i][0] - group[-1][2] < x_thresh:
                group.append(rects[i])
            else:
                merged.append(self.merge_group(group))
                group = [rects[i]]
        if group:
            merged.append(self.merge_group(group))
        return merged

    def merge_group(self, group):
        x1 = min(r[0] for r in group)
        y1 = min(r[1] for r in group)
        x2 = max(r[2] for r in group)
        y2 = max(r[3] for r in group)
        return [x1, y1, x2, y2]

    def _resize_image_if_needed(self, img, max_side=2000):
        h, w = img.shape[:2]
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        return img

    def _write_temp_image(self, img, filename):
        # Ghi file vào thư mục processing (có thể dùng tempfile nếu muốn tự động xóa)
        path = os.path.join(self.processing_dir, filename)
        cv2.imwrite(path, img)
        return path

class DocumentExtractor:
    def __init__(self):
        self.ocr_pipeline = OCRPipeline()
        self.llm_extractor = LLMExtractor()

    def extract_text(self, file_path: str, use_llm: bool = True) -> Tuple[str, Dict]:
        text = self.ocr_pipeline.process_file(file_path)
        if use_llm:
            structured_text = self.llm_extractor(text)
            data = self._analyze_structure(structured_text)
        else:
            structured_text = text
            data = {}
        return structured_text, data

    def _analyze_structure(self, text: str) -> Dict:
        data = {
            "type": "unknown",
            "fields": {},
            "metadata": {}
        }
        # # Parse các trường từ text dạng "key: value"
        # for line in text.split('\n'):
        #     if ':' in line:
        #         key, value = line.split(':', 1)
        #         data["fields"][key.strip()] = value.strip()
        print("Structured Data:", data)
        return data