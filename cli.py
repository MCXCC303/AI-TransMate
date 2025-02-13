import os
import sys
from time import sleep
import openai
import yaml
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from create_config import init
from message_session import translate
from create_config import collect_lang, collect_model, collect_provider_and_api_key
import tempfile
import shutil
import subprocess


def display_config(file_path):
    tmp_fd, tmp_name = tempfile.mkstemp(suffix='.swp', text=True)
    try:
        with open(file_path, 'r') as src, os.fdopen(tmp_fd, 'w') as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(tmp_name, 0o444)
        editor = os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'vi'
        subprocess.call([editor, tmp_name])
    finally:
        os.unlink(tmp_name)


def command_bye(args):
    raise EOFError


def command_help(args):
    if not args:
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


def command_show(args):
    available_opts = ['language', 'model', 'provider']
    if not args:
        display_config('./config.yaml')


def command_switch(args):
    if len(args) > 0:
        return
    with open('config.yaml', 'r', encoding='utf-8') as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config['source_lang'], config['target_lang'] = config['target_lang'], config['source_lang']
    with open('config.yaml', 'w', encoding='utf-8') as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(
        f"Current language setting: \033[34m{config['source_lang']}\033[0m to \033[31m{config['target_lang']}\033[0m.")


def command_lang(args):
    if len(args) > 0:
        return
    with open('config.yaml', 'r', encoding='utf-8') as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config['source_lang'], config['target_lang'] = collect_lang()
    with open('config.yaml', 'w', encoding='utf-8') as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(
        f"Current language setting: \033[34m{config['source_lang']}\033[0m to \033[31m{config['target_lang']}\033[0m.")


def command_model(args):
    if len(args) > 0:
        return
    with open('config.yaml', 'r', encoding='utf-8') as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config['model'] = collect_model(config['provider'], config['api_key'])
    with open('config.yaml', 'w', encoding='utf-8') as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(f"Current model setting: \033[34m{config['model']}\033[0m.")


def command_prov(args):
    if len(args) > 0:
        return
    with open('config.yaml', 'r', encoding='utf-8') as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    config['provider'], config['api_key'], config['base_url'] = collect_provider_and_api_key()
    sys.stdout.write("Authentication succeed. \n\n")
    config['model'] = collect_model(config['provider'], config['api_key'])
    with open('config.yaml', 'w', encoding='utf-8') as conf:
        yaml.dump(config, conf, Dumper=yaml.SafeDumper)
    print(f"Using \033[32m{config['model']}\033[0m from \033[32m{config['provider']}\033[0m.")


def parse_command(command_text: str):
    command_mapping = {
        "bye": command_bye,
        "help": command_help,
        "?": command_help,
        "show": command_show,
        "switch": command_switch,
        "lang": command_lang,
        "model": command_model,
        "prov": command_prov,
    }
    command = command_text.split()[0]
    args = command_text.split()[1:]
    if command not in command_mapping.keys():
        print(f"Unknown command '/{command}'. Type /? for help")
        return
    command_mapping[command](args)


def cli() -> None:
    # Check connection
    with open('config.yaml', 'r', encoding='utf-8') as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    while True:
        try:
            client = openai.OpenAI(api_key=config['api_key'], base_url=config['base_url'])
            response = client.models.list()
            print(f"Connected to \033[36m{config['provider']}\033[0m."
                  f"\nUsing \033[32m{config['model']}\033[0m to Translate.")
            sleep(0.3)
            print(
                f"Current language setting: \033[34m{config['source_lang']}\033[0m to \033[31m{config['target_lang']}\033[0m.")
            sleep(0.5)
            print('\033[90m(/? for help)\033[0m\n')
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
                    translate(message)
                    continue

                multiline_mode = True
                buffer = []
            else:
                text = session.prompt("... ")
                stripped_text = text.strip()
                if stripped_text == '"""':  # End multiline
                    multiline_mode = False
                    message = "\n".join(buffer)
                    translate(text=message)
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
    config_file = './config.yaml'
    if not os.path.exists(config_file):
        init()
    else:
        print("Loading config...\n")
    cli()
