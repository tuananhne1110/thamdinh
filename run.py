import os
import sys

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Chạy ứng dụng
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api:app", host="0.0.0.0", port=5000, reload=True)