import json
import sys
import time
import openai
import yaml
from pathlib import Path
import getpass


def collect_lang() -> tuple:
    with open("./prompt/en_US.json") as jsonfile:
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
    sys.stdout.write("\n\n\033[1;32mSource Language: \033[0m")
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
                "\nERROR: Source language not exist.\n"
                "\n\033[1;32mSource Language: \033[0m"
            )
            continue
        source_lang = input_source_lang
        if source_lang not in mapping.keys():
            sys.stdout.write(
                f"\nERROR: Language {source_lang} not available.\n"
                f"\n\033[1;32mSource Language: \033[0m"
            )
            continue
        break
    sys.stdout.write("\033[1;32mTarget Language: \033[0m")
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
                "\nERROR: Target language not exist.\n"
                "\n\033[1;32mTarget Language: \033[0m"
            )
            continue
        except KeyError:
            sys.stdout.write(
                f"\nERROR: Can not translate from {target_lang} to itself.\n"
                f"\n\033[1;32mTarget Language: \033[0m"
            )
            continue
        target_lang = input_target_lang
        if target_lang == source_lang:
            sys.stdout.write(
                f"\nERROR: Can not translate from {target_lang} to itself.\n"
                f"\n\033[1;32mTarget Language: \033[0m "
            )
            continue
        if target_lang not in mapping.keys():
            sys.stdout.write(
                f"\nERROR: Language {input_target_lang} not available.\n"
                f"\n\033[1;32mTarget Language: \033[0m"
            )
            continue
        break
    return source_lang, target_lang


def collect_provider_and_api_key() -> tuple:
    with open("./providers/provider_list.yml", "r") as file:
        urls = yaml.load(file, Loader=yaml.FullLoader)
    providers = list(urls.keys())
    sys.stdout.write("Choose an API Provider: \n\n")
    count = 0
    for prov in providers:
        sys.stdout.write(f"\t{count}): {prov}\n")
        count += 1
    sys.stdout.write("\n\033[1;32m>>>\033[0m ")
    while True:
        input_provider = input().strip()
        try:
            provider = providers[int(input_provider)]
            break
        except IndexError:
            sys.stdout.write("\nERROR: Provider not exist."
                             "\n\033[1;32m>>>\033[0m")
            continue
        except KeyError:
            sys.stdout.write("\nERROR: Provider not exist."
                             "\n\033[1;32m>>>\033[0m")
            continue
        except ValueError:
            pass
        if input_provider.upper() not in providers:
            sys.stdout.write("\nERROR: Provider not exist."
                             "\n\033[1;32m>>>\033[0m")
            continue
        provider = input_provider.upper()
        break

    while True:
        try:
            api_key = getpass.getpass(f"Enter your API key in {provider}: ")
            sys.stdout.write("\033[1A\033[2K\nVerifying your API key...\n")
            client = openai.OpenAI(api_key=api_key, base_url=urls[provider])
            client.models.list()
            break
        except KeyboardInterrupt:
            sys.stdout.write("\nERROR: API key verification failed.\n")
            raise KeyboardInterrupt
        except openai.AuthenticationError:
            sys.stdout.write("\nERROR: API key not valid. Try again.\n")
            continue
    return provider, api_key, urls[provider]

    # provider_file_name = provider_dir / (provider + '.json')
    # with open(provider_file_name) as jsonfile:
    #     valid_models = {key: value for key, value in json.load(jsonfile).items() if value is not None}
    # sys.stdout.write(f'Available Models in {provider}: \n' +
    #                  '\n'.join(valid_models.keys()) + '\n\033[1;32m>>>\033[0m ')
    # sys.stdout.flush()
    # while True:
    #     try:
    #         model = valid_models[input().strip()]
    #         break
    #     except KeyError:
    #         print("Not Exist")
    #         continue
    # return provider, model


def collect_model(provider, api_key) -> str:
    with open("./providers/provider_list.yml", "r") as file:
        urls = yaml.load(file, Loader=yaml.FullLoader)
    with open("./providers/model_info.yaml", "r") as file:
        docs = yaml.load(file, Loader=yaml.FullLoader)
    client = openai.OpenAI(api_key=api_key, base_url=urls[provider])
    models = []
    for model in client.models.list():
        filter_models = ['code',
                         'math',
                         'ocr',
                         'vl',
                         'diff',
                         'audio',
                         'sovits',
                         'video',
                         'janus',
                         'flux',
                         'qvq',
                         'mochi',
                         '-en']
        model_id = model.id.lower()
        if any(key in model_id for key in filter_models):
            continue
        models.append(model.id)
    if provider == 'ALIYUN':
        models += ['deepseek-r1', 'deepseek-v3', "deepseek-r1-distill-qwen-1.5b", "deepseek-r1-distill-qwen-14b",
                   "deepseek-r1-distill-qwen-32b", "deepseek-r1-distill-llama-70b", "deepseek-r1-distill-llama-8b",
                   "deepseek-r1-distill-qwen-7b"]
    models.sort()
    print(f'Available models in {provider}: \n')
    ommition = 10
    if len(models) >= ommition:
        for i in range(ommition):
            print(f'\t{models[i]}')
        print('\t...\n')
        print(f'Check more models in {docs[provider]}')
    else:
        for model in models:
            print(f'\t{model}')
    sys.stdout.write("\n\033[1;32m>>>\033[0m ")
    sys.stdout.flush()
    while True:
        try:
            input_model = input().strip()
            if input_model in models:
                break
            sys.stdout.write('ERROR: Model not found.'
                             '\n\033[1;32m>>>\033[0m ')
            sys.stdout.flush()
        except KeyboardInterrupt:
            sys.stdout.write("\nERROR: No model selected.\n")
            sys.stdout.flush()
            raise KeyboardInterrupt
    return input_model


def init() -> None:
    config_yaml = Path("./config.yaml")
    print("Let's get started with some basic configuration.")
    time.sleep(0.5)
    try:
        # Collect lang
        source_lang, target_lang = collect_lang()
        sys.stdout.write(
            f'\nTranslate from \033[34m{source_lang}\033[0m to \033[31m{target_lang}\033[0m.'
            f'\nYou can change this option later using \033[33m/lang\033[0m.\n\n'
        )
        time.sleep(0.5)

        # Collect provider, key and base_url
        provider, api_key, base_url = collect_provider_and_api_key()
        sys.stdout.write(
            "\nAuthentication succeed. "
            "\nYou can change the provider later using \033[33m/prov <PROVIDER>\033[0m.\n\n"
        )
        time.sleep(0.5)

        # Collect model
        model = collect_model(provider=provider, api_key=api_key)
        sys.stdout.write(
            f"\nUsing \033[32m{model}\033[0m to translate. "
            f"\nYou can change the model later using \033[33m/model\033[0m.\n\n")
        with open(config_yaml, "w") as outfile:
            yaml.dump(
                {
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "provider": provider,
                    "base_url": base_url,
                    "model": model,
                    "api_key": api_key,
                },
                outfile, Dumper=yaml.SafeDumper
            )
    except KeyboardInterrupt:
        sys.stdout.write("\nYour config will not be saved."
                         "\nExiting...\n")


if __name__ == "__main__":
    init()
