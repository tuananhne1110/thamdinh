FROM python:3.10-slim

# Thiết lập working directory
WORKDIR /app

# Cài đặt các dependencies hệ thống
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    antiword \
    unrtf \
    tcl \
    tk \
    ghostscript \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt
COPY requirements.txt .

# Cài đặt Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ project vào container
COPY . .

# Tạo thư mục uploads
RUN mkdir -p uploads && chmod 777 uploads

# Expose port 8000 cho FastAPI
EXPOSE 8000

# Command để chạy ứng dụng
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"] 