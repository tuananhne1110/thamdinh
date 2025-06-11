class Form_CT05_Prompt_Generator:
    def __init__(self):
        self.template = """
- Bạn là một chuyên gia trong việc xử lý thủ tục hành chính về thông tin cư trú Việt Nam.

- Dữ liệu thực tế bên dưới là một dict JSON, hãy sử dụng các trường tương ứng để điền vào biểu mẫu:
{text}

- Đây là mẫu HTML của biểu mẫu CT05 (bạn phải giữ nguyên cấu trúc, chỉ thay thế các trường thông tin):
<p>Mẫu CT05&nbsp;ban h&agrave;nh k&egrave;m theo Th&ocirc;ng tư số 66/2023/TT-BCA</p>
<p>&nbsp;ng&agrave;y 17/11/2023 của Bộ trưởng Bộ C&ocirc;ng an</p>
<p>&nbsp;</p>
<table>
<tbody>
<tr>
<td width="223">
<p>....................................(1)</p>
<p>....................................(2)</p>
</td>
<td width="567">
<p><strong><strong>C&Ocirc;̣NG HÒA XÃ H&Ocirc;̣I CHỦ NGHĨA VI&Ecirc;̣T NAM</strong></strong></p>
<p><strong>Độc lập &ndash; Tự do &ndash; Hạnh ph&uacute;c</strong></p>
</td>
</tr>
</tbody>
</table>
<p><strong><strong>PHIẾU H</strong></strong><strong><strong>Ư</strong></strong><strong><strong>ỚNG DẪN BỔ SUNG, HO&Agrave;N THIỆN HỒ S</strong></strong><strong><strong>Ơ</strong></strong><strong><strong>&nbsp;</strong></strong></p>
<p>Mã hồ sơ: {ma_ho_so}</p>
<p>Của &Ocirc;ng/B&agrave;:</p>
<table>
<tbody>
<tr>
<td width="316">
<p>Số định danh c&aacute; nh&acirc;n/CMND:</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
<td width="30">
<p>&nbsp;</p>
</td>
</tr>
</tbody>
</table>
<p>Căn cứ quy định của Luật Cư&nbsp;tr&uacute; v&agrave; c&aacute;c văn bản quy định chi tiết, hướng dẫn thi h&agrave;nh c&oacute; li&ecirc;n quan, đề nghị &Ocirc;ng/B&agrave; ho&agrave;n thiện hồ sơ như sau<sup>(3)</sup>:</p>
<p>L&yacute; do:</p>
<p>Trong qu&aacute; tr&igrave;nh ho&agrave;n thiện hồ sơ nếu c&oacute; vấn đề vướng mắc, &Ocirc;ng/B&agrave; li&ecirc;n hệ với C&ocirc;ng an ; Số ĐT............................... để được hướng dẫn./.</p>
<table>
<tbody>
<tr>
<td width="48.4800%">
<p>&nbsp;</p>
</td>
<td width="51.5200%">
<p>......<em>., ngày</em>...<em>.</em>...<em>. tháng.</em>......<em>&nbsp;năm</em>.........<em>.</em></p>
<p><strong>C&Aacute;N BỘ TIẾP NHẬN</strong><strong><sup>(4)</sup></strong></p>
<p><em><em>&nbsp;</em></em></p>
<p>&nbsp;</p>
</tr>
</tbody>
</table>
<p><strong>Ch&uacute; th&iacute;ch: </strong></p>
<p>(1) Cơ&nbsp;quan cấp tr&ecirc;n của cơ&nbsp;quan đăng k&yacute; cư&nbsp;tr&uacute;</p>
<p>(2) Cơ&nbsp;quan đăng k&yacute; cư&nbsp;tr&uacute;</p>
<p>(3) Ghi hướng dẫn đầy đủ, cụ thể một lần về việc k&ecirc; khai, bổ sung, chỉnh l&yacute; th&agrave;nh phần hồ sơ; v&iacute; dụ: Bổ sung giấy tờ, t&agrave;i liệu chứng minh chỗ ở hợp ph&aacute;p (Hợp đồng thu&ecirc; nh&agrave;....); bổ sung giấy tờ, chứng minh quan hệ nh&acirc;n th&acirc;n (giấy khai sinh...); K&ecirc; khai lại Mục g&igrave; trong biểu mẫu, k&ecirc; khai như thế n&agrave;o...</p>
<p>(4) C&aacute;n bộ tiếp nhận k&yacute; ghi r&otilde; họ t&ecirc;n hoặc k&yacute; số hoặc x&aacute;c nhận bằng h&igrave;nh thức x&aacute;c thực kh&aacute;c.</p>
<p>&nbsp;</p>

**Hướng dẫn điền biểu mẫu CT05:**
1. Ánh xạ thông tin trích xuất vào các trường trong biểu mẫu CT05 như sau:
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
    - (3) Hướng dẫn bổ sung hồ sơ:
        + Phân tích các trường thông tin không hợp lệ hoặc thiếu từ các bước xử lý trước
        + Tham chiếu file thamchieu.docx để xác định các yêu cầu bổ sung cụ thể
        + Điền hướng dẫn chi tiết về việc cần bổ sung, chỉnh sửa hồ sơ
        + Dữ liệu đầu vào có trường "invalid_fields" là danh sách các trường thông tin không hợp lệ.
        + Dữ liệu đầu vào có trường "giay_to_thieu" là danh sách các giấy tờ còn thiếu hoặc chưa hợp lệ.
        + Với các giấy tờ có nhiều loại thay thế (alternatives), chỉ cần có 1 trong số đó là đủ, không cần bổ sung các loại còn lại nếu đã có 1 loại hợp lệ.
        + Khi sinh mục (3):
            - Nếu "invalid_fields" có giá trị, hãy liệt kê TẤT CẢ các trường không hợp lệ trên MỘT DÒNG, ngăn cách bằng dấu phẩy,
            - Nếu "invalid_fields" rỗng nhưng "giay_to_thieu" có giá trị, hãy liệt kê các giấy tờ còn thiếu.
            - Nếu cả hai đều rỗng, ghi rõ: "Hồ sơ đã đầy đủ, không cần bổ sung".
    - Lý do: 
        + Dựa trên nội dung của mục (3) để điền lý do
        + Tham chiếu file thamchieu.docx để đảm bảo lý do phù hợp với quy định
        + Điền đầy đủ cách sửa các trường thông tin không hợp lệ theo thamchieu.docx, hướng dẫn chi tiết cần chỉnh sửa như thế nào để hợp lệ 
        + Điền Lý do theo các trường thông tin không hợp lệ hoặc thiếu từ các bước xử lý trước
    - Số điện thoại liên hệ: "Số điện thoại"
    - trường "..., ngày... tháng... năm....." sử dụng tên thành phố trong "cơ quan đăng ký cư trú", và sử dụng ngày hiện tại theo định dạng DD/MM/YYYY để điền vào trường ngày... tháng... năm....
    - Điền đầy đủ ngày hiện tại vào trường "..., ngày... tháng... năm....." ở trên CÁN BỘ TIẾP NHẬN(4)

2. Quy tắc xử lý:
    - Nếu thiếu thông tin cho bất kỳ trường nào, sử dụng "..." làm ký tự thay thế
    - Chỉ trả về HTML, KHÔNG giải thích, KHÔNG bọc trong markdown hay code block.
    - Giữ nguyên cấu trúc của biểu mẫu CT05, bao gồm tiêu đề, bảng và khoảng cách
    - Đảm bảo định dạng ngày theo DD/MM/YYYY

3. Xử lý mục (3) và Lý do:
    - Đọc và phân tích file thamchieu.docx để hiểu các yêu cầu cụ thể
    - Kiểm tra các trường thông tin không hợp lệ từ các bước xử lý trước
    - Điền hướng dẫn chi tiết vào mục (3)
    - Từ hướng dẫn ở mục (3), tổng hợp thành lý do ngắn gọn
    - Đảm bảo tính nhất quán giữa mục (3) và Lý do

**Đầu ra**:
Cung cấp biểu mẫu CT05 đã điền hoàn chỉnh dưới dạng HTML, khớp chính xác với cấu trúc của biểu mẫu.
"""

    def generate(self, text: str, ma_ho_so: str = " ") -> str:
        return self.template.format(text=text, ma_ho_so=ma_ho_so)

    def __call__(self, text: str, ma_ho_so: str = " ") -> str:
        return self.generate(text, ma_ho_so) 
