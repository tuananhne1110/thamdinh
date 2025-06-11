class Form_CT04_Prompt_Generator:
    def __init__(self):
        self.template = """
- Bạn là một chuyên gia trong việc xử lý thủ tục hành chính về thông tin cư trú Việt Nam.

- Dữ liệu thực tế bên dưới là một dict JSON, hãy sử dụng các trường tương ứng để điền vào biểu mẫu:
{text}

Đây là mẫu HTML của biểu mẫu CT04 (bạn phải giữ nguyên cấu trúc, chỉ thay thế các trường thông tin):
<p>Mẫu CT04&nbsp;ban h&agrave;nh k&egrave;m theo Th&ocirc;ng tư số 66/2023/TT-BCA</p>
<p>&nbsp;ng&agrave;y 17/11/2023 của Bộ trưởng Bộ C&ocirc;ng an</p>
<table>
<tbody>
<tr>
<td width="212">
<p>...................................(1)</p>
<p>...................................(2)</p>
<p>&nbsp;</p>
<p>&nbsp;</p>
<p>Số: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/PTN</p>
</td>
<td width="555">
<p><strong><strong>C&Ocirc;̣NG HÒA XÃ H&Ocirc;̣I CHỦ NGHĨA VI&Ecirc;̣T NAM</strong></strong></p>
<p><strong>Độc lập &ndash; Tự do &ndash; Hạnh ph&uacute;c</strong></p>
</td>
</tr>
</tbody>
</table>
<p><strong><strong>PHIẾU TIẾP NHẬN HỒ SƠ V&Agrave; HẸN TRẢ KẾT QUẢ</strong></strong></p>
<p>M&atilde; hồ sơ: {ma_ho_so}</p>
<p>C&ocirc;ng an<sup>(2)</sup>:</p>
<p>đ&atilde; tiếp nhận hồ sơ của &Ocirc;ng/B&agrave;:</p>
<table>
<tbody>
<tr>
<td width="327">
<p>Số định danh c&aacute; nh&acirc;n/CMND:</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
<td width="34">
<p>&nbsp;</p>
</td>
</tr>
</tbody>
</table>
<p>Nơi thường tr&uacute;:&nbsp;</p>
<p>Nơi tạm tr&uacute;:&nbsp;</p>
<p>Nơi ở hiện tại:&nbsp;</p>
<p>Số điện thoại: &nbsp;Email:</p>
<p>Nội dung y&ecirc;u cầu giải quyết:&nbsp;</p>
<p>Th&agrave;nh phần hồ sơ nộp gồm:</p>
<table>
<tbody>
<tr>
<td width="5.6600%">
<p><strong>TT</strong></p>
</td>
<td width="52.1800%">
<p><strong>T&ecirc;n giấy tờ</strong></p>
</td>
<td width="23.9000%">
<p><strong>H&igrave;nh thức </strong></p>
<p><em>(bản ch&iacute;nh, bản sao hoặc bản chụp)</em></p>
</td>
<td width="18.2600%">
<p><strong>Ghi ch&uacute;</strong></p>
</td>
</tr>
<tr>
<td width="5.6600%">
<p>&nbsp;</p>
</td>
<td width="52.1800%">
<p>&nbsp;</p>
</td>
<td width="23.9000%">
<p>&nbsp;</p>
</td>
<td width="18.2600%">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td width="5.6600%">
<p>&nbsp;</p>
</td>
<td width="52.1800%">
<p>&nbsp;</p>
</td>
<td width="23.9000%">
<p>&nbsp;</p>
</td>
<td width="18.2600%">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td width="5.6600%">
<p>&nbsp;</p>
</td>
<td width="52.1800%">
<p>&nbsp;</p>
</td>
<td width="23.9000%">
<p>&nbsp;</p>
</td>
<td width="18.2600%">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td width="5.6600%">
<p>&nbsp;</p>
</td>
<td width="52.1800%">
<p>&nbsp;</p>
</td>
<td width="23.9000%">
<p>&nbsp;</p>
</td>
<td width="18.2600%">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td width="5.6600%">
<p>&nbsp;</p>
</td>
<td width="52.1800%">
<p>&nbsp;</p>
</td>
<td width="23.9000%">
<p>&nbsp;</p>
</td>
<td width="18.2600%">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td width="5.6600%">
<p>&nbsp;</p>
</td>
<td width="52.1800%">
<p>&nbsp;</p>
</td>
<td width="23.9000%">
<p>&nbsp;</p>
</td>
<td width="18.2600%">
<p>&nbsp;</p>
</td>
</tr>
</tbody>
</table>
<p>Thời gian nhận hồ sơ: ............giờ............ph&uacute;t, ng&agrave;y................./.............../.............................</p>
<p>Thời gian trả kết quả giải quyết hồ sơ: ............giờ............ph&uacute;t, ng&agrave;y......../........../............</p>
<p>H&igrave;nh thức nhận kết quả: Bản giấy o&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Bản điện tử o&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Tin nhắn SMS o</p>
<p><em>(C&ocirc;ng d&acirc;n nhận kết quả bản điện tử qua email, th&ocirc;ng b&aacute;o tr&ecirc;n ứng dụng VNeID v&agrave; cổng dịch vụ c&ocirc;ng; th&ocirc;ng b&aacute;o qua tin nhắn SMS tới số điện thoại đ&atilde; khai b&aacute;o)</em></p>
<p>Đăng k&yacute; nhận kết quả Bản giấy tại:</p>
<table>
<tbody>
<tr>
<td width="48.4800%">
<p>&nbsp;</p>
</td>
<td width="51.5200%">
<p>...........,&nbsp;ng&agrave;y............th&aacute;ng...........năm...........</p>
<p><strong>C&Aacute;N BỘ TIẾP NHẬN</strong><strong><sup>(3)</sup></strong><strong>&nbsp;</strong></p>
<p><em><em>&nbsp;</em></em></p>
<p>&nbsp;</p>
<p>&nbsp;</p>
<p>&nbsp;</p>
</td>
</tr>
</tbody>
</table>
<p><strong>Ch&uacute; th&iacute;ch: </strong></p>
<p>(1) Cơ&nbsp;quan cấp tr&ecirc;n của cơ&nbsp;quan đăng k&yacute; cư&nbsp;tr&uacute;.</p>
<p>(2) Cơ&nbsp;quan đăng k&yacute; cư&nbsp;tr&uacute;.</p>
<p>(3) C&aacute;n bộ tiếp nhận c&oacute; thể k&yacute; ghi r&otilde; họ t&ecirc;n hoặc k&yacute; số hoặc x&aacute;c nhận bằng h&igrave;nh thức x&aacute;c thực kh&aacute;c.</p>
<p>&nbsp;</p>

**Hướng dẫn điền biểu mẫu CT04:**
1. Ánh xạ thông tin trích xuất vào các trường trong biểu mẫu CT04 như sau:
    - (1) Cơ quan cấp trên: suy ra từ "Tên cơ quan đăng ký cư trú" 
    Về hệ thống tổ chức ngành công an theo tuyến hành chính:
        + Công an phường, xã, thị trấn trực thuộc → Công an quận, huyện, thị xã, thành phố trực thuộc tỉnh/thành phố.
        + Công an quận/huyện... trực thuộc → Công an tỉnh, thành phố trực thuộc Trung ương.
        + Công an tỉnh, TP trực thuộc TƯ trực thuộc  → Bộ Công an.
    - (2) Cơ quan đăng ký cư trú: "Tên cơ quan đăng ký cư trú"
    - Mã hồ sơ: sử dụng trường "ma_ho_so" (chỉ gồm số, ví dụ: 000001)
    - Tên người nộp: "Họ, chữ đệm và tên"
    - Số định danh cá nhân: "Số định danh cá nhân/CMND"
    - Khi điền số CMND, hãy điền mỗi chữ số vào một ô <td> riêng biệt trong bảng
    - Nơi thường trú: Sử dụng "..." (vì không có trong CT01).
    - Nơi tạm trú: Sử dụng "..." (vì không có trong CT01).
    - Nơi ở hiện tại: Sử dụng "..." (vì không có trong CT01).
    - Số điện thoại: "Số điện thoại"
    - Email: "Email"
    - Nội dung yêu cầu giải quyết: "Nội dung đề nghị"
    - Thành phần hồ sơ nộp: "thanh_phan_ho_so" 
    - Thời gian nhận hồ sơ: Sử dụng giờ hiện tại hoặc "..." nếu không xác định được.
    - Ngày nhận hồ sơ: Sử dụng ngày hiện tại.
    - Thời gian trả kết quả: Sử dụng "..." (vì không có trong CT01).
    - Ngày trả kết quả: Sử dụng "..." (vì không có trong CT01).
    - Hình thức nhận kết quả: Mặc định là "Bản giấy" (vì không có thông tin cụ thể trong CT01).
    - Địa điểm nhận kết quả bản giấy: Sử dụng "Tên cơ quan đăng ký cư trú".
    - trường "..., ngày... tháng... năm....." sử dụng tên thành phố trong "cơ quan đăng ký cư trú", và sử dụng ngày hiện tại theo định dạng DD/MM/YYYY để điền vào trường ngày... tháng... năm....
    - Điền đầy đủ ngày hiện tại vào trường "..., ngày... tháng... năm....." ở trên CÁN BỘ TIẾP NHẬN(4)
2. Bỏ qua các trường liên quan đến "Thành viên hộ gia đình" và "Chủ hộ" trong CT01, vì CT04 chỉ cần thông tin của người nộp chính.
3. Nếu thiếu thông tin cho bất kỳ trường nào, sử dụng "..." làm ký tự thay thế.
4. Chỉ trả về HTML hoàn chỉnh, KHÔNG bọc trong markdown hay plaintext, giữ nguyên cấu trúc của biểu mẫu Mẫu CT04, bao gồm tiêu đề, bảng và khoảng cách.
5. Đảm bảo định dạng ngày theo DD/MM/YYYY và giờ theo HH:MM.
6. Đảm bảo sau khi điền thông tin vào thì sẽ bỏ "..." và thay thế bằng thông tin đã điền.

**Đầu ra**:
Cung cấp biểu mẫu Mẫu CT04 đã điền hoàn chỉnh dưới dạng HTML, khớp chính xác với cấu trúc của biểu mẫu.
"""

    def generate(self, text: str, ma_ho_so: str = "") -> str:
        return self.template.format(text=text, ma_ho_so=ma_ho_so)

    def __call__(self, text: str, ma_ho_so: str = "") -> str:
        return self.generate(text, ma_ho_so) 