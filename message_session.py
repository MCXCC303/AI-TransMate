import json
import openai
import sys
import yaml


def translate(text):
    with open('config.yaml', 'r', encoding='utf-8') as conf:
        config = yaml.load(conf, Loader=yaml.FullLoader)
    client = openai.OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    prompt_file = "prompt/Translator.json"
    with open('./prompt/en_US.json') as json_file:
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
        model=config['model'],
        stream=True,
        messages=messages
    )
    reasoning_response = []
    full_response = []
    with open("output.md", "a") as output:
        output.write(f"\n\n---\n\n> Input: \n\n{text}\n\n> Output:\n\n")
    sys.stdout.write('\n')
    for chunk in response:
        reason_text_length = len(''.join(reasoning_response))
        try:
            if config['provider'] == 'SILICONFLOW' and 'r1' not in config['model'].lower():
                raise AttributeError
            if chunk.choices[0].delta.reasoning_content is not None:
                reasoning_content = chunk.choices[0].delta.reasoning_content
                reasoning_response.append(reasoning_content)
            if len(''.join(reasoning_response)) > reason_text_length:
                sys.stdout.write(f"\033[1A\033[2K\033[90mThinking{'.' * (len(reasoning_response) % 6 + 1)}\033[0m\n")
                sys.stdout.flush()
        except AttributeError:
            pass
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response.append(content)
            sys.stdout.write(content)
            sys.stdout.flush()
            with open("output.md", "a") as output:
                output.write(content)
    print()
    if not full_response:
        sys.stdout.write("\033[90;3mService busy. Try again later or change a provider.\033[0m\n")
        with open("output.md", "a") as output:
            output.write("Service busy. Try again later.")
