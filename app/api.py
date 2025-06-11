from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict
from datetime import datetime
from app.processor.extractor import DocumentExtractor
from app.data.procedures import get_procedure_list, get_procedure_cases, get_required_documents, get_procedure_details
import os
# from app.classify import model as yolo_model
from app.processor.classifier import classify_document, model as yolo_model
from app.processor.validator import validate_ho_so_from_ocr  
from app.processor.filler import LLMFiller
from jinja2 import Template as JinjaTemplate

# Tạo FastAPI app
app = FastAPI(title="Hệ thống Cơ sở dữ liệu thẩm tra, thẩm định")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# Templates
templates = Jinja2Templates(directory="app/templates")

# Khởi tạo DocumentExtractor
document_extractor = DocumentExtractor()

# Khởi tạo LLMFiller
llm_filler = LLMFiller()

# Biến toàn cục để lưu trữ danh sách file đã upload
uploaded_files_info: List[Dict] = []

# Thêm biến toàn cục để sinh mã hồ sơ tự động
last_case_id = 0
case_id_current = None

procedures = [
    {"id": 1, "name": "Đăng ký tạm trú"},
    {"id": 2, "name": "Đăng ký thường trú"},
    {"id": 3, "name": "Cấp giấy chứng nhận"},
]

def get_field_value(f, key):
    v = f.get(key, "")
    if isinstance(v, dict):
        if 'value' in v:
            return v['value']
        else:
            print(f"[WARNING] Field '{key}' is dict but missing 'value' key: {v}")
            return ""
    if v is None:
        print(f"[WARNING] Field '{key}' is None")
        return ""
    return v

def map_predicted_class_to_dropdown_value(predicted_class):
    if not predicted_class:
        return "giay_to_khac"
    mapping = {
        "ct01": "to_khai",
        "to_khai": "to_khai",
        "don": "don",
        "cccd": "cmnd",
        "cmnd": "cmnd",
        "ho_khau": "ho_khau",
        "giay_khai_sinh": "giay_khai_sinh",
        "khac": "giay_to_khac",
        "giay_to_khac": "giay_to_khac"
    }
    return mapping.get(predicted_class.lower(), "giay_to_khac")

def get_checklist(classified_results, required_docs):
    print("Checking documents...")
    print("Required docs:", required_docs)
    print("Uploaded files:", classified_results)
    
    checklist = []
    for req in required_docs:
        found = False
        needs_review = False
        alternatives = req.get('alternatives', [])
        codes_to_check = [req.get('code')] + alternatives
        
        print(f"Checking requirement: {req['name']}")
        print(f"Accepted codes: {codes_to_check}")
        
        for result in classified_results:
            class_name = result.get('predicted_class')
            confidence = result.get('confidence', 0)
            
            print(f"Checking file with class: {class_name}, confidence: {confidence}")
            
            if class_name and class_name.lower() in [c.lower() for c in codes_to_check if c]:
                if confidence > 0.8:
                    found = True
                    print(f"Found matching document with high confidence")
                    break
                elif confidence > 0.5:
                    needs_review = True
                    print(f"Found matching document that needs review")
        
        status = 'matched' if found else ('needs_review' if needs_review else 'missing')
        checklist.append({
            'name': req['name'],
            'status': status
        })
        print(f"Status for {req['name']}: {status}")

    is_full = all(doc['status'] == 'matched' for doc in checklist)
    print(f"Final check - All documents present: {is_full}")
    return checklist, is_full

def get_missing_documents(required_docs, uploaded_files_info):
    uploaded_codes = set()
    for file in uploaded_files_info:
        code = (file.get('predicted_class') or '').lower()
        if code:
            uploaded_codes.add(code)
    missing_docs = []
    for req in required_docs:
        codes_to_check = [req.get('code', '')] + req.get('alternatives', [])
        if not any(code.lower() in uploaded_codes for code in codes_to_check if code):
            missing_docs.append(req['name'])
    return missing_docs

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def step_upload_get(request: Request):
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M")
    procedures = get_procedure_list()
    return templates.TemplateResponse("stepper/upload.html", {
        "request": request,
        "procedures": procedures,
        "today": today,
        "current_time": current_time
    })

