# AI 新聞聚合器 🤖📰

自動化 AI 新聞聚合系統，每天定時從多個 RSS 來源抓取 AI/科技新聞，透過 LLM 進行摘要與重要性評分，最後將精選內容推送到 Slack。

## ✨ 功能特色

- 📡 從多個可靠來源抓取 AI 新聞（TechCrunch、VentureBeat、Hacker News 等）
- 🔍 智慧關鍵字過濾，排除廣告與不相關內容
- 🤖 使用 GPT-4o-mini 產生繁體中文摘要並評分
- 📊 依重要性評分（1-10 分）篩選高價值文章
- 💬 精美的 Slack Block Kit 格式推送
- ⏰ GitHub Actions 自動排程，完全免費

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/your-username/ai-news-aggregator.git
cd ai-news-aggregator
```

### 2. 建立虛擬環境

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 Windows: venv\Scripts\activate
```

### 3. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，填入你的 API keys
```

需要的 API keys：
- **SLACK_WEBHOOK_URL**：從 [Slack API](https://api.slack.com/apps) 建立 Incoming Webhook
- **OPENAI_API_KEY**：從 [OpenAI Platform](https://platform.openai.com/api-keys) 取得

### 5. 本地測試

```bash
python -m src.main
```

## 📦 部署到 GitHub Actions

1. 將專案推送到 GitHub
2. 前往 Settings → Secrets and variables → Actions
3. 新增以下 secrets：
   - `SLACK_WEBHOOK_URL`
   - `OPENAI_API_KEY`
4. 工作流程會自動在設定時間執行

### 手動觸發

前往 Actions → Daily AI News Digest → Run workflow

## ⚙️ 設定說明

編輯 `config.yaml` 自訂：

- **feeds**：RSS 來源，可新增或停用
- **filters**：關鍵字過濾規則
- **digest**：摘要設定（文章數量、評分門檻）
- **llm**：LLM 模型設定
- **slack**：Slack 訊息格式

## 💰 成本估算

| 項目 | 每月成本 |
|------|----------|
| GitHub Actions（公開 repo） | 免費 |
| OpenAI GPT-4o-mini | ~$2-5 |
| Slack | 免費 |
| **總計** | **~$2-5** |

## 📝 授權

MIT License
