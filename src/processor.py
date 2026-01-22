"""
LLM 處理模組
負責使用 OpenAI API 進行文章摘要與評分
"""
import json
from typing import Any

import openai
from loguru import logger

from .config import get_config

# LLM 系統提示詞
SYSTEM_PROMPT = """你是一位專業的 AI 科技新聞分析師。你的任務是分析新聞文章並提供：

1. **摘要**：用繁體中文撰寫 1-2 句精簡摘要，說明這篇文章的核心內容與重要性。
2. **評分**：根據以下標準給予 1-10 分的重要性評分：
   - 新穎性（1-3分）：這是突發新聞還是已知資訊的重複報導？
   - 影響力（1-4分）：這會影響多少人或產業？是否有實質改變？
   - 可行動性（1-3分）：讀者是否需要關注或採取行動？
3. **分類**：選擇最適合的類別
   - RESEARCH：學術研究、論文、技術突破
   - PRODUCT：產品發布、功能更新、服務上線
   - INDUSTRY：產業動態、併購、融資、人事異動
   - OPINION：評論、分析、預測
   - TUTORIAL：教學、指南、最佳實踐

請嚴格以 JSON 格式回應，不要包含其他文字：
{"summary": "繁體中文摘要", "score": 數字, "category": "類別"}"""


def create_openai_client() -> openai.OpenAI:
    """建立 OpenAI 客戶端"""
    config = get_config()
    return openai.OpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=config.llm.get("timeout", 30)
    )


def process_single_article(client: openai.OpenAI, article: dict) -> dict | None:
    """
    使用 LLM 處理單篇文章
    
    Args:
        client: OpenAI 客戶端
        article: 文章字典
        
    Returns:
        包含摘要、評分、分類的文章字典，失敗則回傳 None
    """
    config = get_config()
    llm_config = config.llm
    
    # 準備輸入文字
    title = article.get("title", "")
    summary = article.get("summary", "")
    source = article.get("source", "")
    
    user_content = f"""來源：{source}
標題：{title}

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
            max_tokens=llm_config.get("max_tokens", 300),
            temperature=llm_config.get("temperature", 0.3)
        )
        
        # 解析回應
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # 驗證必要欄位
        if not all(key in result for key in ["summary", "score", "category"]):
            logger.warning(f"LLM 回應缺少必要欄位：{result}")
            return None
        
        # 確保評分在有效範圍內
        score = result.get("score", 0)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            logger.warning(f"評分無效：{score}，設為 5")
            result["score"] = 5
        
        # 合併原始文章資訊
        processed_article = {
            **article,
            "ai_summary": result["summary"],
            "score": int(result["score"]),
            "category": result.get("category", "INDUSTRY")
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


def process_articles(articles: list[dict]) -> list[dict]:
    """
    批次處理文章列表
    
    Args:
        articles: 待處理的文章列表
        
    Returns:
        處理完成且通過評分門檻的文章列表，依評分降序排列
    """
    config = get_config()
    digest_config = config.digest
    
    max_to_process = digest_config.get("max_articles_to_process", 50)
    min_score = digest_config.get("min_score", 6)
    max_articles = digest_config.get("max_articles", 10)
    
    # 限制處理數量以控制 API 成本
    articles_to_process = articles[:max_to_process]
    
    logger.info(f"開始 LLM 處理：{len(articles_to_process)} 篇文章")
    
    client = create_openai_client()
    processed = []
    
    for i, article in enumerate(articles_to_process):
        result = process_single_article(client, article)
        
        if result:
            # 只保留通過評分門檻的文章
            if result.get("score", 0) >= min_score:
                processed.append(result)
                logger.info(f"[{i+1}/{len(articles_to_process)}] ✓ {result['title'][:40]}... (評分: {result['score']})")
            else:
                logger.debug(f"[{i+1}/{len(articles_to_process)}] ✗ 評分過低 ({result['score']})")
        else:
            logger.warning(f"[{i+1}/{len(articles_to_process)}] ✗ 處理失敗")
    
    # 依評分排序
    processed.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 限制最終數量
    final_articles = processed[:max_articles]
    
    logger.info(f"LLM 處理完成：{len(final_articles)} 篇文章通過篩選")
    
    return final_articles