@app.post("/upload")
async def step_upload_post(
    request: Request,
    procedure: Optional[str] = Form(None),
    case: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    process_description: Optional[str] = Form(None),
    comments: Optional[str] = Form(None),
    form_files: List[UploadFile] = File(None),
    related_files: List[UploadFile] = File(None)
):
    try:
        global uploaded_files_info, last_case_id, case_id_current
        uploaded_files_info = []  # Reset danh sách file
        files = []
        if form_files:
            files.extend(form_files)
        if related_files:
            files.extend(related_files)
        print("Tên các file nhận được (trước khi lọc):", [f.filename for f in files])
        # Loại bỏ file rỗng
        files = [f for f in files if f.filename]
        print("Tên các file thực sự xử lý (sau khi lọc):", [f.filename for f in files])
        print("Số file thực sự xử lý:", len(files))
        if not files:
            return templates.TemplateResponse("stepper/upload.html", {
                "request": request,
                "procedures": get_procedure_list(),
                "today": datetime.now().strftime("%Y-%m-%d"),
                "current_time": datetime.now().strftime("%H:%M"),
                "error": "Không có file nào được chọn"
            })
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        for file in files:
            if file.filename:
                file_path = os.path.join(upload_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                try:
                    # Extract text and structured data using OCR and LLM
                    text, data = document_extractor.extract_text(file_path)
                    
                    # PHÂN LOẠI TỰ ĐỘNG
                    ext = os.path.splitext(file.filename)[1][1:].lower()
                    predicted_class = None
                    confidence = None
                    if ext in ["jpg", "jpeg", "png"] and yolo_model is not None:
                        # Dùng YOLO
                        results = yolo_model(file_path)
                        if results and len(results) > 0:
                            result = results[0]
                            if hasattr(result, 'probs') and result.probs is not None:
                                top1_idx = result.probs.top1
                                confidence = float(result.probs.top1conf)
                                predicted_class = yolo_model.names[top1_idx]
                    else:
                        # Dùng text classifier
                        predicted_class = classify_document(text)
                        confidence = 1.0 if predicted_class != "khac" else 0.0
                    
                    dropdown_value = map_predicted_class_to_dropdown_value(predicted_class)
                    
                    # Parse structured text from LLM
                    structured_data = {}
                    if text:
                        lines = text.split('\n')
                        current_section = None
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Parse sections
                            if line.startswith('I. Loại giấy tờ:'):
                                structured_data['Loại giấy tờ'] = line.replace('I. Loại giấy tờ:', '').strip()
                            elif line.startswith('II. Kính gửi:'):
                                structured_data['Cơ quan tiếp nhận'] = line.replace('II. Kính gửi:', '').strip()
                            elif line.startswith('1. Họ và tên:'):
                                structured_data['Họ, chữ đệm và tên'] = line.replace('1. Họ và tên:', '').strip()
                            elif line.startswith('2. Ngày tháng năm sinh:'):
                                structured_data['Ngày tháng năm sinh'] = line.replace('2. Ngày tháng năm sinh:', '').strip()
                            elif line.startswith('3. Giới tính:'):
                                structured_data['Giới tính'] = line.replace('3. Giới tính:', '').strip()
                            elif line.startswith('4. Số định danh cá nhân:'):
                                structured_data['Số định danh cá nhân/CMND'] = line.replace('4. Số định danh cá nhân:', '').strip()
                            elif line.startswith('5. Số điện thoại liên hệ:'):
                                structured_data['Số điện thoại'] = line.replace('5. Số điện thoại liên hệ:', '').strip()
                            elif line.startswith('6. Email:'):
                                structured_data['Email'] = line.replace('6. Email:', '').strip()
                            elif line.startswith('7. Họ và tên chủ hộ:'):
                                structured_data['Họ và tên chủ hộ'] = line.replace('7. Họ và tên chủ hộ:', '').strip()
                            elif line.startswith('8. Mối quan hệ với chủ hộ:'):
                                structured_data['Mối quan hệ với chủ hộ'] = line.replace('8. Mối quan hệ với chủ hộ:', '').strip()
                            elif line.startswith('9. Số định danh cá nhân của chủ hộ:'):
                                structured_data['Số định danh cá nhân của chủ hộ'] = line.replace('9. Số định danh cá nhân của chủ hộ:', '').strip()
                            elif line.startswith('10. Nội dung đề nghị:'):
                                structured_data['Nội dung đề nghị'] = line.replace('10. Nội dung đề nghị:', '').strip()
                            elif line.startswith('11. Thông tin về thành viên trong hộ gia đình cùng thay đổi'):
                                current_section = 'family_members'
                                structured_data['family_members'] = []
                                member_info = {}
                                member_idx = 1
                            elif current_section == 'family_members':
                                # Parse family member information
                                if line.startswith(f'11.{member_idx}.1. Họ và tên:'):
                                    member_info['name'] = line.replace(f'11.{member_idx}.1. Họ và tên:', '').strip()
                                elif line.startswith(f'11.{member_idx}.2. Ngày tháng năm sinh:'):
                                    member_info['dob'] = line.replace(f'11.{member_idx}.2. Ngày tháng năm sinh:', '').strip()
                                elif line.startswith(f'11.{member_idx}.3. Giới tính:'):
                                    member_info['gender'] = line.replace(f'11.{member_idx}.3. Giới tính:', '').strip()
                                elif line.startswith(f'11.{member_idx}.4. Số định danh cá nhân:'):
                                    member_info['id_number'] = line.replace(f'11.{member_idx}.4. Số định danh cá nhân:', '').strip()
                                elif line.startswith(f'11.{member_idx}.5. Mối quan hệ với chủ hộ:'):
                                    member_info['relationship'] = line.replace(f'11.{member_idx}.5. Mối quan hệ với chủ hộ:', '').strip()
                                    # Đã đủ thông tin 1 thành viên, thêm vào structured_data
                                    prefix = f'Thành viên {member_idx}'
                                    if 'name' in member_info:
                                        structured_data[f'{prefix} - Họ và tên'] = member_info['name']
                                    if 'dob' in member_info:
                                        structured_data[f'{prefix} - Ngày sinh'] = member_info['dob']
                                    if 'gender' in member_info:
                                        structured_data[f'{prefix} - Giới tính'] = member_info['gender']
                                    if 'id_number' in member_info:
                                        structured_data[f'{prefix} - Số định danh cá nhân'] = member_info['id_number']
                                    if 'relationship' in member_info:
                                        structured_data[f'{prefix} - Mối quan hệ với chủ hộ'] = member_info['relationship']
                                    structured_data['family_members'].append(member_info)
                                    member_info = {}
                                    member_idx += 1
                    is_declaration = (dropdown_value in ["to_khai", "ct04"])
                    file_info = {
                        "filename": file.filename,
                        "type": ext,
                        "content": text,
                        "created_date": datetime.now().strftime("%Y-%m-%d"),
                        "doc_class": predicted_class or data.get("type", "unknown"),
                        "fields": structured_data if is_declaration else {}, # Use structured data from LLM
                        "show_extract_fields": is_declaration,
                        "predicted_class": predicted_class,
                        "confidence": confidence,
                        "dropdown_value": dropdown_value,
                        "id_numbers": data.get("id_numbers", []),  # Keep ID numbers from OCR
                        "procedure_id": procedure,
                        "case_id": case,
                        "procedure": procedure,  # Thêm procedure để dễ debug
                        "case": case  # Thêm case để dễ debug
                    }
                    uploaded_files_info.append(file_info)
                    print(f"Đã xử lý file: {file.filename}")
                    print(f"Procedure ID: {procedure}, Case ID: {case}")  # Debug log
                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue
        print("Tổng số file đã xử lý:", len(uploaded_files_info))
        # Sau khi xử lý xong file, sinh mã hồ sơ mới
        last_case_id += 1
        case_id_current = last_case_id
        # Gán mã hồ sơ (dạng số, padding 6 chữ số)
        ma_ho_so = f"{case_id_current:06d}"
        for file_info in uploaded_files_info:
            file_info["ma_ho_so"] = ma_ho_so
            file_info["case_id"] = case_id_current
        # Redirect sang bước xử lý tài liệu với procedure/case và truyền mã hồ sơ
        if procedure and case:
            return RedirectResponse(url=f"/process?procedure={procedure}&case={case}&case_id={case_id_current}", status_code=303)
        else:
            return RedirectResponse(url=f"/process?case_id={case_id_current}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("stepper/upload.html", {
            "request": request,
            "procedures": get_procedure_list(),
            "today": datetime.now().strftime("%Y-%m-%d"),
            "current_time": datetime.now().strftime("%H:%M"),
            "error": f"Lỗi khi tải lên: {str(e)}"
        })

