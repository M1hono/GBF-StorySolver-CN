# GBF 剧情提取器

[English](README_EN.md)

一个用于提取、翻译和发布碧蓝幻想剧情内容的完整工具集。支持从 GBF Wiki 提取内容、使用 Claude/彩云 AI 翻译，以及发布到 Notion。

## 目录

- [前置要求](#前置要求)
- [安装](#安装)
- [配置详解](#配置详解)
- [快速开始](#快速开始)
- [详细使用](#详细使用)
  - [内容提取](#内容提取)
  - [翻译](#翻译)
  - [Notion 发布](#notion-发布)
- [项目结构](#项目结构)
- [本地数据说明](#本地数据说明)
- [AI 辅助使用](#ai-辅助使用)
- [故障排除](#故障排除)

---

## 前置要求

- Python 3.9 或更高版本
- Chromium 浏览器（通过 Playwright 安装）
- 相应服务的 API 密钥

## 安装

### 第一步：克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/gbf-story-extractor.git
cd gbf-story-extractor
```

### 第二步：安装 Python 依赖

```bash
pip install -r lib/requirements.txt
```

### 第三步：安装 Playwright 浏览器

```bash
playwright install chromium
```

### 第四步：初始化 BLHXFY 翻译数据

下载社区翻译资源用于角色名映射：

```bash
python -m lib.update_blhxfy
```

此命令会下载：
- BLHXFY 官方翻译数据（角色名、术语映射）
- AI-Translation 社区翻译的剧情文件

---

## 配置详解

本项目使用两个配置文件，理解它们的作用非常重要：

### 配置文件概览

| 文件 | 必需 | 用途 | 内容类型 |
|------|------|------|----------|
| `.env` | ✅ | API 凭证 | 敏感信息（密钥、ID） |
| `config.yaml` | ❌ | 行为设置 | 模型、超时等可调参数 |
| `characters.json` | ❌ | 批量上传 | 角色文件夹和显示名映射 |

### .env 文件（必需）

存放所有 API 密钥和敏感配置。**不要提交到 Git！**

```bash
# 复制模板
cp .env.example .env
```

完整配置示例：

```ini
# ============ 翻译服务 ============
# Claude API（推荐，翻译质量最好）
CLAUDE_API_KEY=sk-ant-api03-xxxxx

# 彩云翻译 API（可选，备用）
CAIYUN_API_KEY=xxxxx

# ============ Notion 发布 ============
# Notion 集成密钥
NOTION_API_KEY=ntn_xxxxx

# Notion 根页面 ID（32位，从 URL 获取）
NOTION_ROOT_PAGE_ID=2c77c15a92478012aa9ee809fec41257
```

### 如何获取各 API 密钥

#### Claude API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 进入 Settings → API Keys
4. 点击 "Create Key" 创建新密钥
5. 复制密钥（格式：`sk-ant-api03-xxx`）

#### 彩云翻译 API Key

1. 访问 https://dashboard.caiyunapp.com/
2. 注册账号并登录
3. 进入 Token 管理页面
4. 复制你的 Token

#### Notion API Key

1. 访问 https://www.notion.so/my-integrations
2. 点击 "New integration" 创建新集成
3. 填写名称，选择工作区
4. 创建后复制 "Internal Integration Token"
5. **重要**：需要在 Notion 页面中共享给此集成

#### Notion Root Page ID

这是你希望所有内容上传到的目标页面 ID：

1. 在 Notion 中打开目标页面
2. 查看浏览器 URL，格式为：
   ```
   https://www.notion.so/workspace/Page-Title-2c77c15a92478012aa9ee809fec41257
   ```
3. 复制最后的 32 位字符（连字符后的部分）
4. 填入 `.env` 的 `NOTION_ROOT_PAGE_ID`

**注意**：必须将页面共享给你的 Notion 集成！
- 打开页面 → 右上角 "Share" → "Invite" → 选择你的集成

### config.yaml 文件（可选）

用于自定义工具行为，不存在时使用默认值：

```bash
cp config.example.yaml config.yaml
```

完整配置项：

```yaml
# 翻译设置
translation:
  # 翻译模式：prompt（使用提示词，准确）或 replace（直接替换，快速）
  mode: prompt
  
  # 每次翻译的行数
  # 较大的值（如 500）可减少 API 调用次数，降低成本
  # 较小的值（如 120）对长文件更稳定
  chunk_size: 500
  
  # 每次请求最大 token 数
  max_tokens: 8192
  
  # Claude 模型选择（根据需求和预算选择）
  # claude-sonnet-4-20250514: 推荐，质量好性价比高
  # claude-3-5-sonnet-20241022: 备选，价格相同
  # claude-3-opus-20240229: 最高质量，成本高5倍
  # claude-3-haiku-20240307: 最便宜，成本仅1/12，质量略低
  claude_model: claude-sonnet-4-20250514
```

### 翻译成本估算

基于实际测试（chunk_size=500，已优化）：

**Claude模型价格对比**（来源：[Anthropic官网](https://www.anthropic.com/pricing)）：

| 模型 | 输入价格 | 输出价格 | 单活动成本 | 100章成本 |
|------|---------|---------|-----------|----------|
| **Sonnet 4** (推荐) | $3/MTok | $15/MTok | **$1.07** | **$13.35** |
| Sonnet 3.5 | $3/MTok | $15/MTok | $1.07 | $13.35 |
| Opus (最高质量) | $15/MTok | $75/MTok | $5.34 | $66.74 |
| **Haiku** (经济) | $0.25/MTok | $1.25/MTok | **$0.09** | **$1.11** |

**说明**：
- 单活动 ≈ 8个章节（已自动合并）
- 100章 ≈ 12-13个活动
- 成本已包含所有优化（合并章节、精炼prompt等）

**推荐配置**：
- **预算充足**：Sonnet 4（质量好，性价比高）
- **预算紧张**：Haiku（成本仅1/12，质量可接受）
- **追求完美**：Opus（质量最高，但成本高5倍）

**翻译质量对比**（同一段落）：

| 模型 | 翻译示例 | 评价 |
|------|---------|------|
| **Sonnet 4** | "我把泽里昂的头目带来了，**如您所愿**" | 更自然、更口语化 ✅ |
| Haiku | "我**按您的要求**把泽里昂的头头带来了" | 略显生硬，但可读 |
| | "咱们可是**老交情**了，对吧？" | 地道的中文表达 ✅ |
| | "咱们可是**有这么深的交情**啊？" | 稍显翻译腔 |

**结论**：
- Sonnet 4 vs Haiku：质量差距约10-15%
- Haiku适合：预览、初稿、对话简单的内容
- Sonnet 4适合：正式发布、对话复杂的剧情

# 提取设置
extraction:
  # 是否无头模式（false 可看到浏览器窗口，便于调试）
  headless: true
  
  # 页面加载超时（毫秒）
  timeout: 30000
  
  # 重试次数
  retries: 3

# Notion 设置
notion:
  # 是否强制重建所有页面
  force_mode: false
  
  # 请求间隔（秒，避免限流）
  rate_limit: 0.1
```

### characters.json 文件

批量上传时使用，定义要上传的角色列表：

```json
[
  {"folder": "vajra", "name": "瓦姬拉"},
  {"folder": "nier", "name": "妮娅"},
  {"folder": "galleon", "name": "伽莱翁"},
  {"folder": "vikala", "name": "毗伽罗"}
]
```

字段说明：
- `folder`：`characters/` 目录下的文件夹名（英文，小写）
- `name`：在 Notion 中显示的名称（中文）

---

## 快速开始

### 完整工作流示例

以瓦姬拉的活动剧情为例：

```bash
# 1. 提取剧情内容
python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra

# 2. 提取角色头像
python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra

# 3. 翻译为中文
python -m lib.translate claude \
  characters/vajra/story/auld_lang_fry_premium/raw \
  characters/vajra/story/auld_lang_fry_premium/trans

# 4. 上传到 Notion
python3 notion_upload.py vajra 瓦姬拉 --event auld_lang_fry_premium
```

### 提取语音和档案

```bash
# 提取语音台词
python -m lib.extract voice Vajra characters/vajra

# 提取角色档案（简介、命运插曲等）
python -m lib.extract lore Vajra characters/vajra

# 翻译语音
python -m lib.translate claude \
  characters/vajra/voice/raw \
  characters/vajra/voice/trans

# 翻译档案
python -m lib.translate claude \
  characters/vajra/lore/raw \
  characters/vajra/lore/trans
```

---

## 详细使用

### 内容提取

提取工具从 GBF Wiki 页面获取内容，使用 Playwright 进行浏览器自动化。

#### 剧情提取 (story)

从活动剧情页面提取章节对话。**新版本会自动合并同一章节的所有 episode**，大幅减少文件数量和翻译成本。

```bash
python -m lib.extract story {活动代号} {输出目录}
```

**参数说明**：
- `活动代号`：Wiki URL 中的活动标识符
  - 来源：`https://gbf.wiki/{活动代号}/Story`
  - 例如：`Auld_Lang_Fry_PREMIUM`、`A_Ballad_of_Unbending_Chivalry`
- `输出目录`：角色目录路径
  - 推荐：`characters/{角色名}`

**输出结构（自动合并）**：
```
characters/yuisis/story/a_ballad_of_unbending_chivalry/
└── raw/
    ├── 01_opening.md                        # 单独文件
    ├── 02_chapter_1_family_reunion.md       # 合并了 4 个 episodes
    ├── 03_chapter_2_means_and_ends.md       # 合并了 4 个 episodes
    └── 08_ending.md                         # 合并了 2 个 episodes
```

**合并效果**：
- 原始：28 个小文件 → 翻译需要 28 次 API 调用
- 合并：8 个文件 → 翻译需要约 8-12 次 API 调用
- **节省成本：约 60-70%**

**示例**：
```bash
# 提取十二神将活动剧情（自动合并）
python -m lib.extract story ZodiaCamp:_The_2nd_Divine_Generals_Assembly characters/vajra

# 提取新年活动
python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra
```

#### 角色列表提取 (cast)

从剧情页面提取登场角色头像和名称，用于在 Notion 中展示。

```bash
python -m lib.extract cast {活动代号} {输出目录}
```

**输出**：`{输出目录}/story/{event}/trans/cast.md`

**cast.md 格式**：
```markdown
# Event Name - Cast Portraits

数据源：`https://gbf.wiki/Event_Name/Story`

| 角色（英 / 中） | 头像 |
| --- | --- |
| [Vajra / 瓦姬拉](https://gbf.wiki/Vajra) | ![Vajra](https://gbf.wiki/images/...) |
```

#### 语音提取 (voice)

从角色页面提取所有语音台词。

```bash
python -m lib.extract voice {角色名} {输出目录}
```

**参数说明**：
- `角色名`：Wiki 上的角色页面名称（首字母大写）
  - 例如：`Vajra`、`Nier`、`Vikala`

**输出结构**：
```
characters/vajra/voice/
└── raw/
    ├── general.md           # 通用台词
    ├── battle/              # 战斗语音
    │   ├── attack.md
    │   └── skills.md
    ├── holidays/            # 节日语音
    │   ├── happy_birthday.md
    │   └── happy_new_year.md
    ├── outfits/             # 皮肤语音
    │   └── soul_channeler.md
    └── character_banter/    # 角色互动
        └── kumbhira.md
```

#### 档案提取 (lore)

提取角色简介、命运插曲和特殊剧情。

```bash
python -m lib.extract lore {角色名} {输出目录}
```

**输出结构**：
```
characters/vajra/lore/
└── raw/
    ├── profile.md              # 角色简介
    ├── fate_episodes/          # 命运插曲
    │   ├── episode_1.md
    │   └── episode_2.md
    └── special_cutscenes/      # 特殊剧情
        └── cross_fate.md
```

#### 本地剧情提取 (scenario)

从已下载的 BLHXFY CSV 文件提取剧情（无需联网）。

```bash
# 列出所有可用剧情
python -m lib.extract scenario --list

# 提取指定剧情
python -m lib.extract scenario "12.17" story/translated/12.17

# 从自定义路径提取
python -m lib.extract scenario /path/to/csv/folder story/translated/custom
```

**剧情来源**：
- 自动从 `lib/local_data/blhxfy/scenario/` 读取
- 运行 `python -m lib.update_blhxfy` 可更新

#### 查找角色本地剧情

智能查找角色在本地翻译数据中的登场活动，支持中文/英文/日文名搜索。

```bash
# 按中文名查找
python -m lib.tools.find_character_stories "缇可"

# 按英文名查找（自动转换为中文）
python -m lib.tools.find_character_stories "Tikoh"

# 显示详细文件列表
python -m lib.tools.find_character_stories "缇可" -v

# 查找并提取到角色目录
python -m lib.tools.find_character_stories "缇可" --extract characters/tikoh
```

**输出示例**：
```
Found 2 activities containing '缇可':
============================================================

📁 活动剧情/金月2
   (43 files)

📁 活动剧情/金月3
   (23 files)
```

**参数说明**：
| 参数 | 说明 |
|------|------|
| `name` | 角色名（中/英/日） |
| `-v, --verbose` | 显示匹配的文件列表 |
| `--extract DIR` | 提取到指定目录 |
| `--no-story-translated` | 不同时复制到 `story/translated/` |

#### 合并章节文件（降低成本）

将每个chapter的多个episode合并成一个文件，减少API调用次数。

```bash
# 合并单个活动的章节
python -m lib.tools.merge_chapters characters/tikoh/story/marionette_stars/raw

# 预览模式（不实际执行）
python -m lib.tools.merge_chapters characters/tikoh/story/marionette_stars/raw --dry-run

# 批量合并多个活动
python -m lib.tools.merge_chapters characters/tikoh/story/*/raw --all
```

**效果**：
- 30个小文件 → 11个合并文件（减少63%）
- API调用次数减少约50%
- 输出到 `raw_merged/` 目录

### 翻译

本项目支持多种翻译引擎，可根据需求和预算选择。

#### 翻译引擎对比

| 引擎 | Input 价格 | Output 价格 | 130K 成本 | 质量 | 术语表 | 推荐 |
|------|-----------|-------------|----------|------|--------|------|
| **Gemini 2.0 Flash** | $0.075/1M | $0.30/1M | **$0.05** | ✅ 好 | ✅ Prompt | 🥇 日常 |
| **OpenAI GPT-4o-mini** | $0.15/1M | $0.60/1M | $0.10 | ✅ 好 | ✅ Prompt | 🥈 平衡 |
| **Claude Sonnet 4** | $3/1M | $15/1M | $2.34 | ⭐ 最佳 | ✅ Prompt | 精翻 |
| Claude Haiku 3.5 | $1/1M | $5/1M | $0.78 | ✅ 好 | ✅ Prompt | 性价比 |
| DeepL Free | 免费 | 免费 | $0 | 一般 | ✅ Native | ⚠️ 格式差 |
| 彩云 | ¥40/1M | ¥40/1M | ¥0.05 | 一般 | ❌ 无 | 预览 |

**推荐顺序**: Gemini > OpenAI > Haiku > Sonnet

> 💡 详细价格对比见 [lib/docs/TRANSLATION_API_COMPARISON.md](lib/docs/TRANSLATION_API_COMPARISON.md)

#### 使用方法

```bash
# 成本估算（翻译前先看看要花多少钱）
python -m lib.translate cost {输入目录}

# Gemini（推荐，最便宜）
python -m lib.translate gemini {输入目录} {输出目录}

# OpenAI GPT-4o-mini
python -m lib.translate openai {输入目录} {输出目录}

# Claude（质量最好，但贵）
python -m lib.translate claude {输入目录} {输出目录}

# 彩云（快速预览）
python -m lib.translate caiyun {输入目录} {输出目录}
```

**示例**：
```bash
# 先估算成本
python -m lib.translate cost characters/vajra/story/zodiacamp/raw

# 用 Gemini 翻译（便宜）
python -m lib.translate gemini \
  characters/vajra/story/zodiacamp/raw \
  characters/vajra/story/zodiacamp/trans

# 重要内容用 Claude 精翻
python -m lib.translate claude \
  characters/vajra/lore/raw \
  characters/vajra/lore/trans
```

**翻译特点**：
- 自动加载 BLHXFY 术语表
- 角色名优先使用本地映射
- 保持 Markdown 格式

#### 配置翻译引擎

在 `config.yaml` 中设置模型：

```yaml
translation:
  # Claude 模型
  claude_model: claude-sonnet-4-20250514
  
  # OpenAI 模型
  openai_model: gpt-4o-mini
  
  # Gemini 模型
  gemini_model: gemini-2.0-flash
```

在 `.env` 中配置 API 密钥：

```bash
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
```

#### 🔥 批量翻译（50% 折扣）

所有主流 API 都支持批量模式，可节省 50% 成本（24小时内返回）：

```bash
# 提交批量任务
python -m lib.translators.batch_translator submit ./raw --engine openai

# 查看状态
python -m lib.translators.batch_translator status <batch_id>

# 下载结果
python -m lib.translators.batch_translator download <batch_id> ./trans
```

| 模式 | 130K 成本 | 返回时间 |
|------|----------|---------|
| Gemini 标准 | $0.05 | 即时 |
| **Gemini 批量** | **$0.025** | 24h |
| Claude 标准 | $2.34 | 即时 |
| **Claude 批量** | **$1.17** | 24h |

#### 查询角色名

检查角色名是否有中文翻译：

```bash
python -m lib.translate lookup "Vajra"
# 输出：Vajra -> 瓦姬拉

python -m lib.translate lookup "Captain"
# 输出：Captain -> 团长
```

#### 修复未翻译名称

翻译后，部分名称可能仍为英文/日文。修复方法：

```bash
# 扫描目录中的未翻译名称
python -m lib.translators.name_fixer scan characters/vajra/story/zodiacamp/trans

# 应用修复（会修改文件）
python -m lib.translators.name_fixer fix characters/vajra/story/zodiacamp/trans
```

如果发现未收录的名称，可以手动添加到 `lib/local_data/blhxfy/etc/added_en_mapping.csv`：

```csv
EnglishName,中文名,,manual
NewCharacter,新角色,,manual
```

### Notion 发布

#### 基本用法

```bash
# 上传单个角色（全部内容）
python3 notion_upload.py {文件夹名} {显示名}

# 示例
python3 notion_upload.py vajra 瓦姬拉
```

#### 完整参数说明

```bash
python3 notion_upload.py [character] [display_name] [OPTIONS]
```

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `character` | 位置参数 | 角色文件夹名 | `vajra` |
| `display_name` | 位置参数 | Notion 显示名称 | `瓦姬拉` |
| `--mode` | 选项 | 上传模式 | `--mode story` |
| `--sync-mode` | 选项 | 同步模式 | `--sync-mode force` |
| `--event` | 选项 | 仅上传指定活动 | `--event zodiacamp` |
| `--name` | 选项 | 筛选根剧情名称 | `--name "12.17"` |
| `--all` | 标志 | 上传所有角色 | `--all` |
| `--clean` | 标志 | 先删除再上传 | `--clean` |
| `--dry-run` | 标志 | 预览不实际上传 | `--dry-run` |
| `--voice-only` | 标志 | 仅上传语音 | `--voice-only` |
| `--lore-only` | 标志 | 仅上传档案 | `--lore-only` |

#### --mode 参数详解

| 值 | 说明 | 上传内容 |
|-----|------|----------|
| `story` | 仅根目录剧情 | `story/translated/` |
| `character` | 仅角色内容 | `characters/{char}/` |
| `both` | 两者都上传（默认） | 全部 |

#### --sync-mode 参数详解

| 值 | 说明 | 适用场景 |
|-----|------|----------|
| `diff` | 增量更新（默认） | 日常更新，只同步变化的内容 |
| `force` | 强制重建 | 修复问题，重新生成所有页面 |

#### 常用命令示例

```bash
# ===== 单角色操作 =====

# 上传角色全部内容
python3 notion_upload.py vajra 瓦姬拉

# 仅上传某个活动剧情（最快）
python3 notion_upload.py vajra 瓦姬拉 --event zodiacamp

# 仅上传语音
python3 notion_upload.py vajra 瓦姬拉 --voice-only

# 仅上传档案
python3 notion_upload.py vajra 瓦姬拉 --lore-only

# 强制重建角色的语音数据库
python3 notion_upload.py vajra 瓦姬拉 --voice-only --sync-mode force

# ===== 根目录剧情 =====

# 上传所有根目录剧情
python3 notion_upload.py --mode story

# 上传指定剧情
python3 notion_upload.py --mode story --name "12.17"

# ===== 批量操作 =====

# 上传所有角色（需要 characters.json）
python3 notion_upload.py --all

# 清空并重新上传所有
python3 notion_upload.py --all --clean

# 强制重建所有页面
python3 notion_upload.py --all --sync-mode force

# 预览模式（不实际上传）
python3 notion_upload.py --all --dry-run
```

#### Notion 页面结构

上传完成后，Notion 中的结构如下：

```
GBF/
├── Story/                      # 根目录剧情（story/translated/）
│   ├── 12.17/
│   │   ├── 00_opening
│   │   └── ...
│   └── 202302 ……and you/
│       └── ...
└── Character/
    ├── 瓦姬拉/
    │   ├── Story/              # 角色活动剧情
    │   │   ├── auld_lang_fry_premium/
    │   │   │   ├── 00_opening
    │   │   │   ├── Cast Portraits  (数据库)
    │   │   │   └── ...
    │   │   └── zodiacamp/
    │   ├── Lore/               # 档案内容
    │   │   ├── profile
    │   │   └── fate_episodes/
    │   └── Voice/              # 语音台词（数据库形式）
    │       ├── general/
    │       │   └── General - Voice Lines (数据库)
    │       ├── holidays/
    │       │   ├── Happy Birthday - Voice Lines
    │       │   └── ...
    │       └── outfits/
    │           └── Soul Channeler - Voice Lines
    └── 妮娅/
        └── ...
```

---

## 项目结构

```
gbf/
├── lib/                          # 核心库
│   ├── extractors/               # 网页提取模块
│   │   ├── story.py              # 剧情章节提取
│   │   ├── cast.py               # 角色头像提取
│   │   ├── voice.py              # 语音台词提取
│   │   ├── lore.py               # 档案内容提取
│   │   └── scenario.py           # 本地 CSV 提取
│   ├── translators/              # 翻译模块
│   │   ├── blhxfy.py             # BLHXFY 术语/名称映射
│   │   ├── claude.py             # Claude AI 翻译
│   │   ├── caiyun.py             # 彩云翻译
│   │   └── name_fixer.py         # 翻译后名称修复
│   ├── notion/                   # Notion 同步模块
│   │   ├── sync.py               # 同步上下文、页面/数据库操作
│   │   ├── render.py             # 剧情渲染为 Notion 块
│   │   ├── parsers.py            # Cast/Voice 表格解析
│   │   ├── database.py           # 数据库同步（Cast/Voice）
│   │   └── content.py            # 统一导出（向后兼容）
│   ├── utils/                    # 工具模块
│   │   └── config.py             # 配置加载
│   ├── docs/                     # 开发文档
│   │   ├── API_REFERENCE.md
│   │   ├── EXTRACTION_WORKFLOW.md
│   │   ├── NOTION_UPLOAD_NOTES.md
│   │   └── LOCAL_DATA.md
│   ├── local_data/               # 本地翻译数据（重要！）
│   │   └── blhxfy/
│   │       ├── scenario/         # 社区翻译的剧情 CSV
│   │       └── etc/              # 术语/名称映射表
│   ├── extract.py                # 提取 CLI 入口
│   ├── translate.py              # 翻译 CLI 入口
│   └── update_blhxfy.py          # 更新本地数据
│
├── story/                        # 根目录剧情内容
│   └── translated/               # 从 BLHXFY 提取的剧情
│       ├── 12.17/
│       └── 202302 ……and you/
│
├── characters/                   # 角色内容（按角色组织）
│   ├── vajra/
│   │   ├── story/                # 活动剧情
│   │   │   └── auld_lang_fry_premium/
│   │   │       ├── raw/          # 英文原文
│   │   │       └── trans/        # 中文翻译 + cast.md
│   │   ├── voice/                # 语音台词
│   │   │   ├── raw/
│   │   │   └── trans/
│   │   └── lore/                 # 角色档案
│   │       ├── raw/
│   │       └── trans/
│   └── nier/
│       └── ...
│
├── .cache/                       # 缓存目录
│   └── notion/                   # Notion 同步缓存（每角色一个 JSON）
│       ├── vajra.json
│       └── all.json
│
├── notion_upload.py              # Notion 上传主脚本
├── characters.json               # 批量上传角色配置
├── .env                          # API 密钥（不提交 Git）
├── .env.example                  # 环境变量模板
├── config.yaml                   # 行为配置（可选）
└── config.example.yaml           # 配置模板
```

---

## 本地数据说明

### 数据优先级

本项目采用**本地优先**策略，数据查找顺序：

1. **本地翻译数据** (`lib/local_data/blhxfy/`) - 最高优先级
2. **GBF Wiki** - 本地没有时才访问
3. **机器翻译** - 最后手段

### 本地数据内容

```
lib/local_data/blhxfy/
├── scenario/                   # 社区翻译的剧情（CSV 格式）
│   ├── main/                   # 主线剧情
│   ├── event/                  # 活动剧情
│   └── fate/                   # 命运插曲
└── etc/                        # 术语和名称映射
    ├── npc-name-en.csv         # 英文→中文 角色名映射
    ├── npc-name-jp.csv         # 日文→中文 角色名映射
    ├── noun.csv                # 术语表（翻译前替换）
    ├── noun-fix.csv            # 术语修复（翻译后替换）
    └── added_en_mapping.csv    # 手动添加的映射
```

### 更新本地数据

```bash
# 普通更新（增量）
python -m lib.update_blhxfy

# 强制重新下载
python -m lib.update_blhxfy --force
```

### 添加自定义映射

如果发现角色名未被翻译，编辑 `lib/local_data/blhxfy/etc/added_en_mapping.csv`：

```csv
EnglishName,中文名,,manual
NewCharacter,新角色,,manual
AnotherName,另一个名字,,manual
```

---

## AI 辅助使用

本项目设计为与 AI 编程助手（如 Cursor）良好配合。

### 有 Playwright MCP 时

如果 AI 助手启用了 Playwright MCP，它可以：

- 自动导航到 wiki 页面验证内容
- 通过检查页面结构调试提取问题
- 从 wiki 导航中发现活动 URL

示例提示：

```
从 https://gbf.wiki/Auld_Lang_Fry_PREMIUM/Story 提取剧情内容
并为 vajra 翻译。
```

```
角色列表提取缺少了一些角色，
你能检查一下页面上有什么吗？
```

### 无 Playwright MCP 时

需要直接提供 URL。查找方法：

1. 访问 https://gbf.wiki/
2. 搜索活动或角色
3. 导航到 Story 或 Voice 页面
4. 复制 URL 代号

示例提示：

```
从活动代号 "ZodiaCamp:_The_2nd_Divine_Generals_Assembly" 
提取剧情到 characters/vajra
```

```
将 characters/vajra/story/zodiacamp/raw 中的原始文件
翻译到 characters/vajra/story/zodiacamp/trans
```

---

## 故障排除

### 常见问题

#### 浏览器未安装

```
Error: Browser not found
```

**解决**：运行 `playwright install chromium`

#### API 密钥错误

```
Error: CLAUDE_API_KEY not set
```

**解决**：
1. 确认 `.env` 文件存在
2. 检查密钥格式是否正确
3. 确认文件中没有多余的空格或引号

#### Notion 页面找不到

```
Error: Could not find page with ID: xxx
```

**解决**：
1. 验证 `NOTION_ROOT_PAGE_ID` 是正确的 32 位 ID
2. 确认页面已共享给你的 Notion 集成
3. 检查集成是否有正确的权限

#### Notion 页面被归档

```
Error: Can't edit page on block with an archived ancestor
```

**解决**：
1. 删除缓存：`rm -rf .cache/notion/`
2. 重新运行上传命令
3. 如果问题持续，在 Notion 中手动删除相关页面后重试

#### 提取超时

```
Error: Timeout waiting for page
```

**解决**：
1. 在 `config.yaml` 中设置 `headless: false` 查看浏览器
2. 增加 `timeout` 值
3. 检查网络连接
4. 确认 Wiki 页面 URL 是否正确

#### 翻译不完整

部分长文件可能无法完整翻译。

**解决**：
1. 减小 `config.yaml` 中的 `chunk_size`（如改为 80）
2. 对特定文件单独重新运行翻译
3. 检查 API 额度是否充足

#### 语音表格为空

```
xxx: no data
```

**解决**：
1. 检查源文件格式是否正确
2. 确认表头包含 `Label`、`Japanese`、`Chinese` 等列
3. 查看日志了解具体解析错误

### 清理和重置

```bash
# 清除 Notion 缓存（解决页面同步问题）
rm -rf .cache/notion/

# 清除特定角色缓存
rm .cache/notion/vajra.json

# 重新下载本地数据
python -m lib.update_blhxfy --force

# 完全重新上传某角色
rm .cache/notion/vajra.json
python3 notion_upload.py vajra 瓦姬拉 --sync-mode force
```

### 获取帮助

如果遇到问题：

1. 查看命令输出中的具体错误信息
2. 使用 `--dry-run` 预览操作
3. 检查 `.env` 和 `config.yaml` 配置
4. 查看 `lib/docs/` 中的开发文档

---

## 许可证

MIT 许可证 - 详见 LICENSE 文件。
