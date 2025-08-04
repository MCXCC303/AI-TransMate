from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from create_config import (
    init,
    collect_lang,
    collect_model_remote,
    collect_provider_and_api_key,
    collect_model_local
)
from message_session import remote_talk, local_talk
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from time import sleep
from generate_hash import by_timestamp
import openai
from openai import BadRequestError
import os
import subprocess
import sys
import yaml
from ansi_chars import TerminalColor
import re

__SESSION_ID = ""


def display_config(file_path):
    with open(file_path, "r") as src:
        subprocess.run(['less'], stdin=src)

def command_id(args):
    print(f"Current Session ID: {TerminalColor.YELLOW.value}{__SESSION_ID}{TerminalColor.RESET.value}.")


def command_bye(args):
    raise EOFError


def command_help_translate(args):
    print(
        "Available commands:\n"
        "  /lang\t\tSelect languages\n"
        "  /model\tSelect model\n"
        "  /prov\t\tChange API provider\n"
        "  /show\t\tShow current config\n"
        "  /switch\tSwitch source and target\n"
        "  /bye\t\tExit\n"
        "  /?, /help\tHelp for a command\n"
        f"  {TerminalColor.GRAY.value}/? shortcut\tHelp for keyboard shortcuts{TerminalColor.RESET.value}\n\n"
        'Use """ to begin a multi-line message.\n'
    )


def command_help_normal(args):
    print(
        "Available commands:\n"
        "  /model\tSelect model\n"
        "  /prov\t\tChange model source\n"
        "  /show\t\tShow current config\n"
        "  /role\tSelect role\n"
        "  /bye\t\tExit\n"
        "  /?, /help\tHelp for a command\n"
        "  /? shortcut\tHelp for keyboard shortcuts\n\n"
        'Use """ to begin a multi-line message.\n'
        f"\n{TerminalColor.GRAY.value}(Test mode enabled.){TerminalColor.RESET.value}"
    )


def command_show(args):
    available_opts = ["language", "model", "provider"]
    if not args:
        display_config("./config.yaml")


def command_switch(args):
    if len(args) > 0:
        return
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config["source_lang"], config["target_lang"] = (
        config["target_lang"],
        config["source_lang"],
    )
    with open("config.yaml", "w", encoding="utf-8") as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(
        f"Current language setting: {TerminalColor.BLUE.value}{config['source_lang']}{TerminalColor.RESET.value} to {TerminalColor.RED.value}{config['target_lang']}{TerminalColor.RESET.value}."
    )


def command_lang(args):
    if len(args) > 0:
        return
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config["source_lang"], config["target_lang"] = collect_lang()
    with open("config.yaml", "w", encoding="utf-8") as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(
        f"Current language setting: {TerminalColor.BLUE.value}{config['source_lang']}{TerminalColor.RESET.value} to {TerminalColor.RED.value}{config['target_lang']}{TerminalColor.RESET.value}."
    )


def command_model(args):
    if len(args) > 0:
        return
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    if config["provider"] != "LOCAL":
        config["model"] = collect_model_remote(config["provider"], config["api_key"])
    else:
        config["model"] = collect_model_local()
    with open("config.yaml", "w", encoding="utf-8") as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(f"Current model setting: {TerminalColor.BLUE.value}{config['model']}{TerminalColor.RESET.value}.")


def command_prov(args):
    if len(args) > 0:
        return
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config["provider"], config["api_key"], config["base_url"] = (
        collect_provider_and_api_key()
    )
    if config["provider"] != "LOCAL":
        sys.stdout.write("Authentication succeed. \n\n")
        config["model"] = collect_model_remote(config["provider"], config["api_key"])
    else:
        config["model"] = collect_model_local()
    with open("config.yaml", "w", encoding="utf-8") as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(
        f"Using {TerminalColor.GREEN.value}{config['model']}{TerminalColor.RESET.value} from {TerminalColor.GREEN.value}{config['provider']}{TerminalColor.RESET.value}."
    )


