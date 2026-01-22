"""
RSS 抓取模組
負責從多個 RSS 來源抓取文章
"""
import re
from datetime import datetime
from typing import Any

import feedparser
import requests
from loguru import logger

from .config import get_config


def parse_published_date(entry: dict) -> str:
    """
    解析文章發布日期
    
    Args:
        entry: feedparser 的 entry 物件
        
    Returns:
        格式化的日期字串，如果解析失敗則回傳空字串
    """
    # 嘗試不同的日期欄位
    for field in ["published_parsed", "updated_parsed", "created_parsed"]:
        parsed_time = entry.get(field)
        if parsed_time:
            try:
                dt = datetime(*parsed_time[:6])
                return dt.strftime("%Y-%m-%d %H:%M")
            except (TypeError, ValueError):
                continue
    
    # 備用：直接使用字串
    for field in ["published", "updated", "created"]:
        date_str = entry.get(field)
        if date_str:
            return date_str[:19]  # 截斷到秒
    
    return ""


def clean_html(text: str) -> str:
    """
    簡單清理 HTML 標籤
    
    Args:
        text: 可能包含 HTML 的文字
        
    Returns:
        清理後的純文字
    """
    # 移除 HTML 標籤
    clean = re.sub(r'<[^>]+>', '', text)
    # 處理 HTML entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    # 移除多餘空白
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def fetch_single_feed(feed_config: dict[str, Any], timeout: int = 15) -> list[dict]:
    """
    抓取單一 RSS feed
    
    Args:
        feed_config: feed 設定，包含 name 和 url
        timeout: 請求超時秒數
        
    Returns:
        文章列表
    """
    config = get_config()
    articles_per_feed = config.digest.get("articles_per_feed", 15)
    
    feed_name = feed_config.get("name", "Unknown")
    feed_url = feed_config.get("url", "")
    
    if not feed_url:
        logger.warning(f"Feed '{feed_name}' 缺少 URL")
        return []
    
    try:
        # 使用 requests 抓取以獲得更好的錯誤處理
        response = requests.get(
            feed_url,
            timeout=timeout,
            headers={"User-Agent": "AI-News-Aggregator/1.0"}
        )
        response.raise_for_status()
        
        # 解析 RSS
        feed = feedparser.parse(response.content)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed '{feed_name}' 解析警告：{feed.bozo_exception}")
        
        articles = []
        for entry in feed.entries[:articles_per_feed]:
            # 取得摘要，優先使用 summary，其次 description，最後 content
            summary = entry.get("summary", "")
            if not summary:
                summary = entry.get("description", "")
            if not summary and entry.get("content"):
                summary = entry.content[0].get("value", "")
            
            article = {
                "title": clean_html(entry.get("title", "無標題")),
                "url": entry.get("link", ""),
                "summary": clean_html(summary)[:800],  # 限制摘要長度
                "source": feed_name,
                "published": parse_published_date(entry),
                "feed_url": feed_url
            }
            
            # 基本驗證
            if article["title"] and article["url"]:
                articles.append(article)
        
        logger.info(f"✓ {feed_name}：抓取 {len(articles)} 篇文章")
        return articles
        
    except requests.Timeout:
        logger.error(f"✗ {feed_name}：請求超時")
        return []
    except requests.RequestException as e:
        logger.error(f"✗ {feed_name}：請求失敗 - {e}")
        return []
    except Exception as e:
        logger.error(f"✗ {feed_name}：未預期錯誤 - {e}")
        return []


def fetch_all_feeds() -> list[dict]:
    """
    抓取所有已啟用的 RSS feeds
    
    Returns:
        所有文章的合併列表
    """
    config = get_config()
    feeds = config.feeds
    
    if not feeds:
        logger.warning("沒有啟用的 RSS feeds")
        return []
    
    logger.info(f"開始抓取 {len(feeds)} 個 RSS 來源...")
    
    all_articles = []
    for feed_config in feeds:
        articles = fetch_single_feed(feed_config)
        all_articles.extend(articles)
    
    logger.info(f"總共抓取 {len(all_articles)} 篇文章")
    
    return all_articles
