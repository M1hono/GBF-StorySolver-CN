# Translation API Comparison (Dec 2024)

## 🔥 Cost Optimization: Batch API = 50% OFF

All major APIs offer **Batch mode with 50% discount**:

| Engine | Standard | **Batch Mode** | Savings |
|--------|----------|----------------|---------|
| OpenAI GPT-4o-mini | $0.10/130K | **$0.05/130K** | 50% |
| Claude Sonnet 4 | $2.34/130K | **$1.17/130K** | 50% |
| Gemini 2.0 Flash | $0.05/130K | **$0.025/130K** | 50% |

**Batch = 24h turnaround, but 50% cheaper!**

## Quick Comparison (Standard Pricing)

| Engine | Input Cost | Output Cost | Quality | Glossary | Recommended |
|--------|-----------|-------------|---------|----------|-------------|
| **Gemini 2.0 Flash** | **$0.075/1M** | **$0.30/1M** | ✅ Good | ✅ Prompt | 🥇 Best value |
| OpenAI GPT-4o-mini | $0.15/1M | $0.60/1M | ✅ Good | ✅ Prompt | 🥈 Balanced |
| Claude Sonnet 4 | $3/1M | $15/1M | ⭐ Best | ✅ Prompt | Important content |
| DeepL Free | Free | Free | OK | ✅ Native | ⚠️ Format issues |
| DeepL Pro | $25/1M | $25/1M | OK | ✅ Native | ⚠️ Format issues |
| Caiyun | ¥40/1M | ¥40/1M | OK | ❌ No | Quick preview |

## Cost Calculation for 130K Tokens (1 Event Story)

| Engine | Input Cost | Output Cost | Total |
|--------|-----------|-------------|-------|
| **Gemini 2.0 Flash** | $0.01 | $0.04 | **$0.05** |
| OpenAI GPT-4o-mini | $0.02 | $0.08 | **$0.10** |
| Claude Sonnet 4 | $0.39 | $1.95 | **$2.34** |
| Claude Sonnet 3.5 | $0.39 | $1.95 | **$2.34** |
| Claude Opus | $1.95 | $9.75 | **$11.70** |
| Claude Haiku 3.5 | $0.13 | $0.65 | **$0.78** |

## Glossary Support

### Native Glossary (DeepL)
- DeepL has built-in glossary API
- Create glossary with source → target pairs
- Applied automatically during translation
- **Problem**: Doesn't preserve Markdown formatting well

### Prompt-based Glossary (OpenAI, Gemini, Claude)
- Include terminology in system prompt
- Works well when filtered to relevant terms
- Preserves formatting better
- **Recommended approach** for this project

```python
# Example: Smart glossary filtering
def get_terminology(content: str) -> str:
    """Filter terminology to names appearing in content."""
    # Only include relevant terms, not entire dictionary
    # Keeps prompt size manageable
```

## Detailed Pricing (Dec 2024)

### Google Gemini
| Model | Input | Output | Context |
|-------|-------|--------|---------|
| Gemini 2.0 Flash | $0.075/1M | $0.30/1M | 1M |
| Gemini 1.5 Pro | $1.25/1M | $5.00/1M | 2M |
| Gemini 1.5 Flash | $0.075/1M | $0.30/1M | 1M |

### OpenAI
| Model | Input | Output | Context |
|-------|-------|--------|---------|
| GPT-4o | $2.50/1M | $10.00/1M | 128K |
| GPT-4o-mini | $0.15/1M | $0.60/1M | 128K |
| GPT-4.1 | $2.00/1M | $8.00/1M | 1M |
| GPT-4.1-mini | $0.40/1M | $1.60/1M | 1M |

### Anthropic Claude
| Model | Input | Output | Context |
|-------|-------|--------|---------|
| Claude Opus 4 | $15/1M | $75/1M | 200K |
| Claude Sonnet 4 | $3/1M | $15/1M | 200K |
| Claude Sonnet 3.5 | $3/1M | $15/1M | 200K |
| Claude Haiku 3.5 | $1/1M | $5/1M | 200K |

### DeepL
| Plan | Characters/Month | Cost |
|------|-----------------|------|
| Free | 500K | $0 |
| Pro | Unlimited | $25/1M chars |

### Caiyun
| Tier | Cost |
|------|------|
| Standard | ¥40/1M chars (~$5.50) |

## Quality Comparison

### Test Content: JP Story (121 lines)

**DeepL Result** (❌ Problems):
```markdown
***路西法：** ...... 路西菲尔。 这个地方对我们来说太小了。
```
- Extra asterisks breaking format
- Inconsistent name translations
- Added periods where none existed

**OpenAI GPT-4o-mini Result** (✅ Good):
```markdown
**路西法:** ……是路西菲尔啊。这里也变得狭窄了，得开辟新的区域。
```
- Clean formatting
- Consistent character names
- Natural Chinese expression

**Gemini 2.0 Flash Result** (✅ Good):
```markdown
**路西法:** ……路西菲尔吗。这里也变得拥挤了，要开辟新的区域。
```
- Clean formatting
- Consistent character names
- Slightly different wording (both natural)

## Recommendations

### Daily Translation Work
**Use: Gemini 2.0 Flash**
- Cheapest option ($0.05/event)
- Good quality
- Fast

### Important/Featured Content
**Use: Claude Sonnet 4**
- Best translation quality
- Better handling of nuance
- Worth the cost for key content

### Batch Processing
**Use: OpenAI GPT-4o-mini**
- Good balance of cost/quality
- More stable API
- Better rate limits

### Quick Preview
**Use: Caiyun**
- Very fast
- Cheap
- Acceptable quality for first pass

## Configuration

### config.yaml
```yaml
translation:
  # Choose your preferred model
  claude_model: claude-sonnet-4-20250514
  openai_model: gpt-4o-mini
  gemini_model: gemini-2.0-flash
```

### .env
```bash
# Required API keys (add only what you need)
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
DEEPL_API_KEY=xxx:fx
```

## Usage

### Standard (Realtime)
```bash
# Estimate cost first
python -m lib.translate cost ./raw

# Gemini (cheapest)
python -m lib.translate gemini ./raw ./trans

# OpenAI (balanced)
python -m lib.translate openai ./raw ./trans

# Claude (best quality)
python -m lib.translate claude ./raw ./trans
```

### Batch Mode (50% OFF, 24h turnaround)
```bash
# Submit batch job
python -m lib.translators.batch_translator submit ./raw --engine openai

# Check status
python -m lib.translators.batch_translator status <batch_id>

# Download when ready
python -m lib.translators.batch_translator download <batch_id> ./trans
```

## Cost Optimization Summary

| Technique | Savings | Effort |
|-----------|---------|--------|
| Use Gemini instead of Claude | 98% | Low |
| Use Batch API | 50% | Medium |
| Minimal prompts | ~20% | Done |
| Filter relevant terminology | ~10% | Done |

**Best strategy**: Gemini Batch = **$0.025/event** (was $2.34 with Claude standard)
