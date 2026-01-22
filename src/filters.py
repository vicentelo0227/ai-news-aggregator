"""
過濾模組
負責關鍵字預過濾，在呼叫 LLM 之前減少文章數量
"""
from loguru import logger

from .config import get_config


def keyword_filter(article: dict) -> bool:
    """
    檢查文章是否通過關鍵字過濾
    
    Args:
        article: 包含 title 和 summary 的文章字典
        
    Returns:
        True 如果文章通過過濾，False 如果應該被排除
    """
    config = get_config()
    filters = config.filters
    
    # 組合標題和摘要進行檢查
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    
    # 檢查是否包含被封鎖的關鍵字
    blocked_keywords = filters.get("blocked_keywords", [])
    for keyword in blocked_keywords:
        if keyword.lower() in text:
            logger.debug(f"文章被封鎖關鍵字過濾：{keyword}")
            return False
    
    # 檢查是否包含至少一個必要關鍵字
    required_keywords = filters.get("required_keywords", [])
    if required_keywords:
        has_required = any(
            keyword.lower() in text 
            for keyword in required_keywords
        )
        if not has_required:
            logger.debug(f"文章缺少必要關鍵字")
            return False
    
    return True


def filter_articles(articles: list[dict]) -> list[dict]:
    """
    過濾文章列表
    
    Args:
        articles: 文章列表
        
    Returns:
        通過過濾的文章列表
    """
    original_count = len(articles)
    filtered = [a for a in articles if keyword_filter(a)]
    filtered_count = len(filtered)
    
    logger.info(f"關鍵字過濾：{original_count} → {filtered_count} 篇文章")
    
    return filtered
