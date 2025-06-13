from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict
from datetime import datetime
from app.processor.extractor import DocumentExtractor
from app.data.procedures import get_procedure_list, get_procedure_cases, get_required_documents, get_procedure_details
import os
import time
# from app.classify import model as yolo_model
from app.processor.classifier import classify_document, model as yolo_model
from app.processor.validator import validate_ho_so_from_ocr  
from app.processor.filler import LLMFiller
from jinja2 import Template as JinjaTemplate
from app.database import get_db
from sqlalchemy.orm import Session
from app.services.case_service import CaseService
from app.middleware.session import SessionMiddleware
from app.models import Case
from app.services.citizen_service import CitizenService

# Tạo FastAPI app
app = FastAPI(title="Hệ thống Cơ sở dữ liệu thẩm tra, thẩm định")

# Add session middleware
session_middleware = SessionMiddleware(app)
app.add_middleware(SessionMiddleware)

# Store middleware instance in app state
app.state.session_middleware = session_middleware


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# Templates
templates = Jinja2Templates(directory="app/templates")

# Khởi tạo DocumentExtractor
document_extractor = DocumentExtractor()

# Khởi tạo LLMFiller
llm_filler = LLMFiller()

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
        "ct01_2021": "to_khai",
        "ct01_2023": "to_khai",
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

