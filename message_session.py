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
    console = Console()
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
