"""
基本測試
"""
import pytest


def test_imports():
    """測試模組是否可正常 import"""
    from src.config import Config, get_config
    from src.feeds import fetch_all_feeds, fetch_single_feed
    from src.filters import keyword_filter, filter_articles
    from src.processor import process_articles
    from src.slack_notifier import send_to_slack
    
    assert True


def test_keyword_filter():
    """測試關鍵字過濾功能"""
    from src.filters import keyword_filter
    
    # 模擬設定（這裡只做基本測試）
    article_with_ai = {
        "title": "OpenAI releases new GPT model",
        "summary": "A breakthrough in AI technology"
    }
    
    article_without_ai = {
        "title": "Best recipes for summer",
        "summary": "Delicious food ideas"
    }
    
    # 注意：實際測試需要設定 mock config
    # 這裡只是範例結構


def test_clean_html():
    """測試 HTML 清理功能"""
    from src.feeds import clean_html
    
    html_text = "<p>Hello <strong>World</strong></p>"
    clean_text = clean_html(html_text)
    
    assert "<p>" not in clean_text
    assert "<strong>" not in clean_text
    assert "Hello" in clean_text
    assert "World" in clean_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
