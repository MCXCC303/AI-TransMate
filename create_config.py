import json
import sys
import time
import openai
import yaml
from pathlib import Path
import getpass
import ollama
from ansi_chars import TerminalColor

def collect_lang() -> tuple:
    with open("lang/en_US.json") as jsonfile:
        mapping = json.load(jsonfile)
    sys.stdout.write("Available languages:\n\n")
    count = 0
    for lang in mapping.keys():
        sys.stdout.write(f"{count}) {lang}\t")
        if len(lang) < 12:
            sys.stdout.write("\t")
        count += 1
        if count % 2 == 0:
            sys.stdout.write("\n")
    sys.stdout.write(f"\n\n{TerminalColor.GREEN_BOLD.value}Source Language: {TerminalColor.RESET.value}")
    sys.stdout.flush()
    while True:
        input_source_lang = input().strip()
        try:
            source_index = int(input_source_lang)
            source_lang = list(mapping.keys())[source_index]
            break
        except ValueError:
            pass
        except IndexError:
            sys.stdout.write(
                f"\nERROR: Source language not exist.\n"
                f"\n{TerminalColor.GREEN_BOLD.value}Source Language: {TerminalColor.RESET.value}"
            )
            continue
        source_lang = input_source_lang
        if source_lang not in mapping.keys():
            sys.stdout.write(
                f"\nERROR: Language {source_lang} not available.\n"
                f"\n{TerminalColor.GREEN_BOLD.value}Source Language: {TerminalColor.RESET.value}"
            )
            continue
        break
    sys.stdout.write(f"{TerminalColor.GREEN_BOLD.value}Target Language: {TerminalColor.RESET.value}")
    sys.stdout.flush()
    while True:
        input_target_lang = input().strip()
        try:
            target_index = int(input_target_lang)
            target_lang = list(mapping.keys())[target_index]
            if target_lang == source_lang:
                raise KeyError
            break
        except ValueError:
            pass
        except IndexError:
            sys.stdout.write(
                f"\nERROR: Target language not exist.\n"
                f"\n{TerminalColor.GREEN_BOLD.value}Target Language: {TerminalColor.RESET.value}"
            )
            continue
        except KeyError:
            sys.stdout.write(
                f"\nERROR: Can not translate from {target_lang} to itself.\n"
                f"\n{TerminalColor.GREEN_BOLD.value}Target Language: {TerminalColor.RESET.value}"
            )
            continue
        target_lang = input_target_lang
        if target_lang == source_lang:
            sys.stdout.write(
                f"\nERROR: Can not translate from {target_lang} to itself.\n"
                f"\n{TerminalColor.GREEN_BOLD.value}Target Language: {TerminalColor.RESET.value} "
            )
            continue
        if target_lang not in mapping.keys():
            sys.stdout.write(
                f"\nERROR: Language {input_target_lang} not available.\n"
                f"\n{TerminalColor.GREEN_BOLD.value}Target Language: {TerminalColor.RESET.value}"
            )
            continue
        break
    return source_lang, target_lang


