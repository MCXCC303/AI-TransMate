import json
import openai
import sys
import yaml
import ollama
from ansi_chars import TerminalColor
import datetime
import time
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich.console import Console
from pylatexenc.latex2text import LatexNodes2Text
import re


def render_markdown_math_to_terminal(markdown_text):
    inline_pattern = r'\\\((.+?)\\\)'
    display_pattern = r'\\\[(.+?)\\\]'

    dollar_inline_pattern = r'(?<!\\)\$((?:\\\$|[^$])+?)(?<!\\)\$'
    dollar_display_pattern = r'(?<!\\)\$\$((?:\\\$|[^$])+?)(?<!\\)\$\$'

    def replace_inline(match):
        latex = match.group(1)
        return LatexNodes2Text().latex_to_text(latex)

    def replace_display(match):
        latex = match.group(1)
        return "\n" + LatexNodes2Text().latex_to_text(latex) + "\n"

    text = re.sub(dollar_display_pattern, replace_display, markdown_text, flags=re.DOTALL)
    text = re.sub(dollar_inline_pattern, replace_inline, text, flags=re.DOTALL)
    text = re.sub(display_pattern, replace_display, markdown_text, flags=re.DOTALL)
    text = re.sub(inline_pattern, replace_inline, text, flags=re.DOTALL)

    return text


def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{TerminalColor.GRAY_ITALIC.value}Response Time: {end_time - start_time:.6f}{TerminalColor.RESET.value}")
        return result

    return wrapper


# @timeit
def remote_talk(text: str, history_id: str = '0000000'):
    console = Console(record=True)
    current_time = datetime.datetime.now().strftime("%Y.%m.%d, %H:%M")
    reasoning_file_name = f'./history/{history_id}_reasoning.md'
    output_file_name = f'./history/{history_id}_output.md'
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    messages = [{"role": "user", "content": text}]
    client = openai.OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    if config["role"] == "translate":
        prompt_file = "prompt/translate.json"
        with open("lang/en_US.json") as json_file:
            mapping = json.load(json_file)
        source_lang = mapping[config["source_lang"]]
        target_lang = mapping[config["target_lang"]]
        with open(prompt_file) as json_file:
            system_message = json.load(json_file)
            system_message["content"] = (
                system_message["content"]
                .replace("A语言", source_lang)
                .replace("B语言", target_lang)
            )
        messages = [system_message, {"role": "user", "content": text}]
    else:
        system_message = {"role":"system", "content": """
你是一个多语言翻译专家，精通世界主流语言。请遵循以下规则进行交互：

**核心指令：**
当用户输入以严格格式 "tr XX " 开头时（例如 "tr EN " 或 "tr 中文 "），请执行以下操作：
1.  识别 "XX" 部分所指定的目标语言（如 EN 代表英语，ZH 或 中文 代表中文，JA 代表日语，FR 代表法语等）。
2.  将 "tr XX " 之后的所有输入内容，视为需要翻译的源文本。
3.  你的**唯一任务**是将该源文本准确、流畅地翻译成指定的 "XX" 语言。
4.  你的回复**必须且只能**是翻译后的文本，不要添加任何额外的解释、问候、说明或格式（如引号）。

**非翻译模式：**
如果用户的输入不以 "tr XX " 的格式开头，请像往常一样，根据输入内容自由、全面地回答问题或进行对话。

**示例：**

*   **用户输入：** `tr EN 今天天气真好，我们一起去公园散步吧。`
*   **正确回复：** `The weather is really nice today. Let's go for a walk in the park together.`

*   **用户输入：** `tr 法语 Hello, how can I get to the nearest museum?`
*   **正确回复：** `Bonjour, comment puis-je me rendre au musée le plus proche ?`

*   **用户输入：** `请解释一下量子计算的基本原理。`
*   **正确回复：** （正常解释量子计算的基本原理）
        """}
        messages = [system_message, {"role": "user", "content": text}]
    response = client.chat.completions.create(
        model=config["model"], stream=True, messages=messages
    )
    reasoning_response = []
    full_response = []
    with open(output_file_name, "a") as output:
        output.write(f"\n\n---\n\n`{current_time}`\n> Input: \n\n{text}\n\n> Output:\n\n")
    with open(reasoning_file_name, "a") as output:
        output.write(f"\n\n---\n\n`{current_time}`\n> Input: \n\n{text}\n\n> Reasoning Content:\n\n")
    sys.stdout.write("\n")
    with Live(console=console, auto_refresh=False, vertical_overflow="visible") as live:
        for chunk in response:
            reason_text_length = len("".join(reasoning_response))
            try:
                if (
                        config["provider"] == "SILICONFLOW"
                        and "r1" not in config["model"].lower()
                ):
                    raise AttributeError
                if chunk.choices[0].delta.reasoning_content is not None:
                    reasoning_content = chunk.choices[0].delta.reasoning_content
                    reasoning_response.append(reasoning_content)
                if len("".join(reasoning_response)) > reason_text_length:
                    sys.stdout.write(
                        f"{TerminalColor.MOVE_TO_LAST_LINE.value}{TerminalColor.CLEAR_LINE.value}{TerminalColor.GRAY.value}Thinking{'.' * (len(reasoning_response) % 6 + 1)}{TerminalColor.RESET.value}\n"
                    )
                    with open(reasoning_file_name, "a") as output:
                        output.write(reasoning_content)
                    sys.stdout.flush()
            except AttributeError:
                pass
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response.append(content)
                # console.print(Markdown("".join(full_response)), end="")
                # console.print('\r', end="")
                live.update(Markdown(render_markdown_math_to_terminal("".join(full_response))))
                live.refresh()
                # sys.stdout.write(content)
                # sys.stdout.flush()
            with open(output_file_name, "a") as output:
                output.write(content)
    print()
    if full_response and not reasoning_response:
        with open(reasoning_file_name, "a") as f:
            f.write('It seems that this model is not thinking or this model does not support it.')
    if not full_response:
        sys.stdout.write(
            f"{TerminalColor.GRAY_ITALIC.value}Service busy. Try again later or change a provider.{TerminalColor.RESET.value}\n"
        )
        with open(output_file_name, "a") as output:
            output.write("Service busy. Try again later.")