def print_timing(start_time, step_name):
    end_time = time.time()
    duration = end_time - start_time
    print(f"[TIMING] {step_name}: {duration:.2f} seconds")
    return end_time

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
        print("[DEBUG] Starting upload_post")
        print("[DEBUG] Received procedure:", procedure)
        print("[DEBUG] Received case:", case)
        
        session = request.state.session
        # Convert procedure and case to integer id if possible
        procedure_id = None
        case_id = None
        
        # Map procedure code/name to ID
        if procedure:
            from app.data.procedures import get_procedure_list
            procedures = get_procedure_list()
            print("[DEBUG] Available procedures:", procedures)
            for p in procedures:
                print("[DEBUG] Compare with:", p.get("name"), p.get("id"), p.get("code"))
                if p.get("name") == procedure or p.get("id") == procedure or p.get("code") == procedure:
                    procedure_id = p.get("id")
                    print("[DEBUG] Mapped procedure to ID:", procedure_id)
                    break
            
            if procedure_id is None:
                try:
                    procedure_id = int(procedure)
                    print("[DEBUG] Converted procedure to ID:", procedure_id)
                except ValueError:
                    print("[ERROR] Could not convert procedure to ID")
                    procedure_id = None

        # Map case code/name to ID
        if case and procedure_id:
            from app.data.procedures import get_procedure_cases
            cases = get_procedure_cases(procedure_id)
            print("[DEBUG] Available cases:", cases)
            for c in cases:
                print("[DEBUG] Compare with:", c.get("name"), c.get("id"), c.get("code"))
                if c.get("name") == case or c.get("id") == case or c.get("code") == case:
                    case_id = c.get("id")
                    print("[DEBUG] Mapped case to ID:", case_id)
                    break
            
            if case_id is None:
                try:
                    case_id = int(case)
                    print("[DEBUG] Converted case to ID:", case_id)
                except ValueError:
                    print("[ERROR] Could not convert case to ID")
                    case_id = None

        print("[DEBUG] Final procedure_id:", procedure_id)
        print("[DEBUG] Final case_id:", case_id)
        # Lưu vào session nếu có giá trị
        if procedure_id:
            session["procedure_id"] = procedure_id
        else:
            print("[WARNING] procedure_id is empty, not saving to session!")
        if case_id:
            session["case_id"] = case_id
        else:
            print("[WARNING] case_id is empty, not saving to session!")

        uploaded_files_info = []  # Reset danh sách file
        files = []
        if form_files:
            files.extend(form_files)
        if related_files:
            files.extend(related_files)
        
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
                file_start_time = time.time()
                file_path = os.path.join(upload_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                try:
                    # Extract text and structured data using OCR and LLM
                    ocr_start_time = time.time()
                    text, data = document_extractor.extract_text(file_path)
                    ocr_end_time = print_timing(ocr_start_time, "OCR Processing")
                    
                    # PHÂN LOẠI TỰ ĐỘNG
                    classify_start_time = time.time()
                    ext = os.path.splitext(file.filename)[1][1:].lower()
                    predicted_class = None
                    confidence = None
                    if ext in ["jpg", "jpeg", "png"] and yolo_model is not None:
                        results = yolo_model(file_path)
                        if results and len(results) > 0:
                            result = results[0]
                            if hasattr(result, 'probs') and result.probs is not None:
                                top1_idx = result.probs.top1
                                confidence = float(result.probs.top1conf)
                                predicted_class = yolo_model.names[top1_idx]
                    else:
                        predicted_class = classify_document(text)
                        confidence = 1.0 if predicted_class != "khac" else 0.0
                    classify_end_time = print_timing(classify_start_time, "Document Classification")
                    
                    dropdown_value = map_predicted_class_to_dropdown_value(predicted_class)
                    
                    # Parse structured text from LLM
                    llm_start_time = time.time()
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
                    llm_end_time = print_timing(llm_start_time, "LLM Processing")
                    
                    is_declaration = (dropdown_value in ["to_khai", "ct04"])
                    file_info = {
                        "filename": file.filename,
                        "type": ext,
                        "content": text,
                        "created_date": datetime.now().strftime("%Y-%m-%d"),
                        "doc_class": predicted_class or data.get("type", "unknown"),
                        "fields": structured_data if is_declaration else {},
                        "show_extract_fields": is_declaration,
                        "predicted_class": predicted_class,
                        "confidence": confidence,
                        "dropdown_value": dropdown_value,
                        "id_numbers": data.get("id_numbers", []),
                        "procedure_id": procedure_id,
                        "case_id": case_id
                    }
                    uploaded_files_info.append(file_info)
                    file_end_time = print_timing(file_start_time, f"Total File Processing for {file.filename}")
                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue

        # Đảm bảo ma_ho_so luôn có trong uploaded_files_info để hiển thị ở bước finalize
        temp_ma_ho_so = None
        if uploaded_files_info:
            # Nếu đã có ma_ho_so trong session thì giữ lại, nếu chưa có thì sinh tạm thời (dạng 6 số random)
            temp_ma_ho_so = session.get("ma_ho_so")
            if not temp_ma_ho_so:
                import random
                temp_ma_ho_so = f"{random.randint(1, 999999):06d}"
                session["ma_ho_so"] = temp_ma_ho_so
            for file_info in uploaded_files_info:
                file_info["ma_ho_so"] = temp_ma_ho_so

        # Update session data
        session["uploaded_files_info"] = uploaded_files_info
        session["fields"] = uploaded_files_info[0].get("fields", {}) if uploaded_files_info else {}

        print("[DEBUG] Updated session data:")
        print("- procedure_id:", procedure_id)
        print("- case_id:", case_id)

        return RedirectResponse(url="/process", status_code=303)
    except Exception as e:
        print(f"[ERROR] Error in upload_post: {str(e)}")
        return templates.TemplateResponse("stepper/upload.html", {
            "request": request,
            "procedures": get_procedure_list(),
            "today": datetime.now().strftime("%Y-%m-%d"),
            "current_time": datetime.now().strftime("%H:%M"),
            "error": f"Lỗi khi xử lý file: {str(e)}"
        })

@app.get("/process", response_class=HTMLResponse)
async def step_process_get(request: Request):
    session = request.state.session
    case_id_current = session.get("case_id_current")
    procedure_id = session.get("procedure_id", "")
    case_id = session.get("case_id", "")
    case_id_param = request.query_params.get('case_id')
    if case_id_param:
        case_id_current = int(case_id_param)
    # Đảm bảo procedure_id và case_id luôn lấy từ session nếu không có
    if not procedure_id:
        procedure_id = session.get("procedure_id", "")
    if not case_id:
        case_id = session.get("case_id", "")
    procedure_details = None
    required_docs = []
    checklist = []
    is_full = False
    uploaded_files_info = session.get("uploaded_files_info", [])
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
        "case_id": case_id_current,
        "procedure_id": procedure_id,
        "case_id_hidden": case_id
    })

