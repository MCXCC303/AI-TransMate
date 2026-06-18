"""提供商基类，定义 OpenAI 兼容接口的默认行为。"""

from dataclasses import dataclass

@dataclass
class Provider:
	"""provider/模型信息。"""
	name: str
	base_url: str
	api_key: str
	model: str

class BaseProvider:
	"""OpenAI 兼容的默认行为。"""

	name = "openai-compat"

	def get_chat_kwargs(self, messages: list, model: str, *,
	                    stream: bool = True,
	                    enable_thinking: bool = False) -> dict:
		"""构建 chat.completions.create 的额外参数。"""
		return {"model": model, "stream": stream, "messages": messages}

	def get_detect_kwargs(self, prompt: str, model: str) -> dict:
		"""构建检测调用的参数。"""
		return {
			"model": model,
			"messages": [{"role": "system", "content": prompt}],
			"temperature": 0.1,
			"max_tokens": 32,
		}

	@staticmethod
	def parse_stream_chunk(chunk) -> tuple[str | None, str | None]:
		"""解析流式 chunk，返回 (reasoning_content, content)。"""
		delta = chunk.choices[0].delta
		rc = getattr(delta, "reasoning_content", None)
		content = delta.content
		return rc, content

	@staticmethod
	def parse_response(response) -> tuple[str, str | None]:
		"""解析非流式响应，返回 (content, reasoning_content)。"""
		msg = response.choices[0].message
		return getattr(msg, "content", "") or "", getattr(msg, "reasoning_content", None)

	def build_assistant_message(self, content: str, reasoning: str | None = None) -> dict:
		"""构建追加到历史中的 assistant 消息。"""
		msg: dict = {"role": "assistant", "content": content}
		return msg