@app.get("/process", response_class=HTMLResponse)
async def step_process_get(request: Request):
    global uploaded_files_info, case_id_current
    procedure_id = request.query_params.get('procedure')
    case_id = request.query_params.get('case')
    case_id_param = request.query_params.get('case_id')
    if case_id_param:
        case_id_current = int(case_id_param)
    procedure_details = None
    required_docs = []
    checklist = []
    is_full = False
    if procedure_id and case_id:
        from app.data.procedures import get_procedure_details, get_required_documents
        procedure_details = get_procedure_details(procedure_id, case_id)
        required_docs = get_required_documents(procedure_id, case_id)
        checklist, is_full = get_checklist(uploaded_files_info, required_docs)
    return templates.TemplateResponse("stepper/process.html", {
        "request": request,
        "results": uploaded_files_info,
        "procedure_details": procedure_details,
        "required_docs": required_docs,
        "checklist": checklist,
        "is_full": is_full,
        "case_id": case_id_current
    })

@app.post("/process")
async def step_process_post(request: Request):
    form = await request.form()
    procedure_id = form.get('procedure')
    case_id = form.get('case')
    global uploaded_files_info
    import json
    fields_data = {}

    # Lấy dữ liệu từ form
    for key, value in form.items():
        if key.startswith('fields['):
            import re
            m = re.match(r'fields\[(.*?)\]\[(.*?)\]', key)
            if m:
                filename = m.group(1)
                field_name = m.group(2)
                if filename not in fields_data:
                    fields_data[filename] = {}
                # Nếu value là JSON hợp lệ, parse về list/dict
                try:
                    parsed = json.loads(value)
                    fields_data[filename][field_name] = parsed
                except Exception:
                    fields_data[filename][field_name] = value

    # Cập nhật thông tin trong uploaded_files_info
    for file_info in uploaded_files_info:
        fname = file_info.get('filename')
        if fname in fields_data:
            file_info['fields'].update(fields_data[fname])

    # Kiểm tra checklist và chuyển hướng
    required_docs = []
    is_full = False
    if procedure_id and case_id:
        print(f"Processing for procedure: {procedure_id}, case: {case_id}")
        required_docs = get_required_documents(procedure_id, case_id)
        checklist, is_full = get_checklist(uploaded_files_info, required_docs)
        print("Checklist results:")
        for item in checklist:
            print(f"- {item['name']}: {item['status']}")
        print(f"Is full: {is_full}")
        if is_full:
            print("Documents complete - Redirecting to verify")
            return RedirectResponse(url="/verify", status_code=303)
        else:
            print("Documents incomplete - Redirecting to finalize")
            return RedirectResponse(url="/finalize", status_code=303)
    else:
        print("No procedure/case specified")
        return RedirectResponse(url="/finalize", status_code=303)

