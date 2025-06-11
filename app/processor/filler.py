import requests
from concurrent.futures import ThreadPoolExecutor
from .prompt.ct04_prompt import Form_CT04_Prompt_Generator
from .prompt.ct05_prompt import Form_CT05_Prompt_Generator
import json
class LLMFiller:
    def __init__(
        self,
        model_name: str = "deepseek-ai/DeepSeek-V3-0324",
        api_url: str = "https://llm.chutes.ai/v1/chat/completions",
        api_key: str = "Bearer cpk_85bdb580dbdf490a826b8cdf8f8988c7.9491854e5d615e06accecfd40a6cc7c0.ThSobUhbvPO57kvhdknw0zpWoazQQ4Oe",
        max_workers: int = 5,
        max_tokens: int = 2000
    ):
        self.model_name = model_name
        self.api_url = api_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # self.prompt_generator = Form_CT04_Prompt_Generator()  # Không dùng mặc định nữa

        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _build_payload(self, prompt_text: str) -> dict:
        return {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt_text}
            ],
            "max_tokens": self.max_tokens
        }

    def _call_llm_api(self, prompt_text: str) -> str:
        payload = self._build_payload(prompt_text)
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            print(f"[LLM ERROR] {e}")
            return "Lỗi khi gọi LLM API."

    def fill_form(self, extracted_data: dict, form_type: str = 'CT04') -> str:
        """
        Fill form data using LLM based on extracted information
        """
        try:
            # Convert all numeric values to strings
            for key, value in extracted_data.items():
                if isinstance(value, (int, float)):
                    extracted_data[key] = str(value)

            prompt_data = {
                "Tên cơ quan đăng ký cư trú": extracted_data.get("Tên cơ quan đăng ký cư trú", ""),
                "Họ, chữ đệm và tên": extracted_data.get("Họ, chữ đệm và tên", ""),
                "Ngày tháng năm sinh": extracted_data.get("Ngày, tháng, năm sinh", ""),
                "Giới tính": extracted_data.get("Giới tính", ""),
                "Số định danh cá nhân/CMND": extracted_data.get("Số định danh cá nhân", ""),
                "Số điện thoại": extracted_data.get("Số điện thoại", ""),
                "Email": extracted_data.get("Email", ""),
                "Họ và tên chủ hộ": extracted_data.get("Họ, chữ đệm và tên chủ hộ", ""),
                "Mối quan hệ với chủ hộ": extracted_data.get("Quan hệ với chủ hộ", ""),
                "Số định danh cá nhân của chủ hộ": extracted_data.get("Số định danh cá nhân của chủ hộ", ""),
                "Nội dung đề nghị": extracted_data.get("Nội dung đề nghị", ""),
                "family_members": [],
                "thanh_phan_ho_so": extracted_data.get("thanh_phan_ho_so", []),
                "invalid_fields": extracted_data.get("invalid_fields", []),
                "giay_to_thieu": extracted_data.get("giay_to_thieu", []),
                "ngay_lap_phieu": extracted_data.get("ngay_lap_phieu", ""),
                "Ngày lập phiếu": extracted_data.get("Ngày lập phiếu", ""),
                "ma_ho_so": extracted_data.get("ma_ho_so", "")
            }

            # Process family members if available
            if "Thành viên thay đổi" in extracted_data and extracted_data["Thành viên thay đổi"]:
                for member in extracted_data["Thành viên thay đổi"]:
                    member_data = {
                        "name": member.get("Họ, chữ đệm và tên", ""),
                        "dob": member.get("Ngày sinh", ""),
                        "gender": member.get("Giới tính", ""),
                        "id_number": str(member.get("Số định danh cá nhân", "")),
                        "relationship": member.get("Quan hệ với chủ hộ", "")
                    }
                    prompt_data["family_members"].append(member_data)

            # Chọn prompt generator phù hợp
            if form_type == 'CT05':
                prompt_generator = Form_CT05_Prompt_Generator()
            else:
                prompt_generator = Form_CT04_Prompt_Generator()

            # Generate prompt text
            if form_type == 'CT05' or form_type == 'CT04':
                prompt_text = prompt_generator(json.dumps(prompt_data, ensure_ascii=False), ma_ho_so=prompt_data.get('ma_ho_so', ''))
            else:
                prompt_text = prompt_generator(json.dumps(prompt_data, ensure_ascii=False))

            # Call LLM API
            response = self._call_llm_api(prompt_text)
            if not response or response == "Lỗi khi gọi LLM API.":
                return "Không thể điền form tự động. Vui lòng kiểm tra lại dữ liệu."
            return response
        except Exception as e:
            print(f"Error in fill_form: {str(e)}")
            return "Lỗi khi điền form tự động. Vui lòng thử lại."

    def __call__(self, extracted_data: dict, form_type: str = 'CT04') -> str:
        future = self.executor.submit(self.fill_form, extracted_data, form_type)
        return future.result()