def detect_type(filename):
    ext = filename.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg', 'png', 'bmp']:
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    elif ext == 'docx':
        return 'docx'
    elif ext == 'doc':
        return 'doc'
    else:
        raise ValueError(f"Không hỗ trợ định dạng file: .{ext}")