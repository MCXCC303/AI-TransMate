<h1 align="center">AI TransMate</h1>
<p align="center">
  <b>终端 LLM 翻译工具 — 自动源语言检测、语境分析、流式渲染</b>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python 3.9+-%231f4361?logo=python&logoColor=%23ffe264&labelColor=%233570a0">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/LICENSE-MIT-black">
  </a>
</p>

---

## 特点

- **自动源语言检测**：无需手动指定，小模型自动识别输入语言并写入主模型提示词
- **翻译语境分析**：自动识别文本领域（技术/医学/法律/文学/日常等），提供语境化翻译
- **多厂商支持**：DeepSeek、阿里云百炼、硅基流动、OpenAI、腾讯云、火山引擎
- **提示词缓存优化**：固定角色+目标语言在前，动态检测结果在后，最大化 API 缓存命中率
- **终端状态栏**：实时显示会话 ID、目标语言、源语言（自动检测/手动指定）、语境、当前模型
- **流式 Markdown/LaTeX 渲染**：在终端实时渲染 Markdown 格式和 LaTeX 数学公式
- **Vim 模式**：支持 vim 风格键盘操作（hjkl 导航、Esc 切换模式）
- **历史查看器**：`/history` 命令浏览和回看历史翻译记录

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

首次运行会引导完成配置（API 提供商、密钥、目标语言）。配置保存在 `~/.config/transmate/config.json`。

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

### 配置文件

```json
{
  "api_key": "...",
  "base_url": "https://api.deepseek.com/v1",
  "provider": "DEEPSEEK",
  "main_model": "deepseek-chat",
  "fast_model": "deepseek-chat",
  "target_lang": "Chinese",
  "source_lang_specified": false,
  "source_lang": null,
  "vi_mode": true,
  "context_optimization": true
}
```

### 提示词架构

发送给主模型的 messages 按缓存优化顺序排列：

1. **System Message 1**（静态）：翻译角色定义 + 目标语言 → 固定前缀，高缓存命中
2. **System Message 2**（半静态）：小模型返回的语境/风格标签
3. **System Message 3**（动态）：小模型返回的源语言
4. **User Message**：用户输入文本

## 依赖

- `openai` — 多厂商 API 兼容调用
- `prompt-toolkit` — 终端输入（vi 模式、状态栏、历史查看器）
- `rich` — Markdown/LaTeX 实时渲染
- `pyyaml` — 旧配置迁移（仅首次）
- `pylatexenc` — LaTeX 公式转终端文本