@app.get("/verify", response_class=HTMLResponse)
async def step_verify_get(request: Request):
    global uploaded_files_info, case_id_current
    print("Uploaded Files Info:", uploaded_files_info)
    if not uploaded_files_info:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": "Chưa có tài liệu nào được upload hoặc trích xuất."
        })
    file_info = next((f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04"]), None)
    if not file_info:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": "Không tìm thấy thông tin tờ khai hợp lệ để thẩm định."
        })
    fields = file_info.get("fields", {})
    print("Fields extracted from file:", fields)

    # Log mapping for debug
    print("Mapping for validate:")
    print("Cơ quan tiếp nhận:", fields.get("Cơ quan tiếp nhận", ""))
    print("Họ, chữ đệm và tên:", fields.get("Họ, chữ đệm và tên", ""))
    print("Ngày tháng năm sinh:", fields.get("Ngày tháng năm sinh", ""))
    print("Giới tính:", fields.get("Giới tính", ""))
    print("Số định danh cá nhân/CMND:", fields.get("Số định danh cá nhân/CMND", ""))
    print("Số điện thoại:", fields.get("Số điện thoại", ""))
    print("Email:", fields.get("Email", ""))
    print("Họ và tên chủ hộ:", fields.get("Họ và tên chủ hộ", ""))
    print("Mối quan hệ với chủ hộ:", fields.get("Mối quan hệ với chủ hộ", ""))
    print("Số định danh cá nhân của chủ hộ:", fields.get("Số định danh cá nhân của chủ hộ", ""))
    print("Nội dung đề nghị:", fields.get("Nội dung đề nghị", ""))

    # Build input for validate_ho_so_from_ocr with correct keys
    family_members = []
    if 'family_members' in fields:
        import ast
        try:
            members = fields['family_members']
            if isinstance(members, str):
                members = ast.literal_eval(members)
            for m in members:
                family_members.append({
                    "Họ, chữ đệm và tên": m.get("name", ""),
                    "Ngày, tháng, năm sinh": m.get("dob", ""),
                    "Giới tính": m.get("gender", ""),
                    "Số định danh cá nhân": m.get("id_number", ""),
                    "Quan hệ với chủ hộ": m.get("relationship", "")
                })
        except Exception as e:
            print("Error parsing family_members:", e)

    def get_field_value(f, key):
        v = f.get(key, "")
        if isinstance(v, dict):
            if 'value' in v:
                return v['value']
            else:
                print(f"[WARNING] Field '{key}' is dict but missing 'value' key: {v}")
                return ""
        if v is None:
            print(f"[WARNING] Field '{key}' is None")
            return ""
        return v

    validate_input = {
        "Tên cơ quan đăng ký cư trú": str(get_field_value(fields, "Cơ quan tiếp nhận")).strip(),
        "Họ, chữ đệm và tên": str(get_field_value(fields, "Họ, chữ đệm và tên")).strip(),
        "Ngày, tháng, năm sinh": str(get_field_value(fields, "Ngày tháng năm sinh")).strip(),
        "Giới tính": str(get_field_value(fields, "Giới tính")).lower().strip(),
        "Số định danh cá nhân": str(get_field_value(fields, "Số định danh cá nhân") or get_field_value(fields, "Số định danh cá nhân/CMND")).strip(),
        "Số điện thoại": str(get_field_value(fields, "Số điện thoại")).strip(),
        "Email": str(get_field_value(fields, "Email")).strip(),
        "Họ, chữ đệm và tên chủ hộ": str(get_field_value(fields, "Họ và tên chủ hộ")).strip(),
        "Quan hệ với chủ hộ": str(get_field_value(fields, "Mối quan hệ với chủ hộ")).lower().strip(),
        "Số định danh cá nhân của chủ hộ": str(get_field_value(fields, "Số định danh cá nhân của chủ hộ")).strip(),
        "Nội dung đề nghị": str(get_field_value(fields, "Nội dung đề nghị")).strip(),
        "Những thành viên trong hộ gia đình cùng thay đổi": family_members
    }
    print('DEBUG validate_input:', validate_input)

    from app.processor.validator import validate_ho_so_from_ocr
    validation_result = validate_ho_so_from_ocr(validate_input)

    # Sau khi validate, in toàn bộ validation_result
    print("[DEBUG] validation_result:", validation_result)
    # Luôn khởi tạo lại invalid_fields mới (KHÔNG lấy từ file_info)
    invalid_fields = []
    for field_name, field_data in validation_result.items():
        if isinstance(field_data, dict):
            status = field_data.get('status', '')
            if status != 'Đạt':
                invalid_fields.append(f"{field_name}: {status}")
        elif isinstance(field_data, list):
            for item in field_data:
                if isinstance(item, dict):
                    for sub_field, sub_data in item.items():
                        if isinstance(sub_data, dict):
                            status = sub_data.get('status', '')
                            if status != 'Đạt':
                                invalid_fields.append(f"{field_name} - {sub_field}: {status}")
        elif field_data != 'Đạt':
            invalid_fields.append(f"{field_name}: {field_data}")
    print("[DEBUG] invalid_fields mới nhất:", invalid_fields)
    # Cập nhật lại vào file_info nếu cần
    if file_info is not None:
        file_info["invalid_fields"] = invalid_fields

    # Mapping các trường chính với trạng thái
    extracted_fields = {
        "Tên cơ quan đăng ký cư trú": {
            "value": fields.get("Cơ quan tiếp nhận", ""),
            "status": validation_result.get("Tên cơ quan đăng ký cư trú", "Không xác định")
        },
        "Họ, chữ đệm và tên": {
            "value": fields.get("Họ, chữ đệm và tên", ""),
            "status": validation_result.get("Họ tên người kê khai", "Không xác định")
        },
        "Ngày, tháng, năm sinh": {
            "value": fields.get("Ngày tháng năm sinh", ""),
            "status": validation_result.get("Ngày sinh", "Không xác định")
        },
        "Giới tính": {
            "value": fields.get("Giới tính", ""),
            "status": validation_result.get("Giới tính", "Không xác định")
        },
        "Số định danh cá nhân": {
            "value": fields.get("Số định danh cá nhân/CMND", ""),
            "status": validation_result.get("Số định danh cá nhân", "Không xác định")
        },
        "Số điện thoại": {
            "value": fields.get("Số điện thoại", ""),
            "status": validation_result.get("Số điện thoại", "Không xác định")
        },
        "Email": {
            "value": fields.get("Email", ""),
            "status": validation_result.get("Email", "Không xác định")
        },
        "Họ, chữ đệm và tên chủ hộ": {
            "value": fields.get("Họ và tên chủ hộ", ""),
            "status": validation_result.get("Họ tên chủ hộ", "Không xác định")
        },
        "Quan hệ với chủ hộ": {
            "value": fields.get("Mối quan hệ với chủ hộ", ""),
            "status": validation_result.get("Quan hệ với chủ hộ", "Không xác định")
        },
        "Số định danh cá nhân của chủ hộ": {
            "value": fields.get("Số định danh cá nhân của chủ hộ", ""),
            "status": validation_result.get("Số định danh chủ hộ", "Không xác định")
        },
        "Nội dung đề nghị": {
            "value": fields.get("Nội dung đề nghị", ""),
            "status": ""
        }
    }

    # Thêm thông tin thành viên gia đình
    family_members = fields.get("family_members", [])
    if isinstance(family_members, str):
        try:
            import ast
            family_members = ast.literal_eval(family_members)
        except:
            family_members = []
    for idx, member in enumerate(family_members, 1):
        prefix = f"Thành viên {idx}"
        if isinstance(member, dict):
            extracted_fields[f"{prefix} - Họ và tên"] = {
                "value": member.get("name", ""),
                "status": validation_result.get("Thành viên thay đổi", [{}]*idx)[idx-1].get("Họ, chữ đệm và tên", "Không xác định") if "Thành viên thay đổi" in validation_result and len(validation_result["Thành viên thay đổi"]) >= idx else "Không xác định"
            }
            extracted_fields[f"{prefix} - Ngày sinh"] = {
                "value": member.get("dob", ""),
                "status": validation_result.get("Thành viên thay đổi", [{}]*idx)[idx-1].get("Ngày sinh", "Không xác định") if "Thành viên thay đổi" in validation_result and len(validation_result["Thành viên thay đổi"]) >= idx else "Không xác định"
            }
            extracted_fields[f"{prefix} - Giới tính"] = {
                "value": member.get("gender", ""),
                "status": validation_result.get("Thành viên thay đổi", [{}]*idx)[idx-1].get("Giới tính", "Không xác định") if "Thành viên thay đổi" in validation_result and len(validation_result["Thành viên thay đổi"]) >= idx else "Không xác định"
            }
            extracted_fields[f"{prefix} - Số định danh cá nhân"] = {
                "value": member.get("id_number", ""),
                "status": validation_result.get("Thành viên thay đổi", [{}]*idx)[idx-1].get("Số định danh cá nhân", "Không xác định") if "Thành viên thay đổi" in validation_result and len(validation_result["Thành viên thay đổi"]) >= idx else "Không xác định"
            }
            extracted_fields[f"{prefix} - Mối quan hệ với chủ hộ"] = {
                "value": member.get("relationship", ""),
                "status": validation_result.get("Thành viên thay đổi", [{}]*idx)[idx-1].get("Quan hệ với chủ hộ", "Không xác định") if "Thành viên thay đổi" in validation_result and len(validation_result["Thành viên thay đổi"]) >= idx else "Không xác định"
            }

    # Xác định trạng thái tổng thể cho "Trích xuất thông tin"
    info_status = 'pass'
    for field in extracted_fields.values():
        if field['status'] and field['status'] != 'Đạt' and field['status'] != '':
            info_status = 'fail'
            break

    print("Extracted Fields:", extracted_fields)

    result = {
        "fields": extracted_fields,
        "filename": file_info.get("filename", ""),
        "type": file_info.get("type", ""),
        "content": file_info.get("content", ""),
        "created_date": file_info.get("created_date", ""),
        "doc_class": file_info.get("doc_class", ""),
        "confidence": file_info.get("confidence", ""),
        "dropdown_value": file_info.get("dropdown_value", ""),
    }
    return templates.TemplateResponse("stepper/verify.html", {
        "request": request,
        "fields": extracted_fields,
        "result": result,
        "info_status": info_status,
        "case_id": case_id_current
    })

