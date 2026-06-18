"""通用 OpenAI 兼容提供商（SiliconFlow, Aliyun, Tencent 等）。"""

from .base import BaseProvider

class OpenAICompatProvider(BaseProvider):
	"""通用 OpenAI 兼容行为，无特殊参数。"""

	name = "openai-compat"