def collect_provider_and_api_key() -> tuple:
    with open("./providers/provider_list.yml", "r") as file:
        urls = yaml.load(file, Loader=yaml.FullLoader)
    providers = list(urls.keys())
    sys.stdout.write("Choose an API Model: \n\n")
    count = 0
    for prov in providers:
        sys.stdout.write(f"\t{count}): {prov}\n")
        count += 1
    sys.stdout.write(f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ")
    while True:
        input_provider = input().strip()
        try:
            provider = providers[int(input_provider)]
            break
        except IndexError:
            sys.stdout.write(f"\nERROR: Model not exist." 
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value}")
            continue
        except KeyError:
            sys.stdout.write(f"\nERROR: Model not exist." 
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value}")
            continue
        except ValueError:
            pass
        if input_provider.upper() not in providers:
            sys.stdout.write(f"\nERROR: Model not exist." 
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value}")
            continue
        provider = input_provider.upper()
        break
    if provider == "LOCAL":
        return provider, None, None

    while True:
        try:
            api_key = getpass.getpass(f"Enter your API key in {provider}: ")
            sys.stdout.write("\033[1A\033[2K\nVerifying your API key...\n")
            client = openai.OpenAI(api_key=api_key, base_url=urls[provider])
            try:
                client.models.list()
            except openai.NotFoundError:
                if provider.upper() == "VOLCE":
                    pass
                else:
                    raise openai.AuthenticationError
            break
        except KeyboardInterrupt:
            sys.stdout.write("\nERROR: API key verification failed.\n")
            raise KeyboardInterrupt
        except openai.AuthenticationError:
            sys.stdout.write("\nERROR: API key not valid. Try again.\n")
            continue
    return provider, api_key, urls[provider]


def collect_model_remote(provider, api_key) -> str:
    if provider == "VOLCE":
        sys.stdout.write(f"Enter model id to use: \n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ")
        input_model = input().strip()
        return input_model
    with open("./providers/provider_list.yml", "r") as file:
        urls = yaml.load(file, Loader=yaml.FullLoader)
    with open("./providers/model_info.yaml", "r") as file:
        docs = yaml.load(file, Loader=yaml.FullLoader)
    client = openai.OpenAI(api_key=api_key, base_url=urls[provider])
    models = []
    filter_models = [
        "code",
        # 'math',
        "ocr",
        "vl",
        "diff",
        "audio",
        "sovits",
        "video",
        "janus",
        "flux",
        "qvq",
        "mochi",
        "-en",
    ]

    for model in client.models.list():
        model_id = model.id.lower()
        if any(key in model_id for key in filter_models):
            continue
        models.append(model.id)
    if provider == "ALIYUN":
        models += [
            # "deepseek-r1",
            # "deepseek-v3",
            # "deepseek-r1-distill-qwen-1.5b",
            # "deepseek-r1-distill-qwen-14b",
            # "deepseek-r1-distill-qwen-32b",
            # "deepseek-r1-distill-llama-70b",
            # "deepseek-r1-distill-llama-8b",
            # "deepseek-r1-distill-qwen-7b",
        ]
    models.sort()
    print(f"Available models in {provider}: \n")
    ommition = 10
    if len(models) >= ommition:
        for i in range(ommition):
            print(f"\t{models[i]}")
        print("\t...\n")
        print(f"Check more models in {docs[provider]}")
    else:
        for model in models:
            print(f"\t{model}")
    sys.stdout.write(f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ")
    sys.stdout.flush()
    while True:
        try:
            input_model = input().strip()
            if input_model in models:
                break
            sys.stdout.write(f"ERROR: Model not found."
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ")
            sys.stdout.flush()
        except KeyboardInterrupt:
            sys.stdout.write("\nERROR: No model selected.\n")
            sys.stdout.flush()
            raise KeyboardInterrupt
    return input_model


def collect_model_local():
    try:
        models = [mod.model for mod in list(ollama.list())[0][1]]
        print(f"Available local models: \n")
    except ConnectionError:
        print('Failed to find ollama service. Is it opened?')
        return

    count = 0
    for model in models:
        sys.stdout.write(f"\t{count}): {model}\n")
        count += 1
    sys.stdout.write(f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ")
    while True:
        input_model = input().strip()
        try:
            model = models[int(input_model)]
            break
        except IndexError:
            sys.stdout.write(f"\nERROR: Model not exist."
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value}")
            continue
        except KeyError:
            sys.stdout.write(f"\nERROR: Model not exist."
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value}")
            continue
        except ValueError:
            pass
        except KeyboardInterrupt:
            sys.stdout.write("\nERROR: No model selected.\n")
            sys.stdout.flush()
            raise KeyboardInterrupt
        if input_model.upper() not in models:
            sys.stdout.write(f"\nERROR: Model not exist."
                             f"\n{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value}")
            continue
        model = input_model.upper()
        break
    return model


def init() -> None:
    config_yaml = Path("./config.yaml")
    print("Let's get started with some basic configuration.")
    time.sleep(0.5)
    role = "translate"
    if input("Press Enter To Continue...").strip() == "test":
        role = 'talk'
    try:
        # Collect lang
        if role == "translate":
            source_lang, target_lang = collect_lang()
            sys.stdout.write(
                f"\nTranslate from {TerminalColor.BLUE.value}{source_lang}{TerminalColor.RESET.value} to \033[31m{target_lang}{TerminalColor.RESET.value}."
                f"\nYou can change this option later using {TerminalColor.YELLOW.value}/lang{TerminalColor.RESET.value}.\n\n"
            )
            time.sleep(0.5)
        else:
            print("Test mode enabled.\n")
            time.sleep(0.5)
        # Collect provider, key and base_url
        provider, api_key, base_url = collect_provider_and_api_key()
        if provider != "LOCAL":
            sys.stdout.write(
                f"\nAuthentication succeed. "
                f"\nYou can change the provider later using {TerminalColor.YELLOW.value}/prov <PROVIDER>{TerminalColor.RESET.value}.\n\n"
            )
        else:
            print("Testing local model.\n")

        time.sleep(0.5)

        # Collect model
        if provider != "LOCAL":
            model = collect_model_remote(provider=provider, api_key=api_key)
        else:
            model = collect_model_local()

        sys.stdout.write(
            f"\nUsing {TerminalColor.GREEN.value}{model}{TerminalColor.RESET.value} to translate. "
            f"\nYou can change the model later using {TerminalColor.YELLOW.value}/model{TerminalColor.RESET.value}.\n\n"
        )
        data = {
            "role": role,
            "model": model,
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
        }
        if role == "translate":
            data = {**data, "source_lang": source_lang, "target_lang": target_lang}
        with open(config_yaml, "w") as outfile:
            yaml.dump(data, outfile, Dumper=yaml.SafeDumper)
    except KeyboardInterrupt:
        sys.stdout.write("\nYour config will not be saved." "\nExiting...\n")


if __name__ == "__main__":
    init()
