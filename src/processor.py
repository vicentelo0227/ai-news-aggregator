"""
LLM 處理模組
負責使用 OpenAI API 進行文章摘要、評分與財經影響分析
"""
import json
from typing import Any

import openai
from loguru import logger

from .config import get_config

# LLM 系統提示詞（深度分析版）
SYSTEM_PROMPT = """你是一位資深的財經科技分析師，專精於 AI 科技、台股與美股市場。你的任務是深度分析新聞文章並提供全面的投資參考資訊。

請針對每篇文章提供以下分析：

1. **摘要**（300-500字）：
   - 詳細說明新聞的核心內容
   - 包含關鍵數據、時間點、涉及的公司或人物
   - 說明事件的背景脈絡與重要性

2. **評分**（1-10分）：
   - 新穎性（1-3分）：是否為突發或獨家消息？
   - 影響力（1-4分）：對產業或市場的影響程度？
   - 可行動性（1-3分）：是否需要立即關注或採取行動？

3. **分類**：
   - RESEARCH：學術研究、論文、技術突破
   - PRODUCT：產品發布、功能更新、服務上線
   - INDUSTRY：產業動態、併購、融資、人事異動
   - MARKET：市場動態、股價、財報、法人動向
   - POLICY：政策、法規、監管
   - OPINION：評論、分析、預測

4. **關聯企業分析**：
   - 列出可能直接或間接受影響的上市公司
   - 包含股票代號（台股用數字如 2330、美股用代碼如 NVDA）
   - 說明每家公司為何會受影響
   - 區分「直接受益/受損」與「間接受益/受損」

5. **市場影響評估**：
   - 短期影響（1-2週）：預期的立即市場反應
   - 中期影響（1-3個月）：可能的趨勢變化
   - 需關注的後續發展

6. **投資觀點**：
   - 潛在投資機會或風險
   - 建議的觀察重點
   - 相關產業鏈的連動效應

請嚴格以 JSON 格式回應：
{
  "summary": "詳細摘要（300-500字）",
  "score": 數字,
  "category": "類別",
  "related_companies": "受影響企業分析（包含股票代號與影響說明）",
  "market_impact": "市場影響評估（短期與中期）",
  "investment_insight": "投資觀點與建議"
}"""


def create_openai_client() -> openai.OpenAI:
    """建立 OpenAI 客戶端"""
    config = get_config()
    return openai.OpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=config.llm.get("timeout", 60)
    )


def process_single_article(client: openai.OpenAI, article: dict, news_type: str = "ai") -> dict | None:
    """
    使用 LLM 處理單篇文章（含深度財經分析）
    
    Args:
        client: OpenAI 客戶端
        article: 文章字典
        news_type: 新聞類型（ai/tw_stock/us_stock）
        
    Returns:
        包含摘要、評分、分析的文章字典，失敗則回傳 None
    """
    config = get_config()
    llm_config = config.llm
    
    # 準備輸入文字
    title = article.get("title", "")
    summary = article.get("summary", "")
    source = article.get("source", "")
    url = article.get("url", "")
    
    # 根據新聞類型調整提示
    type_context = {
        "ai": "這是一篇 AI 科技相關新聞，請特別關注對科技股與 AI 供應鏈的影響。",
        "tw_stock": "這是一篇台股相關新聞，請特別關注對台灣上市櫃公司的影響，使用台股代號（如 2330 台積電）。",
        "us_stock": "這是一篇美股相關新聞，請特別關注對美國上市公司的影響，使用美股代碼（如 NVDA、AAPL）。"
    }
    
    user_content = f"""新聞類型：{type_context.get(news_type, type_context["ai"])}

來源：{source}
標題：{title}
連結：{url}

內容摘要：
{summary}"""
    
    try:
        response = client.chat.completions.create(
            model=llm_config.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=llm_config.get("max_completion_tokens", 2000),
            temperature=llm_config.get("temperature", 0.3)
        )
        
        # 解析回應
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # 驗證必要欄位
        required_fields = ["summary", "score", "category"]
        if not all(key in result for key in required_fields):
            logger.warning(f"LLM 回應缺少必要欄位：{result}")
            return None
        
        # 確保評分在有效範圍內
        score = result.get("score", 0)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            logger.warning(f"評分無效：{score}，設為 5")
            result["score"] = 5
        
        # 合併原始文章資訊與分析結果
        processed_article = {
            **article,
            "ai_summary": result.get("summary", ""),
            "score": int(result["score"]),
            "category": result.get("category", "INDUSTRY"),
            "related_companies": result.get("related_companies", ""),
            "market_impact": result.get("market_impact", ""),
            "investment_insight": result.get("investment_insight", ""),
            "news_type": news_type
        }
        
        logger.debug(f"處理完成：{title[:30]}... → 評分 {result['score']}")
        return processed_article
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失敗：{e}")
        return None
    except openai.APIError as e:
        logger.error(f"OpenAI API 錯誤：{e}")
        return None
    except Exception as e:
        logger.error(f"處理文章時發生錯誤：{e}")
        return None


def process_articles(
    articles: list[dict],
    news_type: str = "ai",
    process_all: bool = True
) -> tuple[list[dict], list[dict]]:
    """
    批次處理文章列表
    
    Args:
        articles: 待處理的文章列表
        news_type: 新聞類型（ai/tw_stock/us_stock）
        process_all: 是否處理所有文章（True = 全部做摘要分析）
        
    Returns:
        (top_articles, all_processed_articles) 元組：
        - top_articles: 通過評分門檻的前 N 篇文章（用於 Slack）
        - all_processed_articles: 所有處理過的文章（用於 Google Sheet）
    """
    config = get_config()
    digest_config = config.digest
    
    min_score = digest_config.get("min_score", 6)
    max_articles = digest_config.get("max_articles", 20)
    
    # 決定處理數量
    if process_all:
        articles_to_process = articles  # 處理全部
    else:
        max_to_process = digest_config.get("max_articles_to_process", 50)
        articles_to_process = articles[:max_to_process]
    
    logger.info(f"開始 LLM 處理：{len(articles_to_process)} 篇文章（類型：{news_type}）")
    
    client = create_openai_client()
    all_processed = []
    top_articles = []
    
    for i, article in enumerate(articles_to_process):
        result = process_single_article(client, article, news_type)
        
        if result:
            all_processed.append(result)
            
            # 檢查是否通過評分門檻（用於 Slack 推送）
            if result.get("score", 0) >= min_score:
                top_articles.append(result)
                logger.info(f"[{i+1}/{len(articles_to_process)}] ✓ {result['title'][:40]}... (評分: {result['score']})")
            else:
                logger.info(f"[{i+1}/{len(articles_to_process)}] ○ {result['title'][:40]}... (評分: {result['score']})")
        else:
            logger.warning(f"[{i+1}/{len(articles_to_process)}] ✗ 處理失敗")
    
    # 依評分排序
    all_processed.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 限制 Slack 推送數量
    top_articles = top_articles[:max_articles]
    
    logger.info(f"LLM 處理完成：共 {len(all_processed)} 篇，Slack 推送 {len(top_articles)} 篇")
    
    return top_articles, all_processed
