from google import genai
from config import Config


class _LazyClient:
    """Tạo client Gemini một cách lười biếng.
    Server vẫn khởi động được khi chưa đặt GOOGLE_AI_API_KEY;
    chỉ báo lỗi khi thực sự gọi kiểm duyệt (route /check).
    """

    _real = None

    def _get(self):
        if self._real is None:
            if not Config.api_key:
                raise ValueError("GOOGLE_AI_API_KEY is not set in .env")
            self._real = genai.Client(api_key=Config.api_key)
        return self._real

    @property
    def models(self):
        return self._get().models

    def __getattr__(self, name):
        return getattr(self._get(), name)


client = _LazyClient()
