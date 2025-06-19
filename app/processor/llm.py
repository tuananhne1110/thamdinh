import requests
from concurrent.futures import ThreadPoolExecutor
from .prompt.ct01_prompt import Form_CT01_Prompt_Generator


class LLMExtractor:
    def __init__(
        self,
        model_name: str = "deepseek-ai/DeepSeek-V3-0324",
        api_url: str = "https://llm.chutes.ai/v1/chat/completions",
        api_key: str = "Bearer cpk_85bdb580dbdf490a826b8cdf8f8988c7.9491854e5d615e06accecfd40a6cc7c0.ThSobUhbvPO57kvhdknw0zpWoazQQ4Oe",
        max_workers: int = 5,
        max_tokens: int = 999
    ):
        self.model_name = model_name
        self.api_url = api_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.prompt_generator = Form_CT01_Prompt_Generator()

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

    def extract(self, ocr_text: str) -> str:
        prompt_text = self.prompt_generator(ocr_text)
        return self._call_llm_api(prompt_text)

    def __call__(self, ocr_text: str) -> str:
        future = self.executor.submit(self.extract, ocr_text)
        return future.result() 