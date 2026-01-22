"""
Slack 通知模組
負責格式化訊息並推送到 Slack
"""
import time
from datetime import datetime
from typing import Any

import requests
from loguru import logger

from .config import get_config


def format_slack_blocks(articles: list[dict]) -> list[dict[str, Any]]:
    """
    將文章列表格式化為 Slack Block Kit 格式
    
    Args:
        articles: 處理完成的文章列表
        
    Returns:
        Slack blocks 列表
    """
    config = get_config()
    slack_config = config.slack
    
    # 標題區塊
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": slack_config.get("title", "📰 AI 新聞摘要"),
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*{datetime.now().strftime('%Y年%m月%d日 %H:%M')}* • {len(articles)} 則精選報導"
                }
            ]
        },
        {"type": "divider"}
    ]
    
    # 文章區塊
    for i, article in enumerate(articles):
        # 主要內容
        title = article.get("title", "無標題")
        url = article.get("url", "#")
        summary = article.get("ai_summary", article.get("summary", ""))
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i+1}. <{url}|{title}>*\n{summary}"
            }
        })
        
        # 元資訊
        meta_elements = []
        
        if slack_config.get("show_score", True):
            score = article.get("score", 0)
            # 根據分數使用不同 emoji
            score_emoji = "🔥" if score >= 8 else "⭐" if score >= 6 else "📌"
            meta_elements.append({
                "type": "mrkdwn",
                "text": f"{score_emoji} *{score}/10*"
            })
        
        if slack_config.get("show_category", True):
            category = article.get("category", "INDUSTRY")
            category_emoji = {
                "RESEARCH": "🔬",
                "PRODUCT": "🚀",
                "INDUSTRY": "🏢",
                "OPINION": "💭",
                "TUTORIAL": "📚"
            }.get(category, "📄")
            meta_elements.append({
                "type": "mrkdwn",
                "text": f"{category_emoji} {category}"
            })
        
        if slack_config.get("show_source", True):
            source = article.get("source", "Unknown")
            meta_elements.append({
                "type": "mrkdwn",
                "text": f"🔗 {source}"
            })
        
        if meta_elements:
            blocks.append({
                "type": "context",
                "elements": meta_elements
            })
        
        # 分隔線（最後一篇不加）
        if i < len(articles) - 1:
            blocks.append({"type": "divider"})
    
    # 結尾
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "🤖 由 AI 新聞聚合器自動產生 | <https://github.com/your-username/ai-news-aggregator|GitHub>"
            }
        ]
    })
    
    return blocks


def send_to_slack(articles: list[dict], max_retries: int = 3) -> bool:
    """
    發送訊息到 Slack
    
    Args:
        articles: 處理完成的文章列表
        max_retries: 最大重試次數
        
    Returns:
        True 如果發送成功，False 如果失敗
    """
    config = get_config()
    webhook_url = config.SLACK_WEBHOOK_URL
    
    if not webhook_url:
        logger.error("Slack Webhook URL 未設定")
        return False
    
    if not articles:
        logger.warning("沒有文章可發送")
        return False
    
    # 建立訊息
    blocks = format_slack_blocks(articles)
    payload = {
        "text": f"AI 新聞摘要 - {len(articles)} 則報導",  # 備用文字
        "blocks": blocks
    }
    
    # 發送（含重試邏輯）
    for attempt in range(max_retries):
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"✓ 成功發送 {len(articles)} 篇文章到 Slack")
                return True
            
            elif response.status_code == 429:
                # Rate limited
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(f"Slack 速率限制，等待 {retry_after} 秒後重試...")
                time.sleep(retry_after)
                continue
            
            else:
                logger.error(f"Slack 回應錯誤：{response.status_code} - {response.text}")
                return False
                
        except requests.Timeout:
            logger.warning(f"Slack 請求超時（嘗試 {attempt + 1}/{max_retries}）")
            time.sleep(2 ** attempt)  # 指數退避
            
        except requests.RequestException as e:
            logger.error(f"Slack 請求失敗：{e}")
            time.sleep(2 ** attempt)
    
    logger.error("Slack 發送失敗，已達最大重試次數")
    return False


def send_error_notification(error_message: str) -> bool:
    """
    發送錯誤通知到 Slack
    
    Args:
        error_message: 錯誤訊息
        
    Returns:
        True 如果發送成功
    """
    config = get_config()
    webhook_url = config.SLACK_WEBHOOK_URL
    
    if not webhook_url:
        return False
    
    payload = {
        "text": f"⚠️ AI 新聞聚合器執行錯誤",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ 執行錯誤通知", "emoji": True}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{error_message}```"}
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False