def parse_command(command_text: str):
    with open("config.yaml") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    role = config['role']
    command_mapping_basic = {
        "bye": command_bye,
        "help": command_help_translate,
        "?": command_help_translate,
        "id": command_id,
        "show": command_show,
        "model": command_model,
        "prov": command_prov,
        "role": command_role_test
    }
    command_mapping_translate = {**command_mapping_basic,
                                 "lang": command_lang,
                                 "switch": command_switch,
                                 }
    command_mapping_talk = {**command_mapping_basic}
    role_mapping = {'translate': command_mapping_translate,
                    'talk': command_mapping_talk}
    try:
        command = command_text.split()[0]
        args = command_text.split()[1:]
    except Exception as e:
        print(f"Unknown command. Type /? for help")
        return
    if command not in role_mapping[role].keys():
        print(f"Unknown command '/{command}'. Type /? for help")
        return
    role_mapping[role][command](args)


def command_role_test(args):
    pass


def command_help_test(args):
    pass


def command_show_test(args):
    pass


# def command_model_test(args):
#     pass


def parse_command_test(command_text: str):
    command_mapping = {
        "bye": command_bye,
        "help": command_help_test,
        "?": command_help_test,
        "show": command_show_test,
        "model": command_model,
        "prov": command_prov,
        "role": command_role_test,
    }
    command = command_text.split()[0]
    args = command_text.split()[1:]
    if command not in command_mapping.keys():
        print(f"Unknown command '/{command}'. Type /? for help")
        return
    command_mapping[command](args)


def cli_old() -> None:
    history_file_id = by_timestamp()
    # Check connection
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    while True:
        try:
            if config["provider"] != "LOCAL":
                client = openai.OpenAI(
                    api_key=config["api_key"], base_url=config["base_url"]
                )
                try:
                    response = client.models.list()
                except openai.NotFoundError:
                    pass
                print(
                    f"Connected to {TerminalColor.CYAN.value}{config['provider']}{TerminalColor.RESET.value}."
                    f"\nUsing {TerminalColor.GREEN.value}{config['model']}{TerminalColor.RESET.value} to Translate."
                )
            else:
                print("Using Local Models.")
            sleep(0.3)
            if config["role"] == "translate":
                print(
                    f"Current language setting: {TerminalColor.BLUE.value}{config['source_lang']}{TerminalColor.RESET.value} to {TerminalColor.RED.value}{config['target_lang']}{TerminalColor.RESET.value}."
                )
            else:
                print(f"Test mode enabled. This may occur unexpected errors.")
            sleep(0.5)
            print(f"Current Session ID: {TerminalColor.YELLOW.value}{history_file_id}{TerminalColor.RESET.value}.")
            print(f"{TerminalColor.GRAY.value}(/? for help){TerminalColor.RESET.value}\n")
            break
        except KeyboardInterrupt:
            print("Exiting...")
            return
        except:
            print(f"Failed to connect to {config['provider']}. Retrying...")
            sleep(1)
    # history enabled
    session = PromptSession(history=FileHistory(".translate_history"),
                            auto_suggest=AutoSuggestFromHistory())
    multiline_mode = False
    buffer: list = []
    while True:
        talk = remote_talk
        if config["provider"] == "LOCAL":
            talk = local_talk
        try:
            if not multiline_mode:
                text = session.prompt(">>> ")
                stripped_text = text.strip()
                if stripped_text[0:2] == '"""' and len(stripped_text) > 3:
                    continue
                if stripped_text != '"""':  # Single Line
                    if not text.strip():
                        continue
                    if text[0] == "/":
                        parse_command(text[1:])
                        continue
                    message = text
                    # session create by message
                    talk(text=message, history_id=history_file_id)
                    continue

                multiline_mode = True
                buffer = []
            else:
                text = session.prompt("... ")
                stripped_text = text.strip()
                if stripped_text == '"""':  # End multiline
                    multiline_mode = False
                    message = "\n".join(buffer)
                    talk(text=message, history_id=history_file_id)
                    buffer = []
                else:
                    buffer.append(text)

        except EOFError:
            # Ctrl + d to exit
            print("Exiting...")
            break

        except KeyboardInterrupt:
            # Ctrl + c clear input
            if multiline_mode:
                multiline_mode = False
                buffer = []
            print()
            continue


