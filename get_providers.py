import os
import json


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        providers_dir = os.path.join(os.path.dirname(__file__), "providers")

        for filename in os.listdir(providers_dir):
            if filename.endswith(".json"):
                provider_name = os.path.splitext(filename)[0].upper()

                with open(os.path.join(providers_dir, filename), "r") as f:
                    provider_data = json.load(f)

                model_attrs = {k: v for k, v in provider_data.items() if v is not None}
                provider_class = type(
                    f"{provider_name}Models",
                    (),
                    {"__slots__": ()} | model_attrs,  # Python 3.9+
                )

                # 将供应商类添加为外层类的属性
                attrs[provider_name] = provider_class()

        return super().__new__(cls, name, bases, attrs)


class Models(metaclass=ModelMeta):
    __slots__ = ()


if __name__ == "__main__":
    print(Models.DEEPSEEK.deepseek_v3)
    print(Models.DEEPSEEK.deepseek_r1)
    print(Models.SILICONFLOW.deepseek_v3)
    print(Models.ALIYUN.deepseek_r1)
