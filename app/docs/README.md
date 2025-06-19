# Tài liệu Thiết kế hệ thống xử lý Hồ sơ Cư trú

## 1. Tổng quan hệ thống

**Mục tiêu**
Tự động hóa quy trình xử lý hồ sơ cư trú từ file giấy/tài liệu scan đến kiểm tra hợp lệ và sinh biểu mẫu

**Luồng xử lý chính**
`Upload → OCR → Extract → Validate → DB Check → Form Generation → Response`

----

## 2. Kiến trúc tổng thể

### 2.1 Sơ đồ kiến trúc
![QuyTrinh_DangKy_TamTru-Page-14 drawio (1)](https://github.com/user-attachments/assets/ea29bb9f-8cdc-44f0-9c8c-7d3d4844ee0e)

### 2.2 Các thành phần chính

| Module                 | Mô tả                                                                      |
|------------------------|----------------------------------------------------------------------------|
| Input Processing       | Nhận file đầu vào, phân loại định dạng và OCR để lấy text thô              |
| Information Extraction | Trích xuất thông tin từ text sử dụng template, LLM và rule engine          |
| Field Validator        | Kiểm tra định dạng, logic, đối chiếu các trường thông tin giữa các văn bản |
| Database Check         | So sánh dữ liệu với CSDL dân cư                                            |
| Form Generator         | Tạo biểu mẫu CT04/CT05 tự động từ dữ liệu đã xác thực                      |

## 3 Mô tả chi tiết từng Module 

### 3.1 Input Processing Module
 - Input .pdf, .jpg, .png, .docx, .doc
 - Xử lý:
    + File Classifier: Phân loại file đầu vào theo định dạng
    + OCR Pipeline: Dùng PaddleOCR / Tesseract để trích xuất văn bản
    + Text Preprocessor: Clean text, Chuẩn hóa định dạng
 - Output: Text + metadata (Loại tài liệu, độ tin cậy,... )   

### 3.2 Information Extraction Module 
 - Input: Text thô từ OCR
 - Xử lý: 
    + Template Matcher: Ánh xạ nội dung theo biểu mẫu (CT01, CT02,...)
    + LLM Extractor: Dùng LLLM để suy luận và trích xuất thông tin phức tạp
    + Rule Engine: Áp dụng regex và rule để định dạng & validate dữ liệu
 - Output: Dữ liệu structured dạng JSON

 - Ví dụ dữ liệu đầu ra của module Extraction: 
      {
      "ho_ten_nguoi_ke_khai": "Nguyễn Văn A",
      "ngay_sinh": "01/01/1990",
      "gioi_tinh": "Nam",
      "so_dinh_danh": "123456789012",
      "so_dien_thoai": "0901123123",
      "email": "nguyenvana@gmail.com"
      }

### 3.3 Validation Module
 - Kiểm tra:
    + Format Validator: Các trường số định danh, địa chỉ, ...
    + Logic Validator: Quan hệ nhân thân, số điện thoại, ...
    + Cross-Reference: So sánh dữ liệu trích xuất giữa các file trong hồ sơ
 - Output: JSON trạng thái từng trường + Tổng trạng thái hồ sơ

 - Ví dụ dữ liệu Validation:
      {
      "ho_ten_nguoi_ke_khai": "Hợp lệ",
      "ngay_sinh": "Hợp lệ",
      "so_dinh_danh": "Hợp lệ",
      "so_dien_thoai": "Không hợp lệ"
      }

### 3.4 Database Check Module
 - So sánh với CSDL dân cư 
 - Xử lý
    + Database Service: Truy vấn CSDL
    + Match Service: So khớp thông tin 
 - Output: Log so sánh + kết quả xác thực
 - Ví dụ output so khớp Database:
 
### 3.5 Form Generator Module
 - Xử lý
    + Template Engine: Chọn mẫu phù hợp (CT04/CT05)
    + Form Builder: Tự động điền thông tin đã xác thực vào biểu mẫu
    + Output Handler: Xuất file Word và lưu trữ hệ thống
 - Output: File biểu mẫu CT04/CT05 + log metadata

# 4 Các trường dữ liệu trong hệ thống

## 4.1 Thông tin cơ bản người kê khai

| Trường                   | Kiểu dữ liệu  | Mô tả                                            |
|--------------------------|---------------|--------------------------------------------------|
| **ho_ten_nguoi_ke_khai** |string         | Họ và tên người kê khai                          |                                   
| **ngay_sinh**            |string         | Ngày tháng năm sinh                              |                                       
| **gioi_tinh**            |string         | Nam/Nữ                                           |                              
| **so_dinh_danh**         |string         | CCCD/CMND (12 số)                                |                                         
| **so_dien_thoai**        |string         | Số điện thoại liên hệ (10 số bắt đầu bằng số 0)  |              
| **email**                |string         | Email liên hệ                                    |

## 4.2 Thông tin chủ hộ

**Thông tin chủ hộ**

| Trường                   | Kiểu dữ liệu  | Mô tả                                      |
|--------------------------|---------------|--------------------------------------------|
| **ho_ten_chu_ho**        |string         | Họ, chữ đệm và tên chủ hộ                  |
| **so_dinh_danh_chu_ho**  |string         | CCCD/CMND chủ hộ (12 số)                   |
| **quan_he_voi_chu_ho**   |string         | Quan hệ với chủ hộ, thuộc QUAN_HE_HOP_PHAP | 

**Danh sách quan hệ hợp lệ**
QUAN_HE_HOP_LE_VOI_CHU_HO = {
    "vợ", "chồng", "con", "con ruột", "con nuôi", 
    "cha", "bố", "mẹ", "cháu ruột",
    "anh", "chị", "em", "ông", "bà", 
    "người ở thuê", "người ở nhờ",... }

## 4.3 Thông tin hành chính

| Trường                   | Kiểu dữ liệu  | Mô tả                                        |
|--------------------------|---------------|----------------------------------------------|
| **ten_co_quan_dang_ky**  |string         | Cơ quan xử lý thủ tục (bắt đầu bằng Công An) |
| **loai_giay_to**         |string         | Loại giấy tờ nộp                             |
| **ma_ho_so**             |string         | Mã hồ sơ                                     |

## 4.4 Thông tin thành viên

| Trường                            | Kiểu dữ liệu  | Mô tả                                            |
|-----------------------------------|---------------|--------------------------------------------------|
| **ho_ten**                        |string         | Họ và tên thành viên                             |                                   
| **ngay_sinh**                     |string         | Ngày tháng năm sinh                              |                                       
| **gioi_tinh**                     |string         | Nam/Nữ                                           |                              
| **so_dinh_danh**                  |string         | CCCD/CMND (12 số)                                |                                         
| **quan_he_voi_nguoi_co_thay_doi** |string         | Quan hệ với chủ hộ, thuộc QUAN_HE_HOP_PHAP       |              

# 5 Bảng các API chính

| Endpoint                   | Method | Chức năng                        | Đầu vào               | Đầu ra        |
|----------------------------|--------|----------------------------------|-----------------------|---------------|
|  /upload                   | POST   | Nhận hồ sơ, trích xuất dữ liệu   | file, thông tin hồ sơ |	JSON/status   |
|  /process                  | POST   | So sánh checklist giấy tờ        | session, file info	 | checklist     |
|  /verify                   | POST   | Thẩm định từng trường thông tin  | fields, DB	          | status        |
|  /finalize                 | POST   | Sinh form CT04/CT05, lưu kết quả | fields, status	       | file + status |
|  /api/required_documents   | GET    | Lấy danh mục giấy tờ cần nộp     | procedure, case	    | JSON giấy tờ  |
|  /api/cases/{procedure_id} | GET    | Lấy danh sách case theo thủ tục  | procedure_id          | JSON          |
|  /cases                    | GET    | Danh sách hồ sơ đã xử lý         |                       | HTML/JSON     |
|  /cases/{case_id}          | GET    | Chi tiết từng hồ sơ, trạng thái  | case_id	             | HTML/JSON     |

















