from get_api import load_api_keys
from get_providers import Models
import json
import openai
import sys
import yaml

api_keys = load_api_keys(dir='api_keys')

if __name__ == "__main__1":
    default_message = ">>> \033[90mSend a message: \033[0m"
    sys.stdout.write(default_message)
    sys.stdout.flush()
    while (message := input().lower()) != "/bye":
        # talk(message)
        sys.stdout.write(default_message)


def test(content, role=None):
    # with open("/home/thf/Programme/.dskey1") as keyfile:
    # with open('/home/thf/Programme/.sfkey1') as keyfile:
    with open("/home/thf/Programme/.alikey1") as keyfile:
        key = keyfile.readline().split("\n")[0]
    # client = openai.OpenAI(api_key=key, base_url="https://api.deepseek.com/v1")
    # client = openai.OpenAI(api_key=key,base_url="https://api.siliconflow.cn/v1")
    client = openai.OpenAI(api_key=key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    system_message = None
    if role == "translate":
        prompt_file = "prompt/Translator.json"
        with open(prompt_file) as json_file:
            system_message = json.load(json_file)
            system_message["content"] = (
                system_message["content"]
                .replace("A语言", "中文")
                .replace("B语言", "英文")
            )
    messages = [{"role": "user", "content": content}]
    if system_message:
        messages = [system_message, {"role": "user", "content": content}]
    response = client.chat.completions.create(
        # model="deepseek-reasoner",
        # model='deepseek-ai/DeepSeek-R1',
        model=Models.ALIYUN.deepseek_r1,
        stream=True,
        messages=messages,
    )
    # reasoning_content = []
    # for chunk in response:
    #     if chunk.choices[0].delta.reasoning_content is not None:
    #         content = chunk.choices[0].delta.reasoning_content
    #         reasoning_content.append(content)
    #         sys.stdout.write(content)
    #         sys.stdout.flush()
    reasoning_response = []
    full_response = []
    with open("output.md", "a") as output:
        output.write(f"\n\n---\n\n> Input: \n\n{content}\n\n> Output:\n\n")
    for chunk in response:
        try:
            if chunk.choices[0].delta.reasoning_content is not None:
                reasoning_content = chunk.choices[0].delta.reasoning_content
                reasoning_response.append(reasoning_content)
                sys.stdout.write('\033[90m' + reasoning_content + '\033[0m')
                # sys.stdout.write('\n\033[90m<Thinking...>\033[0m')
                sys.stdout.flush()
        except AttributeError:
            pass
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response.append(content)
            with open("output.md", "a") as output:
                output.write(content)
    if not full_response:
        with open("output.md", "a") as output:
            output.write("服务器繁忙，请稍后再试。")


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
                # sys.stdout.write('\033[90m' + reasoning_content + '\033[0m')
                # sys.stdout.flush()
            # if chunk.choices[0].delta.reasoning_content != '' and len(''.join(reasoning_response)) > reason_text_length:
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


if __name__ == "__main__":
    with open("inputs/input3.md") as inputfile:
        message = list(inputfile.readlines())
    test(''.join(message))
    # translate('Hello, World!')