@timeit
def local_talk(text: str, history_id: str = '0000000'):
    current_time = datetime.datetime.now().strftime("%Y.%m.%d, %H:%M")
    reasoning_file_name = f'./history/{history_id}_reasoning.md'
    output_file_name = f'./history/{history_id}_output.md'
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    messages = [{"role": "user", "content": text}]
    if config["role"] == "translate":
        prompt_file = "prompt/translate.json"
        with open("lang/en_US.json") as json_file:
            mapping = json.load(json_file)
        source_lang = mapping[config["source_lang"]]
        target_lang = mapping[config["target_lang"]]
        with open(prompt_file) as json_file:
            system_message = json.load(json_file)
            system_message["content"] = (
                system_message["content"]
                .replace("A语言", source_lang)
                .replace("B语言", target_lang)
            )
        messages = [system_message, {"role": "user", "content": text}]
    response = ollama.chat(model=config['model'], stream=True, messages=messages)
    full_reason_content = []
    full_answer_content = []
    thinking = False
    sys.stdout.write("\n")
    with open(output_file_name, "a") as output:
        output.write(f"\n\n---\n\n`{current_time}`> Input: \n\n{text}\n\n> Output:\n\n")
    with open(reasoning_file_name, "a") as output:
        output.write(f"\n\n---\n\n`{current_time}`> Input: \n\n{text}\n\n> Reasoning Content:\n\n")
    with Live(Text(), refresh_per_second=15, transient=True, vertical_overflow="visible") as live:
        for chunk in response:
            chunk_message = chunk["message"]["content"]
            if chunk_message == "<think>":
                thinking = True
                continue
            if chunk_message == "</think>":
                thinking = False
                sys.stdout.write(
                    f"{TerminalColor.MOVE_TO_LAST_LINE.value}{TerminalColor.CLEAR_LINE.value}{TerminalColor.RESET.value}")
                continue
            if thinking:
                full_reason_content.append(chunk_message)
                with open(reasoning_file_name, "a") as f:
                    f.write(chunk_message)
                sys.stdout.write(
                    f'{TerminalColor.MOVE_TO_LAST_LINE.value}{TerminalColor.CLEAR_LINE.value}{TerminalColor.GRAY.value}Thinking{"." * (len(full_reason_content) % 6 + 1)}{TerminalColor.RESET.value}\n'
                )
            else:
                full_answer_content.append(chunk_message)
                # sys.stdout.write(chunk_message)
                # sys.stdout.flush()
                live.update(Markdown("".join(full_answer_content)))
                with open(output_file_name, "a") as f:
                    f.write(chunk_message)
    if not full_reason_content:
        with open(reasoning_file_name, "a") as f:
            f.write('It seems that this model is not thinking or this model does not support it.')
    print()