@app.post("/process")
async def step_process_post(request: Request):
    session = request.state.session
    form = await request.form()
    print("[DEBUG] FORM DATA:", dict(form))  # Thêm dòng này để debug
    procedure_id = form.get('procedure')
    case_id = form.get('case')
    import json
    fields_data = {}
    uploaded_files_info = session.get("uploaded_files_info", [])

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
    session["uploaded_files_info"] = uploaded_files_info

    # Kiểm tra checklist và chuyển hướng
    required_docs = []
    is_full = False
    if procedure_id and case_id:
        print(f"[DEBUG] procedure_id: {procedure_id}, case_id: {case_id}")
        required_docs = get_required_documents(procedure_id, case_id)
        checklist, is_full = get_checklist(uploaded_files_info, required_docs)
        print("[DEBUG] Checklist results:")
        for item in checklist:
            print(f"- {item['name']}: {item['status']}")
        print(f"[DEBUG] is_full: {is_full}")
        if is_full:
            print("[DEBUG] Documents complete - Redirecting to verify")
            return RedirectResponse(url="/verify", status_code=303)
        else:
            print("[DEBUG] Documents incomplete - Redirecting to finalize")
            return RedirectResponse(url="/finalize", status_code=303)
    else:
        print(f"[DEBUG] No procedure/case specified: procedure_id={procedure_id}, case_id={case_id}")
        return RedirectResponse(url="/finalize", status_code=303)

