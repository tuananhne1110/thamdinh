import re

def extract_fields(text):
    fields = {}

    name_match = re.search(r"(?:Họ và tên|Tên):\s*(.*)", text)
    id_match = re.search(r"(?:CMND|CCCD|Số định danh):\s*(\d{9,12})", text)
    dob_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    addr_match = re.search(r"(?:Địa chỉ|Nơi cư trú):\s*(.*)", text)

    if name_match:
        fields['ho_ten'] = name_match.group(1).strip()
    if id_match:
        fields['so_giay_to'] = id_match.group(1).strip()
    if dob_match:
        fields['ngay_sinh'] = dob_match.group(1).strip()
    if addr_match:
        fields['dia_chi'] = addr_match.group(1).strip()

    return fields