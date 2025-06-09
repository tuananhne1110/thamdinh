from flask import Flask, render_template, request, redirect, url_for, jsonify
from ultralytics import YOLO
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Tạo thư mục uploads nếu chưa tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load mô hình YOLO
try:
    model = YOLO('best.pt')
    print("Model loaded successfully!")
    print("Model classes:", model.names)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# Các loại file được phép
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Danh sách mẫu tài liệu yêu cầu
REQUIRED_TEMPLATES = [
    {
        'id': 1,
        'name': 'Đơn đăng ký tạm trú',
        'description': 'Mẫu đơn đăng ký tạm trú theo quy định',
        'status': 'missing'
    },
    {
        'id': 2,
        'name': 'CMND/CCCD người đăng ký',
        'description': 'Bản sao có công chứng CMND/CCCD',
        'status': 'missing'
    },
    {
        'id': 3,
        'name': 'Giấy tờ chứng minh chỗ ở hợp pháp',
        'description': 'Các loại giấy tờ pháp lý đa dạng chứng minh quyền sử dụng, sở hữu hoặc thuê chỗ ở ',
        'status': 'missing'
    },
    {
        'id': 4,
        'name': 'Giấy chứng nhận quyền sở hữu nhà',
        'description': 'Sổ đỏ hoặc giấy tờ chứng minh quyền sở hữu',
        'status': 'missing'
    }
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'error': 'No file part'})
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Thêm timestamp để tránh trùng tên file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            filename = timestamp + filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Thông tin file đã upload
            file_info = {
                'name': file.filename,
                'saved_name': filename,
                'type': file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'path': file_path,
                'size': os.path.getsize(file_path)
            }
            uploaded_files.append(file_info)
    
    return jsonify({'files': uploaded_files})

@app.route('/classify', methods=['POST'])
def classify_documents():
    try:
        if model is None:
            return jsonify({'error': 'Model not loaded'})
        
        data = request.get_json()
        files_to_classify = data.get('files', [])
        
        classified_results = []
        
        for file_info in files_to_classify:
            file_path = file_info.get('path')
            
            if not os.path.exists(file_path):
                continue
                
            try:
                # Chạy phân loại với YOLO
                results = model(file_path)
                
                # Lấy kết quả phân loại
                if results and len(results) > 0:
                    result = results[0]
                    if hasattr(result, 'probs') and result.probs is not None:
                        # Classification model
                        top1_idx = result.probs.top1
                        confidence = float(result.probs.top1conf)
                        class_name = model.names[top1_idx]
                        
                        # Map class name to template
                        matched_template = map_class_to_template(class_name, confidence)
                        
                        classified_result = {
                            'file': file_info,
                            'predicted_class': class_name,
                            'confidence': confidence,
                            'matched_template': matched_template,
                            'status': 'success'
                        }
                    else:
                        # Detection model fallback
                        classified_result = {
                            'file': file_info,
                            'predicted_class': 'unknown',
                            'confidence': 0.0,
                            'matched_template': None,
                            'status': 'no_classification'
                        }
                else:
                    classified_result = {
                        'file': file_info,
                        'predicted_class': 'unknown',
                        'confidence': 0.0,
                        'matched_template': None,
                        'status': 'no_result'
                    }
                    
            except Exception as e:
                classified_result = {
                    'file': file_info,
                    'error': str(e),
                    'status': 'error'
                }
            
            classified_results.append(classified_result)
        
        # Cập nhật trạng thái các template
        updated_templates = update_template_status(classified_results)
        
        return jsonify({
            'classified_files': classified_results,
            'templates': updated_templates
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

def map_class_to_template(class_name, confidence):
    """Map predicted class to required template"""
    class_template_mapping = {
        'ct01': {'id': 1, 'name': 'Đơn đăng ký tạm trú'},
        'cccd': {'id': 2, 'name': 'CMND/CCCD người đăng ký'},
        'residence_proof': {'id': 3, 'name': 'Giấy tờ chứng minh chỗ ở hợp pháp'},
        'property_certificate': {'id': 4, 'name': 'Giấy chứng nhận quyền sở hữu nhà'},
    }
    if class_name and class_name.lower() in class_template_mapping:
        template = class_template_mapping[class_name.lower()]
        template['confidence'] = confidence
        return template
    return None

def update_template_status(classified_results):
    """Update template status based on classification results"""
    templates = REQUIRED_TEMPLATES.copy()
    
    for template in templates:
        template['status'] = 'missing'
        template['matched_files'] = []
    
    for result in classified_results:
        if result.get('matched_template'):
            template_id = result['matched_template']['id']
            for template in templates:
                if template['id'] == template_id:
                    if result['confidence'] > 0.8:
                        template['status'] = 'matched'
                    elif result['confidence'] > 0.5:
                        template['status'] = 'needs_review'
                    else:
                        template['status'] = 'low_confidence'
                    
                    template['matched_files'].append({
                        'file': result['file'],
                        'confidence': result['confidence']
                    })
                    break
    
    return templates

@app.route('/get_templates')
def get_templates():
    return jsonify(REQUIRED_TEMPLATES)

if __name__ == '__main__':
    app.run(debug=True, port=5000)