@app.get("/verify", response_class=HTMLResponse)
async def step_verify_get(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    case_id_current = session.get("case_id_current")
    uploaded_files_info = session.get("uploaded_files_info", [])
    print("Uploaded Files Info:", uploaded_files_info)
    if not uploaded_files_info:
        return templates.TemplateResponse("stepper/verify.html", {
            "request": request,
            "result": None,
            "fields": None,
            "error": "Chưa có tài liệu nào được upload hoặc trích xuất."
        })
    file_info = next(
        (f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04", "ct01_2021", "ct01_2023"]), None)
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
    print("Họ, chữ đệm và tên chủ hộ:", fields.get("Họ và tên chủ hộ", ""))
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

    # Đối chiếu thông tin với database citizen
    citizen_data = {
        "ho_ten": validate_input["Họ, chữ đệm và tên"],
        "ngay_sinh": validate_input["Ngày, tháng, năm sinh"],
        "gioi_tinh": validate_input["Giới tính"],
        "cccd": validate_input["Số định danh cá nhân"]
    }
    db_verification = CitizenService.verify_citizen_info(db, citizen_data)
    
    # Validate thông tin từ OCR
    from app.processor.validator import validate_ho_so_from_ocr
    validation_result = validate_ho_so_from_ocr(validate_input)
    
    # Thêm kết quả đối chiếu vào validation_result
    if not db_verification["is_valid"]:
        validation_result["Đối chiếu cơ sở dữ liệu"] = {
            "status": "Không đạt",
            "details": db_verification["mismatches"]
        }
    else:
        validation_result["Đối chiếu cơ sở dữ liệu"] = {
            "status": "Đạt",
            "details": ["Thông tin khớp với cơ sở dữ liệu"]
        }

    # Tổng hợp invalid_fields từ validation_result
    invalid_fields = []
    for field_name, field_data in validation_result.items():
        if isinstance(field_data, dict):
            status = field_data.get('status', '')
            if status != 'Đạt':
                if field_name == "Đối chiếu cơ sở dữ liệu":
                    # Thêm từng lỗi đối chiếu CSDL vào invalid_fields
                    for detail in field_data.get('details', []):
                        invalid_fields.append(f"Đối chiếu cơ sở dữ liệu: {detail}")
                else:
                    invalid_fields.append(f"{field_name}: {status}")
                    if 'details' in field_data:
                        for detail in field_data['details']:
                            invalid_fields.append(f"- {detail}")
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

    # Lưu lại validation_result và invalid_fields vào file_info
    if file_info is not None:
        file_info["validation_result"] = validation_result
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
        },
        "Đối chiếu cơ sở dữ liệu": {
            "value": "Đã kiểm tra",
            "status": validation_result.get("Đối chiếu cơ sở dữ liệu", {}).get("status", "Không xác định"),
            "details": validation_result.get("Đối chiếu cơ sở dữ liệu", {}).get("details", [])
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
        if field['status'] and field['status'] != 'Đạt':
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
    session = request.state.session
    form = await request.form()
    import json
    uploaded_files_info = session.get("uploaded_files_info", [])
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
        file_info = next((f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04", "ct01_2021", "ct01_2023"]), None)
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

    # Nếu file_info có validation_result cũ với trường Đối chiếu cơ sở dữ liệu, gộp vào
    if file_info and "validation_result" in file_info:
        old_db_check = file_info["validation_result"].get("Đối chiếu cơ sở dữ liệu")
        if old_db_check:
            ket_qua["Đối chiếu cơ sở dữ liệu"] = old_db_check

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
            status = validation_result.get('status', '')
            if status != 'Đạt':
                is_full = False
                if field_name == "Đối chiếu cơ sở dữ liệu":
                    for detail in validation_result.get('details', []):
                        invalid_fields.append(f"Đối chiếu cơ sở dữ liệu: {detail}")
                else:
                    invalid_fields.append(f"{field_name}: {status}")
                    for detail in validation_result.get('details', []):
                        invalid_fields.append(f"- {detail}")
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
    session["uploaded_files_info"] = uploaded_files_info
    return RedirectResponse(url="/finalize", status_code=303)

@app.get("/finalize", response_class=HTMLResponse)
async def step_finalize_get(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    case_id_current = session.get("case_id_current")
    uploaded_files_info = session.get("uploaded_files_info", [])
    file_info = next((f for f in uploaded_files_info if f.get("doc_class") in ["ct01", "to_khai", "ct04", "ct01_2021", "ct01_2023"]), None)
    if not file_info and uploaded_files_info:
        file_info = uploaded_files_info[0]
    fields = file_info.get("fields", {}) if file_info else {}
    print("[DEBUG] Fields for validation:", fields)
    is_full = file_info.get("is_full", False) if file_info else False
    invalid_fields = file_info.get("invalid_fields", []) if file_info else []
    validation_result = file_info.get("validation_result", {}) if file_info else {}
    # Lấy validation_result từ file_info
    validation_result = file_info.get("validation_result", {}) if file_info else {}

    # Tổng hợp invalid_fields duy nhất từ validation_result (KHÔNG lấy từ file_info)
    invalid_fields = []
    for field_name, field_data in validation_result.items():
        if isinstance(field_data, dict):
            status = field_data.get('status', '')
            if status != 'Đạt':
                if field_name == "Đối chiếu cơ sở dữ liệu":
                    # Thêm từng lỗi đối chiếu CSDL vào invalid_fields
                    for detail in field_data.get('details', []):
                        invalid_fields.append(f"Đối chiếu cơ sở dữ liệu: {detail}")
                else:
                    invalid_fields.append(f"{field_name}: {status}")
                    if 'details' in field_data:
                        for detail in field_data['details']:
                            invalid_fields.append(f"- {detail}")
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
    # Bổ sung lỗi đối chiếu CSDL vào invalid_fields nếu có
    db_check = validation_result.get("Đối chiếu cơ sở dữ liệu", {})
    if db_check and db_check.get("status") != "Đạt":
        for detail in db_check.get("details", []):
            if f"Đối chiếu cơ sở dữ liệu: {detail}" not in invalid_fields:
                invalid_fields.append(f"Đối chiếu cơ sở dữ liệu: {detail}")
    # Lưu lại vào file_info
    if file_info is not None:
        file_info["validation_result"] = validation_result
        file_info["invalid_fields"] = invalid_fields

    ma_ho_so = file_info.get("ma_ho_so") if file_info else None
    if not ma_ho_so:
        ma_ho_so = session.get("ma_ho_so")
    if not ma_ho_so:
        import random
        ma_ho_so = f"{random.randint(1, 999999):06d}"

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
                if 'details' in field_data:
                    for detail in field_data['details']:
                        invalid_fields.append(f"- {detail}")
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
    # --- Thêm lỗi đối chiếu cơ sở dữ liệu vào invalid_fields nếu có ---
    db_check = validation_result.get("Đối chiếu cơ sở dữ liệu", {})
    if db_check and db_check.get("status") != "Đạt":
        for detail in db_check.get("details", []):
            invalid_fields.append(f"Đối chiếu cơ sở dữ liệu: {detail}")
    print("[DEBUG] invalid_fields mới nhất:", invalid_fields)
    # Cập nhật lại vào file_info nếu cần
    if file_info is not None:
        file_info["invalid_fields"] = invalid_fields

    # --- Lấy thông tin công dân từ DB để điền vào CT04 ---
    cccd = str(get_field_value(fields, "Số định danh cá nhân") or get_field_value(fields, "Số định danh cá nhân/CMND")).strip()
    citizen = CitizenService.get_citizen_by_cccd(db, cccd) if cccd else None
    noi_thuong_tru = getattr(citizen, "noi_thuong_tru", "...") if citizen else "..."
    noi_tam_tru = getattr(citizen, "noi_tam_tru", "...") if citizen else "..."
    noi_o_hien_tai = getattr(citizen, "noi_o_hien_tai", "...") if citizen else "..."

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
                "Nơi thường trú": noi_thuong_tru,
                "Nơi tạm trú": noi_tam_tru,
                "Nơi ở hiện tại": noi_o_hien_tai,
                "Thành viên thay đổi": [],
                "thanh_phan_ho_so": [doc['name'] for doc in required_docs] if required_docs else [],
                "ma_ho_so": ma_ho_so,
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
async def step_finalize_post(request: Request, db: Session = Depends(get_db)):
    try:
        print("[DEBUG] Starting finalize_post")
        session = request.state.session
        print("[DEBUG] Session data:", session)
        
        # Get procedure_id and case_id from session
        procedure_id = session.get("procedure_id")
        case_id = session.get("case_id")
        uploaded_files_info = session.get("uploaded_files_info", [])
        fields = session.get("fields", {})
        
        # Lấy ma_ho_so từ file_info đầu tiên
        ma_ho_so = uploaded_files_info[0].get("ma_ho_so", "") if uploaded_files_info else ""
        
        print("[DEBUG] Before update - procedure_id:", procedure_id, type(procedure_id))
        print("[DEBUG] Before update - case_id:", case_id, type(case_id))
        print("[DEBUG] Before update - uploaded_files_info:", uploaded_files_info)
        print("[DEBUG] ma_ho_so:", ma_ho_so)
        
        # Update procedure_id and case_id in uploaded_files_info
        for file_info in uploaded_files_info:
            file_info["procedure_id"] = procedure_id
            file_info["case_id"] = case_id
        print("[DEBUG] After update - uploaded_files_info:", uploaded_files_info)
        
        # Save case if we have valid procedure_id and uploaded_files_info
        if procedure_id and uploaded_files_info:
            try:
                print("[DEBUG] Attempting to save case with:")
                print("- procedure_id:", procedure_id)
                print("- fields:", fields)
                print("- documents:", uploaded_files_info)
                print("- ma_ho_so:", ma_ho_so)
                
                case = CaseService.save_case(
                    db=db,
                    procedure_id=procedure_id,
                    case_data=fields,
                    documents=uploaded_files_info
                )
                session["saved_case_id"] = case.id
                print("[DEBUG] Successfully saved case:", case.id)

            except Exception as e:
                    print("[ERROR] Failed to save case:", str(e))
                    raise
        else:
                print("[DEBUG] Not saving case because:")
                print("- procedure_id:", procedure_id)
                print("- uploaded_files_info:", bool(uploaded_files_info))

        session.clear()
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        print(f"[ERROR] Error in finalize_post: {str(e)}")
        return templates.TemplateResponse("stepper/finalize.html", {
            "request": request,
            "error": f"Lỗi khi lưu hồ sơ: {str(e)}"
        })

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

@app.get("/cases", response_class=HTMLResponse)
def cases_list(request: Request, db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    return templates.TemplateResponse("reports/cases_list.html", {"request": request, "cases": cases})

@app.get("/case/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return templates.TemplateResponse("reports/case_detail.html", {"request": request, "error": "Không tìm thấy hồ sơ."})
    return templates.TemplateResponse("reports/case_detail.html", {"request": request, "case": case})