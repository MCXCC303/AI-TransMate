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
import openai
import os
import shutil
import subprocess
import sys
import tempfile
import yaml


def display_config(file_path):
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".swp", text=True)
    try:
        with open(file_path, "r") as src, os.fdopen(tmp_fd, "w") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(tmp_name, 0o444)
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
        subprocess.call([editor, tmp_name])
    finally:
        os.unlink(tmp_name)


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
        "  \033[90m/? shortcut\tHelp for keyboard shortcuts\033[0m\n\n"
        'Use """ to begin a multi-line message.\n'
    )


def command_help_normal(args):
    print(
        "Available commands:\n"
        "  /model\tSelect model\n"
        "  /prov\t\tChange model source\n"
        "  /show\t\tShow current config\n"
        "  /prompt\tSelect role\n"
        "  /bye\t\tExit\n"
        "  /?, /help\tHelp for a command\n"
        "  /? shortcut\tHelp for keyboard shortcuts\n\n"
        'Use """ to begin a multi-line message.\n'
        "\n\033[90m(Test mode enabled.)\033[0m"
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
        f"Current language setting: \033[34m{config['source_lang']}\033[0m to \033[31m{config['target_lang']}\033[0m."
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
        f"Current language setting: \033[34m{config['source_lang']}\033[0m to \033[31m{config['target_lang']}\033[0m."
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
    print(f"Current model setting: \033[34m{config['model']}\033[0m.")


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
        f"Using \033[32m{config['model']}\033[0m from \033[32m{config['provider']}\033[0m."
    )


def parse_command(command_text: str):
    with open("config.yaml") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    role = config['role']
    command_mapping_basic = {
        "bye": command_bye,
        "help": command_help_translate,
        "?": command_help_translate,
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
    command = command_text.split()[0]
    args = command_text.split()[1:]
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


def cli() -> None:
    # Check connection
    with open("config.yaml", "r", encoding="utf-8") as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    while True:
        try:
            if config["provider"] != "LOCAL":
                client = openai.OpenAI(
                    api_key=config["api_key"], base_url=config["base_url"]
                )
                response = client.models.list()
                print(
                    f"Connected to \033[36m{config['provider']}\033[0m."
                    f"\nUsing \033[32m{config['model']}\033[0m to Translate."
                )
            else:
                print("Using Local Models.")
            sleep(0.3)
            if config["role"] == "translate":
                print(
                    f"Current language setting: \033[34m{config['source_lang']}\033[0m to \033[31m{config['target_lang']}\033[0m."
                )
            else:
                print(f"Test mode enabled. This may occur unexpected errors.")
            sleep(0.5)
            print("\033[90m(/? for help)\033[0m\n")
            break
        except KeyboardInterrupt:
            print("Exiting...")
            return
        except:
            print(f"Failed to connect to {config['provider']}. Retrying...")
            sleep(1)
    # history enabled
    session = PromptSession(history=FileHistory(".translate_history"))
    multiline_mode = False
    buffer = []
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
                    talk(message)
                    continue

                multiline_mode = True
                buffer = []
            else:
                text = session.prompt("... ")
                stripped_text = text.strip()
                if stripped_text == '"""':  # End multiline
                    multiline_mode = False
                    message = "\n".join(buffer)
                    talk(text=message)
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
            continue


if __name__ == "__main__":
    config_file = "./config.yaml"
    if not os.path.exists(config_file):
        init()
    else:
        print("Loading config...\n")
    cli()
