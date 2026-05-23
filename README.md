# Knowledge Cards · AI 知识卡片制作工具

用 AI 批量制作学科知识卡片的完整工具集。核心流程：收集知识点 → 补充内容 → 构造提示词 → 批量生成图片。

面向中国学生考试复习场景（中考、高考、考研等），覆盖任意学科。

## 快速开始

### 安装为 Claude Code Skill

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/knowledge-cards.git
cd knowledge-cards

# 2. 把 skill 链接到 Claude Code（任选一种）

# 方式 A：软链接到全局 skills 目录
ln -s $(pwd)/skills/knowledge-cards ~/.claude/skills/knowledge-cards

# 方式 B：直接复制
cp -r skills/knowledge-cards ~/.claude/skills/knowledge-cards

# 3. 验证安装
# 在 Claude Code 中说"帮我做一套XX知识卡片"，skill 会自动激活
```

### 不用 Claude Code 也能用

直接把 `skills/knowledge-cards/SKILL.md` 当作教程阅读，按步骤手动完成每一步。脚本可以独立运行。

## 四种批量生成模式

| 模式 | 自动化 | 自动下载图片 | 需要什么 |
|------|--------|-------------|---------|
| **剪贴板** | 半自动 | 手动保存 | 无额外依赖 |
| **桌面端** | 全自动 | 手动保存 | macOS 无需 / Win+Linux 需 pyautogui |
| **API** | 全自动 | 自动下载 | `pip install openai` + API Key |
| **网页** | 全自动 | 自动下载 | `pip install playwright` + ChatGPT Plus |

### 推荐：先用剪贴板试 3-5 张，确认风格后再切全自动。

## 脚本使用

所有脚本在 `skills/knowledge-cards/scripts/` 目录下。

```bash
# 1. 从 Markdown 提取 JSON
python3 scripts/extract_prompts.py examples/示例_心理学知识卡片提示词集.md

# 2. 选一种模式批量生成

# 剪贴板模式（零依赖，推荐先试）
python3 scripts/batch_send_clipboard.py 1 3

# 桌面端全自动（macOS 零依赖 / Win 需 pyautogui）
python3 scripts/batch_send_auto.py --wait 90

# API 模式（最可靠，自动下载图片）
export OPENAI_API_KEY="sk-..."
python3 scripts/batch_send_api.py --output ./output

# 网页模式（Playwright，自动下载图片）
python3 scripts/batch_send_web.py --output ./output --wait 120
```

## 目录结构

```
knowledge-cards/
├── .claude-plugin/
│   └── plugin.json              # Claude Code 插件元数据
├── skills/
│   └── knowledge-cards/
│       ├── SKILL.md             # 完整方法论教程（9 步流水线）
│       └── scripts/
│           ├── extract_prompts.py       # MD → JSON 解析
│           ├── batch_send_clipboard.py  # 剪贴板模式（跨平台）
│           ├── batch_send_auto.py       # 桌面端全自动（跨平台）
│           ├── batch_send_web.py        # Playwright 网页模式
│           └── batch_send_api.py        # OpenAI API 模式
├── examples/
│   └── 示例_心理学知识卡片提示词集.md  # 示例提示词集
├── README.md
├── requirements.txt
└── LICENSE
```

## 平台支持

| 功能 | macOS | Windows | Linux |
|------|-------|---------|-------|
| 剪贴板模式 | pbcopy（自带） | PowerShell（自带） | xclip |
| 桌面端全自动 | AppleScript（自带） | pyautogui | pyautogui |
| API 模式 | ✓ | ✓ | ✓ |
| 网页模式 | ✓ | ✓ | ✓ |

## 方法论概述

核心原则：**你当主编，AI 当排版员和画师。**

```
收集需求 → 选风格 → 提取知识点 → 核验准确性 → 匹配模板 → 生成提示词 → 质量检查 → 输出 Markdown → 批量生成
```

完整教程见 `skills/knowledge-cards/SKILL.md`，包含：
- 6 种画面风格 + 4 种比例 + 6 种配色方案
- 4 种内容模板（理科/文科/语言/过程）
- 8 种版式自动匹配
- 6 个提示词写法核心技巧
- 真实案例对比（心理学 vs 中考数学）

## 依赖安装

按需安装，不需要全部装：

```bash
# API 模式
pip3 install openai

# 网页模式
pip3 install playwright && python3 -m playwright install chromium

# 桌面端模式（仅 Windows/Linux）
pip3 install pyautogui
```

## License

MIT
