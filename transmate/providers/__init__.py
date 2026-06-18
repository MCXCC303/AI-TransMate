"""LLM 提供商抽象层，封装各提供商的 API 差异。"""

from .base import BaseProvider, Provider
from .deepseek import DeepSeekProvider
from .openai_compat import OpenAICompatProvider

_provider_registry: dict[str, type[BaseProvider]] = {
	"DEEPSEEK": DeepSeekProvider,
}

def get_provider(name: str) -> BaseProvider:
	cls = _provider_registry.get(name.upper(), OpenAICompatProvider)
	return cls()
