import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime, date
from app.database import SessionLocal
from app.services.citizen_service import CitizenService

def seed_data():
    db = SessionLocal()
    try:
        service = CitizenService(db)
        
        # Thêm dữ liệu công dân
        citizens = [
            {
                'cccd': '404597490141',
                'ho_ten': 'Huỳnh Gia Khánh',
                'ngay_sinh': date(1977, 12, 2),
                'gioi_tinh': 'Nữ',
                'noi_thuong_tru': '123 Đường Lê Thánh Tôn, Quận 1, TP.HCM',
                'noi_o_hien_tai': '123 Đường Lê Thánh Tôn, Quận 1, TP.HCM',
                'noi_tam_tru': None
            },
            {
                'cccd': '216999234501',
                'ho_ten': 'Trần Thanh Quỳnh',
                'ngay_sinh': date(1992, 2, 2),
                'gioi_tinh': 'Nữ',
                'noi_thuong_tru': '456 Đường XYZ, Quận Gò Vấp, TP.HCM',
                'noi_o_hien_tai': None,
                'noi_tam_tru': '567 Đường XYZ, Quận Gò Vấp, TP.HCM'
            },
            {
                'cccd': '108620070839',
                'ho_ten': 'Đỗ Thành Chi',
                'ngay_sinh': date(1981, 10, 15),
                'gioi_tinh': 'Nữ',
                'noi_thuong_tru': '123 Đường Lê Thánh Tôn, Quận 1, TP.HCM',
                'noi_o_hien_tai': '123 Đường Lê Thánh Tôn, Quận 1, TP.HCM',
                'noi_tam_tru': None
            },
            {
                'cccd': '930604961989',
                'ho_ten': 'Bùi Nhật Phát',
                'ngay_sinh': date(2008, 8, 3),
                'gioi_tinh': 'Nam',
                'noi_thuong_tru': '123 Đường Lê Thánh Tôn, Quận 1, TP.HCM',
                'noi_o_hien_tai': '123 Đường Lê Thánh Tôn, Quận 1, TP.HCM',
                'noi_tam_tru': None
            }
        ]
        
        for citizen_data in citizens:
            service.create_citizen(citizen_data)
            
    finally:
        db.close()

if __name__ == "__main__":
    seed_data() 