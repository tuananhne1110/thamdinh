class Form_CT01_Prompt_Generator:
    def __init__(self):
        self.template = """
- Bạn là một hệ thống trích xuất thông tin từ văn bản hành chính. 
- Dưới đây là nội dung từ các loại giấy tờ thường gặp trong hồ sơ cư trú.

- Hãy trích xuất các trường thông tin sau và trả về dưới dạng MD có cấu trúc rõ ràng:
I. Loại giấy tờ: 
II. Kính gửi:
1. Họ và tên:
2. Ngày tháng năm sinh:
3. Giới tính:
4. Số định danh cá nhân:
5. Số điện thoại liên hệ:
6. Email:
7. Họ và tên chủ hộ:
8. Mối quan hệ với chủ hộ:
9. Số định danh cá nhân của chủ hộ:
10. Nội dung đề nghị:
11. Thông tin về thành viên trong hộ gia đình cùng thay đổi
11.1. Thành viên 1
11.1.1. Họ và tên: 
11.1.2. Ngày tháng năm sinh: 
11.1.3. Giới tính: 
11.1.4. Số định danh cá nhân: 
11.1.5. Mối quan hệ với chủ hộ:
11.2. Thành viên 2
...

- **Chỉ trích xuất thông tin từ nội dung được cung cấp bên dưới, không chỉnh sửa, không phỏng đoán, không tạo dữ liệu nếu thiếu**. 
- Khi đưa ra thông tin trích xuất, tiến hành đánh số như quy tắc trên, phải đủ hai mục I. và II., phải đủ từ mục 1. đến mục 10., mỗi thông tin được in ra trên một hàng, không cần in đậm, không in nghiêng.
- Không in ra các dòng trống cách đoạn, giữa các dòng thông tin phải nối liền nhau.
- Không cần in ra giới thiệu, không cần đặt trong khối ```markdown hoặc ```. 
- Nếu thông tin không có, hãy để trống.
- Lưu ý phải có phần Loại giấy tờ và Kính gửi được đánh thứ tự theo số la mã, các phần còn lại được đánh thứ tự theo số tự nhiên.

- Loại giấy tờ có thể là:
    + Tờ khai thay đổi thông tin cư trú
    + Phiếu khai báo tạm vắng
    + Đơn xin xác nhận cư trú
    + Đơn xin đăng ký thường trú
    + Giấy cam kết (về chỗ ở, quan hệ thân nhân...)

- Lưu ý rằng hai mã số định danh của mục 4 và mục 9 nằm ở đầu nội dung OCR.

- Đối với mục 6. Email, giữ nguyên như thông tin được OCR và không chỉnh sửa, kể cả ký tự đặc biệt không hợp lý.

- Đối với thông tin về thành viên trong hộ gia đình cùng thay đổi, tiến hành liệt kê thông tin của từng thành viên: bao gồm họ tên, ngày tháng năm sinh, giới tính, số định danh cá nhân, mối quan hệ với chủ hộ.
- Nếu có Thông tin về thành viên trong hộ gia đình cùng thay đổi, phải có phần 11.1. Thành viên 1 rồi tiếp đến các phần 11.1.1, 11.1.2,... và tương tự cho 11.2. Thành viên 2.
- Nếu với bất kỳ thành viên, chỉ có số ít thông tin thì vẫn đưa ra các mục thông tin tương ứng, mục nào thiếu thì để trống.
- Nếu không có thành viên nào cho mục 11 thì không in ra mục 11, dừng ngang mục 10, không in ra giới thiệu gì thêm và kết thúc cuộc trò chuyện.

- Văn bản đã được OCR: {text}
"""

    def generate(self, text: str) -> str:
        return self.template.format(text=text)

    def __call__(self, text: str) -> str:
        return self.generate(text) 