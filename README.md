<h1 align="center">AI TransMate</h1>
<p align="center">
  <b>终端 LLM 翻译工具 — 自动源语言检测、语境分析</b>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python 3.9+-%231f4361?logo=python&logoColor=%23ffe264&labelColor=%233570a0">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/LICENSE-MIT-black">
  </a>
</p>

---

## 安装

```shell
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 使用

```shell
python main.py
```

首次运行会引导完成配置（API 提供商、密钥、目标语言）。

### 命令

| 命令 | 说明 |
|------|------|
| `/lang` | 设置目标语言 |
| `/source` | 设置源语言（可选 `auto` 自动检测） |
| `/model` | 切换主翻译模型 |
| `/fast` | 切换快速模型（用于语言/语境检测） |
| `/prov` | 切换 API 提供商 |
| `/show` | 显示当前配置 |
| `/switch` | 交换源/目标语言 |
| `/history` | 查看翻译历史 |
| `/history clear` | 清空历史 |
| `/bye` | 退出 |
| `/?` | 帮助 |

多行输入：使用 `"""` 开始和结束多行消息。