def cli() -> None:
    global __SESSION_ID
    history_file_id = by_timestamp()
    __SESSION_ID = history_file_id
    # Check connection
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    while True:
        try:
            if config["provider"] != "LOCAL":
                client = openai.OpenAI(
                    api_key=config["api_key"], base_url=config["base_url"]
                )
                try:
                    response = client.models.list()
                except openai.NotFoundError:
                    pass
                print(
                    f"Connected to {TerminalColor.CYAN.value}{config['provider']}{TerminalColor.RESET.value}."
                    f"\nUsing {TerminalColor.GREEN.value}{config['model']}{TerminalColor.RESET.value} to Translate."
                )
            else:
                print("Using Local Models.")
            sleep(0.3)
            if config["role"] == "translate":
                print(
                    f"Current language setting: {TerminalColor.BLUE.value}{config['source_lang']}{TerminalColor.RESET.value} to {TerminalColor.RED.value}{config['target_lang']}{TerminalColor.RESET.value}."
                )
            else:
                print(f"Test mode enabled. This may occur unexpected errors.")
            sleep(0.5)
            print(f"Current Session ID: {TerminalColor.YELLOW.value}{history_file_id}{TerminalColor.RESET.value}.")
            print(f"{TerminalColor.GRAY.value}(/? for help){TerminalColor.RESET.value}\n")
            break
        except KeyboardInterrupt:
            print("Exiting...")
            return
        except:
            print(f"Failed to connect to {config['provider']}. Retrying...")
            sleep(1)

    # 创建PromptSession时配置续行提示符
    session = PromptSession(
        history=FileHistory(".translate_history"),
        prompt_continuation=lambda width, line_number, wrap_count: (
            f"... "
            if line_number > 0 else ""
        ),
        wrap_lines=True
    )

    multiline_mode = False
    buffer: list = []
    while True:
        talk = remote_talk if config["provider"] != "LOCAL" else local_talk
        try:
            if not multiline_mode:
                try:
                    text = session.prompt(">>> ")
                except KeyboardInterrupt:
                    continue

                # 检测粘贴的多行内容（包含换行符）
                if '\n' in text:
                    lines = text.split('\n')
                    # 显示粘贴的多行内容模拟多行输入
                    for line in lines[1:]:
                        print(f"... {line}")
                    # 合并处理所有行
                    message = '\n'.join(lines)
                    talk(text=message, history_id=history_file_id)
                    continue

                stripped_text = text.strip()
                if stripped_text.startswith('"""') and len(stripped_text) > 3:
                    continue
                if stripped_text == '"""':
                    multiline_mode = True
                    buffer = []
                else:
                    if not text:
                        continue
                    if text.startswith("/"):
                        parse_command(text[1:])
                        continue
                    talk(text=text, history_id=history_file_id)
            else:
                text = session.prompt("... ")
                stripped_text = text.strip()
                if stripped_text == '"""':
                    multiline_mode = False
                    message = "\n".join(buffer)
                    talk(text=message, history_id=history_file_id)
                    buffer = []
                else:
                    buffer.append(text)

        except EOFError:
            print("Exiting...")
            break
        except KeyboardInterrupt:
            if multiline_mode:
                multiline_mode = False
                buffer = []
            print()
            continue
        except BadRequestError as e:
            if e.code == 'invalid_request_error' and "maximum context length" in str(e):
                error_msg = e.response.json()["error"]["message"]
                max_tokens = re.search(r"maximum context length is (\d+) tokens", error_msg)
                requested_tokens = re.search(r"requested (\d+) tokens", error_msg)
                print(f"{TerminalColor.RED.value}Your input is {int(requested_tokens.group(1))/int(max_tokens.group(1))*100:.2f}% of maximum tokens. Cut off some content to continue.{TerminalColor.RESET.value}")
            else:
                print(e)
            continue



if __name__ == "__main__":
    config_file = "./config.yaml"
    if not os.path.exists(config_file):
        init()
    else:
        print("Loading config...\n")
    cli()
