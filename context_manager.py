from contextlib import contextmanager
from typing import Dict, List, Optional, Generator, Callable

import openai


class ChatContextManager:
    def __init__(
        self,
        default_model: str = "deepseek-r1",
        default_temperature: float = 0.7,
        system_message: str = "You are a helpful assistant.",
        max_history: int = 10,
    ):
        """
        Initialize chat context manager
        :param default_model: 默认使用的模型
        :param default_temperature: 默认生成温度
        :param system_message: 系统角色消息
        :param max_history: 最大历史记录长度
        """
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.max_history = max_history

        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_message}
        ]

        # 可扩展的回调函数
        self.pre_hooks: List[Callable] = []
        self.post_hooks: List[Callable] = []

    def add_message(self, role: str, content: str) -> None:
        """添加消息到上下文"""
        self.messages.append({"role": role, "content": content})
        self._trim_history()

    def stream_response(
        self, model: Optional[str] = None, temperature: Optional[float] = None, **kwargs
    ) -> Generator[str, None, None]:
        """流式响应生成器"""
        try:
            response = openai.ChatCompletion.create(
                model=model or self.default_model,
                messages=self.messages,
                temperature=temperature or self.default_temperature,
                stream=True,
                **kwargs,
            )

            full_response = []
            for chunk in response:
                content = chunk.choices[0].delta.get("content", "")
                full_response.append(content)
                yield content

            self.add_message("assistant", "".join(full_response))

        except Exception as e:
            self.handle_error(e)

    def generate_response(
        self, model: Optional[str] = None, temperature: Optional[float] = None, **kwargs
    ) -> str:
        """生成完整响应"""
        try:
            # 执行前置钩子
            for hook in self.pre_hooks:
                hook(self.messages)

            response = openai.ChatCompletion.create(
                model=model or self.default_model,
                messages=self.messages,
                temperature=temperature or self.default_temperature,
                **kwargs,
            )

            content = response.choices[0].message.content
            self.add_message("assistant", content)

            # 执行后置钩子
            for hook in self.post_hooks:
                hook(self.messages, content)

            return content

        except Exception as e:
            self.handle_error(e)
            return ""

    def _trim_history(self) -> None:
        """维护历史记录长度"""
        while len(self.messages) > self.max_history + 1:  # +1 保留系统消息
            del self.messages[1]  # 保留系统消息位置

    def handle_error(self, error: Exception) -> None:
        """统一错误处理"""
        print(f"Error occurred: {str(error)}")
        # 可以扩展自定义错误处理逻辑

    def clear_context(self) -> None:
        """清空上下文（保留系统消息）"""
        self.messages = self.messages[:1]

    def register_hook(self, hook_type: str, hook_func: Callable) -> None:
        """注册回调钩子"""
        if hook_type == "pre":
            self.pre_hooks.append(hook_func)
        elif hook_type == "post":
            self.post_hooks.append(hook_func)


@contextmanager
def chat_context(
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    system_message: str = "You are a helpful assistant.",
    max_history: int = 10
) -> Generator[ChatContextManager, None, None]:
    """上下文管理器工厂函数"""
    manager = ChatContextManager(
        default_model=model,
        default_temperature=temperature,
        system_message=system_message,
        max_history=max_history
    )
    try:
        yield manager
    finally:
        manager.clear_context()

with chat_context(max_history = 5, model='deepseek-r1') as chat:
    while True:
        user_input = input(">>> ")
        if user_input.lower() == "exit":
            break

        chat.add_message("user", user_input)
        response = chat.generate_response()
        print(f"Assistant: {response}")