@app.post("/verify")
async def step_verify_post(request: Request):
    form = await request.form()
    import json
    global uploaded_files_info
    fields_json = form.get('fields')
    if not fields_json:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": "Không có dữ liệu để thẩm định."
        })
    try:
        fields = json.loads(fields_json)
        # Lấy lại file_info gốc
        file_info = next((f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04"]), None)
        fields_origin = file_info.get("fields", {}) if file_info else {}
        def get_field_value_safe(f, key, fallback=""):
            v = f.get(key, "")
            if isinstance(v, dict):
                return v.get("value", fallback)
            if v is None or v == "":
                return fallback
            return v
        mapped_fields = {
            "Tên cơ quan đăng ký cư trú": get_field_value_safe(fields, "Cơ quan tiếp nhận", fields_origin.get("Cơ quan tiếp nhận", "")),
            "Họ, chữ đệm và tên": get_field_value_safe(fields, "Họ, chữ đệm và tên", fields_origin.get("Họ, chữ đệm và tên", "")),
            "Ngày, tháng, năm sinh": get_field_value_safe(fields, "Ngày tháng năm sinh", fields_origin.get("Ngày tháng năm sinh", "")),
            "Giới tính": get_field_value_safe(fields, "Giới tính", fields_origin.get("Giới tính", "")),
            "Số định danh cá nhân": get_field_value_safe(fields, "Số định danh cá nhân/CMND", fields_origin.get("Số định danh cá nhân/CMND", "")),
            "Số điện thoại": get_field_value_safe(fields, "Số điện thoại", fields_origin.get("Số điện thoại", "")),
            "Email": get_field_value_safe(fields, "Email", fields_origin.get("Email", "")),
            "Họ, chữ đệm và tên chủ hộ": get_field_value_safe(fields, "Họ và tên chủ hộ", fields_origin.get("Họ và tên chủ hộ", "")),
            "Quan hệ với chủ hộ": get_field_value_safe(fields, "Mối quan hệ với chủ hộ", fields_origin.get("Mối quan hệ với chủ hộ", "")),
            "Số định danh cá nhân của chủ hộ": get_field_value_safe(fields, "Số định danh cá nhân của chủ hộ", fields_origin.get("Số định danh cá nhân của chủ hộ", "")),
            "Nội dung đề nghị": get_field_value_safe(fields, "Nội dung đề nghị", fields_origin.get("Nội dung đề nghị", "")),
        }
    except Exception as e:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": f"Lỗi dữ liệu: {e}"
        })
    
    ket_qua = validate_ho_so_from_ocr(mapped_fields)
    
    # Kiểm tra tất cả các trường đều hợp lệ
    is_full = True
    invalid_fields = []
    
    for field_name, validation_result in ket_qua.items():
        if isinstance(validation_result, list):
            for item in validation_result:
                if isinstance(item, dict):
                    for sub_field, status in item.items():
                        if status != 'Đạt':
                            is_full = False
                            invalid_fields.append(f"{field_name} - {sub_field}: {status}")
                elif validation_result != 'Đạt':
                    is_full = False
                    invalid_fields.append(f"{field_name}: {validation_result}")
        elif isinstance(validation_result, dict):
            for sub_field, status in validation_result.items():
                if status != 'Đạt':
                    is_full = False
                    invalid_fields.append(f"{field_name} - {sub_field}: {status}")
        elif validation_result != 'Đạt':
            is_full = False
            invalid_fields.append(f"{field_name}: {validation_result}")
    
    # Lưu trạng thái và thông tin lỗi vào uploaded_files_info
    for file_info in uploaded_files_info:
        if file_info.get("doc_class") in ["ct01", "to_khai", "ct04"]:
            file_info["is_full"] = is_full
            file_info["validation_result"] = ket_qua
            file_info["invalid_fields"] = invalid_fields
            break
    
    # Chuyển hướng đến trang finalize
    return RedirectResponse(url="/finalize", status_code=303)

