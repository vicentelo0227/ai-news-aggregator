# Multi-Type News Aggregator

Automated news aggregation system supporting AI, Taiwan Stock, and US Stock news. Fetches from multiple RSS sources, performs deep analysis with GPT-5.2, and delivers curated content to Slack with full records in Google Sheets.

## Features

- Multi-type news support: AI, Taiwan Stock (tw_stock), US Stock (us_stock)
- RSS feeds from reliable sources (TechCrunch, VentureBeat, Yahoo Finance, Bloomberg, etc.)
- Smart keyword filtering to exclude ads and irrelevant content
- GPT-5.2 deep analysis with 300-500 word summaries in Traditional Chinese
- Financial impact analysis: related companies, market impact, investment insights
- Importance scoring (1-10) to filter high-value articles
- Slack Block Kit formatted notifications
- Google Sheets integration for full article archive
- GitHub Actions scheduled automation

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/vicentelo0227/ai-news-aggregator.git
cd ai-news-aggregator
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required API keys:
- **SLACK_WEBHOOK_URL**: Create an Incoming Webhook from [Slack API](https://api.slack.com/apps)
- **OPENAI_API_KEY**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)

### 5. Run locally

```bash
# AI News (default)
python -m src.main

# Taiwan Stock News
python -m src.main --news-type tw_stock

# US Stock News
python -m src.main --news-type us_stock

# Dry run (no notifications)
python -m src.main --news-type ai --dry-run
```

## Deploy to GitHub Actions

1. Push the project to GitHub
2. Go to Settings > Secrets and variables > Actions
3. Add the following secrets:
   - `SLACK_WEBHOOK_URL`
   - `OPENAI_API_KEY`
   - `GOOGLE_CREDENTIALS` (Google service account JSON content)
4. Workflows will run automatically on schedule

### Schedule

| News Type | UTC Time | Taiwan Time | Frequency |
|-----------|----------|-------------|-----------|
| AI News | 00:00 | 08:00 | Daily |
| Taiwan Stock | 10:00 | 18:00 | Mon-Fri |
| US Stock | 14:00 | 22:00 | Mon-Fri |

### Manual Trigger

Go to Actions > Multi-Type News Digest > Run workflow > Select news type

## Configuration

Edit `config.yaml` to customize:

- **news_types**: Define news types with feeds and keywords
- **digest**: Summary settings (article count, score threshold)
- **llm**: LLM model settings (model, tokens, temperature)
- **slack**: Slack message format

## Google Sheets Output

Each run creates a new sheet tab with the following columns:

| Column | Description |
|--------|-------------|
| Fetch Time | Execution timestamp |
| Type | AI / Taiwan Stock / US Stock |
| Title | Article title |
| URL | Article link |
| Source | RSS source name |
| Score | AI score (1-10) |
| Category | RESEARCH / PRODUCT / INDUSTRY / MARKET / POLICY / OPINION |
| AI Summary | 300-500 word detailed summary |
| Related Companies | Potentially affected companies with stock codes |
| Market Impact | Short-term and mid-term market impact analysis |
| Investment Insight | Potential opportunities or risks |
| Published | Article publish time |

## Documentation

See [docs/使用說明書.md](docs/使用說明書.md) for detailed usage instructions (in Chinese).
