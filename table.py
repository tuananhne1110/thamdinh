from app.database import SessionLocal
from app.models import Citizen  # Thay bằng model bạn muốn insert

db = SessionLocal()

# Tạo một bản ghi mới
new_citizen = Citizen(
    cccd="849909329561",
    ho_ten="Vũ Văn Lan",
    ngay_sinh="1966-09-14",
    gioi_tinh="Nam",
    noi_thuong_tru="Ha Noi",
    noi_o_hien_tai="Quan 1, TP HCM",
    noi_tam_tru="Quan 1, TP HCM",
)

db.add(new_citizen)
db.commit()
db.refresh(new_citizen)
print("Inserted:", new_citizen)

db.close()