@app.get("/finalize", response_class=HTMLResponse)
async def step_finalize_get(request: Request):
    global uploaded_files_info, case_id_current
    # Lấy đúng file tờ khai để kiểm tra hợp lệ
    file_info = next((f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04"]), None)
    if not file_info and uploaded_files_info:
        file_info = uploaded_files_info[0]
    fields = file_info.get("fields", {}) if file_info else {}
    print("[DEBUG] Fields for validation:", fields)
    is_full = file_info.get("is_full", False) if file_info else False
    invalid_fields = file_info.get("invalid_fields", []) if file_info else []
    ma_ho_so = file_info.get("ma_ho_so") if file_info else None
    validation_result = file_info.get("validation_result", {}) if file_info else {}

    # Lấy thành phần hồ sơ nộp từ procedure/case
    required_docs = []
    if file_info:
        from app.data.procedures import get_required_documents
        # Ưu tiên lấy key chuỗi (case/procedure), nếu không có thì lấy case_id/procedure_id
        procedure_key = file_info.get('procedure') or file_info.get('procedure_id') or ''
        case_key = file_info.get('case') or file_info.get('case_id') or ''
        print(f"[DEBUG] Getting required docs for procedure: {procedure_key}, case: {case_key}")
        required_docs = get_required_documents(str(procedure_key), str(case_key))
        print(f"[DEBUG] Required docs: {required_docs}")

    # Kiểm tra trạng thái validation trên validation_result
    info_status = 'pass'
    for field_name, field_data in validation_result.items():
        if isinstance(field_data, dict):
            status = field_data.get('status', '')
            if status != 'Đạt':
                info_status = 'fail'
                invalid_fields.append(f"{field_name}: {status}")
        elif isinstance(field_data, list):
            for item in field_data:
                if isinstance(item, dict):
                    for sub_field, sub_data in item.items():
                        if isinstance(sub_data, dict):
                            status = sub_data.get('status', '')
                            if status != 'Đạt':
                                info_status = 'fail'
                                invalid_fields.append(f"{field_name} - {sub_field}: {status}")
        elif field_data != 'Đạt':
            info_status = 'fail'
            invalid_fields.append(f"{field_name}: {field_data}")

    # Xác định form type dựa trên kết quả validation và giấy tờ còn thiếu
    if not get_missing_documents(required_docs, uploaded_files_info) and info_status == 'pass':
        form_type = 'CT04'
    else:
        form_type = 'CT05'

    # Sau khi validate, in toàn bộ validation_result
    print("[DEBUG] validation_result:", validation_result)
    # Luôn khởi tạo lại invalid_fields mới (KHÔNG lấy từ file_info)
    invalid_fields = []
    for field_name, field_data in validation_result.items():
        if isinstance(field_data, dict):
            status = field_data.get('status', '')
            if status != 'Đạt':
                invalid_fields.append(f"{field_name}: {status}")
        elif isinstance(field_data, list):
            for item in field_data:
                if isinstance(item, dict):
                    for sub_field, sub_data in item.items():
                        if isinstance(sub_data, dict):
                            status = sub_data.get('status', '')
                            if status != 'Đạt':
                                invalid_fields.append(f"{field_name} - {sub_field}: {status}")
        elif field_data != 'Đạt':
            invalid_fields.append(f"{field_name}: {field_data}")
    print("[DEBUG] invalid_fields mới nhất:", invalid_fields)
    # Cập nhật lại vào file_info nếu cần
    if file_info is not None:
        file_info["invalid_fields"] = invalid_fields

    # Chuẩn bị dữ liệu đầu vào cho LLM
    if fields:
        try:
            # Chuẩn bị dữ liệu đầu vào
            missing_docs = get_missing_documents(required_docs, uploaded_files_info)
            from datetime import datetime
            today = datetime.now()
            ngay_lap_phieu = today.strftime('%d/%m/%Y')
            validator_input = {
                "Tên cơ quan đăng ký cư trú": str(get_field_value(fields, "Cơ quan tiếp nhận")).strip(),
                "Họ, chữ đệm và tên": str(get_field_value(fields, "Họ, chữ đệm và tên")).strip(),
                "Ngày, tháng, năm sinh": str(get_field_value(fields, "Ngày tháng năm sinh")).strip(),
                "Giới tính": str(get_field_value(fields, "Giới tính")).lower().strip(),
                "Số định danh cá nhân": str(get_field_value(fields, "Số định danh cá nhân") or get_field_value(fields, "Số định danh cá nhân/CMND")).strip(),
                "Số điện thoại": str(get_field_value(fields, "Số điện thoại")).strip(),
                "Email": str(get_field_value(fields, "Email")).strip(),
                "Họ, chữ đệm và tên chủ hộ": str(get_field_value(fields, "Họ và tên chủ hộ")).strip(),
                "Quan hệ với chủ hộ": str(get_field_value(fields, "Mối quan hệ với chủ hộ")).lower().strip(),
                "Số định danh cá nhân của chủ hộ": str(get_field_value(fields, "Số định danh cá nhân của chủ hộ")).strip(),
                "Nội dung đề nghị": str(get_field_value(fields, "Nội dung đề nghị")).strip(),
                "Thành viên thay đổi": [],
                "thanh_phan_ho_so": [doc['name'] for doc in required_docs] if required_docs else [],
                "ma_ho_so": ma_ho_so or "",
                "giay_to_thieu": missing_docs,
                "ngay_lap_phieu": ngay_lap_phieu
            }

            # Thêm thông tin thành viên gia đình nếu có
            for i in range(1, 10):  # Giả sử tối đa 9 thành viên
                prefix = f"Thành viên {i}"
                if f"{prefix} - Họ và tên" in fields:
                    member = {
                        "Họ, chữ đệm và tên": fields.get(f"{prefix} - Họ và tên", ""),
                        "Ngày sinh": fields.get(f"{prefix} - Ngày sinh", ""),
                        "Giới tính": fields.get(f"{prefix} - Giới tính", "").lower().strip(),
                        "Số định danh cá nhân": str(fields.get(f"{prefix} - Số định danh cá nhân", "")).strip(),
                        "Quan hệ với chủ hộ": fields.get(f"{prefix} - Mối quan hệ với chủ hộ", "").lower().strip()
                    }
                    validator_input["Thành viên thay đổi"].append(member)

            # Xác định form type và thêm invalid_fields nếu cần
            form_type = form_type
            if form_type == "CT05" and info_status == 'fail':
                validator_input["invalid_fields"] = invalid_fields

            # Khi truyền vào LLM, chỉ lấy invalid_fields mới nhất
            if form_type == 'CT05' and invalid_fields:
                validator_input["invalid_fields"] = invalid_fields
            else:
                validator_input.pop("invalid_fields", None)
            print("[DEBUG] validator_input truyền vào LLM:", validator_input)

            from app.processor.filler import LLMFiller
            llm_content = LLMFiller()(validator_input, form_type=form_type)
        except Exception as e:
            print(f"Error filling form: {str(e)}")
            llm_content = "Lỗi khi điền form tự động"
    else:
        # Render nội dung từ file mẫu HTML
        template_file = f"app/templates/snippets/ct04.html" if form_type == "CT04" else f"app/templates/snippets/ct05.html"
        llm_content = ""
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                raw_html = f.read()
                jinja_template = JinjaTemplate(raw_html)
                context = {**fields, "case_id": case_id_current}
                if form_type == 'CT05':
                    context["invalid_fields"] = invalid_fields
                llm_content = jinja_template.render(**context)
        else:
            llm_content = f"Không tìm thấy file mẫu {template_file}!"

    return templates.TemplateResponse("stepper/finalize.html", {
        "request": request,
        "llm_content": llm_content,
        "ct04_blank": "",
        "ct05_blank": "",
        "selected_template": form_type,
        "case_id": case_id_current,
        "ma_ho_so": ma_ho_so,
        "invalid_fields": invalid_fields
    })

@app.post("/finalize", response_class=HTMLResponse)
async def step_finalize_post(request: Request):
    form = await request.form()
    template = form.get("template", "CT04")
    ngay_bao_cao = form.get("ngay_bao_cao", "")
    import os
    global uploaded_files_info, case_id_current
    # Lấy đúng file tờ khai để kiểm tra hợp lệ
    file_info = next((f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04"]), None)
    if not file_info and uploaded_files_info:
        file_info = uploaded_files_info[0]
    fields = file_info.get("fields", {}) if file_info else {}
    print("[DEBUG] Fields for validation:", fields)
    is_full = file_info.get("is_full", False) if file_info else False
    invalid_fields = file_info.get("invalid_fields", []) if file_info else []
    ma_ho_so = file_info.get("ma_ho_so") if file_info else None
    validation_result = file_info.get("validation_result", {}) if file_info else {}

    # Lấy thành phần hồ sơ nộp từ procedure/case
    required_docs = []
    if file_info:
        from app.data.procedures import get_required_documents
        procedure_key = file_info.get('procedure') or file_info.get('procedure_id') or ''
        case_key = file_info.get('case') or file_info.get('case_id') or ''
        print(f"[DEBUG] Getting required docs for procedure: {procedure_key}, case: {case_key}")
        required_docs = get_required_documents(str(procedure_key), str(case_key))
        print(f"[DEBUG] Required docs: {required_docs}")

    # Luôn khởi tạo lại invalid_fields mới nhất từ validation_result
    invalid_fields = []
    info_status = 'pass'
    for field_name, field_data in validation_result.items():
        if isinstance(field_data, dict):
            status = field_data.get('status', '')
            if status != 'Đạt':
                info_status = 'fail'
                invalid_fields.append(f"{field_name}: {status}")
        elif isinstance(field_data, list):
            for item in field_data:
                if isinstance(item, dict):
                    for sub_field, sub_data in item.items():
                        if isinstance(sub_data, dict):
                            status = sub_data.get('status', '')
                            if status != 'Đạt':
                                info_status = 'fail'
                                invalid_fields.append(f"{field_name} - {sub_field}: {status}")
        elif field_data != 'Đạt':
            info_status = 'fail'
            invalid_fields.append(f"{field_name}: {field_data}")
    print("[DEBUG] invalid_fields mới nhất:", invalid_fields)
    if file_info is not None:
        file_info["invalid_fields"] = invalid_fields

    # Xác định form type dựa trên kết quả validation và giấy tờ còn thiếu
    missing_docs = get_missing_documents(required_docs, uploaded_files_info)
    if not missing_docs and info_status == 'pass':
        form_type = 'CT04'
    else:
        form_type = template
    today = datetime.now()
    ngay_lap_phieu = today.strftime('%d/%m/%Y')
    # Chuẩn bị dữ liệu đầu vào cho LLM
    if fields:
        try:
            validator_input = {
                "Tên cơ quan đăng ký cư trú": str(get_field_value(fields, "Cơ quan tiếp nhận")).strip(),
                "Họ, chữ đệm và tên": str(get_field_value(fields, "Họ, chữ đệm và tên")).strip(),
                "Ngày, tháng, năm sinh": str(get_field_value(fields, "Ngày tháng năm sinh")).strip(),
                "Giới tính": str(get_field_value(fields, "Giới tính")).lower().strip(),
                "Số định danh cá nhân": str(get_field_value(fields, "Số định danh cá nhân") or get_field_value(fields, "Số định danh cá nhân/CMND")).strip(),
                "Số điện thoại": str(get_field_value(fields, "Số điện thoại")).strip(),
                "Email": str(get_field_value(fields, "Email")).strip(),
                "Họ, chữ đệm và tên chủ hộ": str(get_field_value(fields, "Họ và tên chủ hộ")).strip(),
                "Quan hệ với chủ hộ": str(get_field_value(fields, "Mối quan hệ với chủ hộ")).lower().strip(),
                "Số định danh cá nhân của chủ hộ": str(get_field_value(fields, "Số định danh cá nhân của chủ hộ")).strip(),
                "Nội dung đề nghị": str(get_field_value(fields, "Nội dung đề nghị")).strip(),
                "Thành viên thay đổi": [],
                "thanh_phan_ho_so": [doc['name'] for doc in required_docs] if required_docs else [],
                "ma_ho_so": ma_ho_so or "",
                "giay_to_thieu": missing_docs,
                "ngay_lap_phieu": ngay_lap_phieu
            }
            for i in range(1, 10):
                prefix = f"Thành viên {i}"
                if f"{prefix} - Họ và tên" in fields:
                    member = {
                        "Họ, chữ đệm và tên": fields.get(f"{prefix} - Họ và tên", ""),
                        "Ngày sinh": fields.get(f"{prefix} - Ngày sinh", ""),
                        "Giới tính": fields.get(f"{prefix} - Giới tính", "").lower().strip(),
                        "Số định danh cá nhân": str(fields.get(f"{prefix} - Số định danh cá nhân", "")).strip(),
                        "Quan hệ với chủ hộ": fields.get(f"{prefix} - Mối quan hệ với chủ hộ", "").lower().strip()
                    }
                    validator_input["Thành viên thay đổi"].append(member)
            if form_type == "CT05" and invalid_fields:
                validator_input["invalid_fields"] = invalid_fields
            else:
                validator_input.pop("invalid_fields", None)
            print("[DEBUG] validator_input truyền vào LLM:", validator_input)
            from app.processor.filler import LLMFiller
            llm_content = LLMFiller()(validator_input, form_type=form_type)
        except Exception as e:
            print(f"Error filling form: {str(e)}")
            llm_content = "Lỗi khi điền form tự động"
    else:
        template_file = f"app/templates/snippets/ct04.html" if form_type == "CT04" else f"app/templates/snippets/ct05.html"
        llm_content = ""
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                raw_html = f.read()
                jinja_template = JinjaTemplate(raw_html)
                context = {**fields, "case_id": case_id_current}
                if form_type == 'CT05':
                    context["invalid_fields"] = invalid_fields
                llm_content = jinja_template.render(**context)
        else:
            llm_content = f"Không tìm thấy file mẫu {template_file}!"

    # Xóa cache sau khi xử lý xong
    uploaded_files_info = []

    # Chuyển về trang chủ sau khi hoàn thành
    return RedirectResponse(url="/", status_code=303)

@app.post("/support/verify")
async def support_verify(request: Request):
    form = await request.form()
    import json
    fields_json = form.get('fields')
    if not fields_json:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": "Không có dữ liệu để thẩm định."
        })
    try:
        fields = json.loads(fields_json)
    except Exception as e:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": f"Lỗi dữ liệu: {e}"
        })
    ket_qua = validate_ho_so_from_ocr(fields)
    return templates.TemplateResponse("stepper/verify.html", {
        "request": request,
        "fields": fields,
        "result": ket_qua
    })

# API endpoints
@app.get("/api/cases/{procedure_id}")
async def get_cases(procedure_id: str):
    cases = get_procedure_cases(procedure_id)
    return JSONResponse(content=cases)

@app.get("/api/required_documents")
async def api_required_documents(procedure: str, case: str):
    documents = get_required_documents(procedure, case)
    return JSONResponse(content=documents)

def is_all_fields_valid(validation_result):
    for v in validation_result.values():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    for sub_status in item.values():
                        if sub_status != 'Đạt':
                            return False
                elif item != 'Đạt':
                    return False
        elif isinstance(v, dict):
            for sub_status in v.values():
                if sub_status != 'Đạt':
                    return False
        elif v != 'Đạt':
            return False
    return True