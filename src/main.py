#!/usr/bin/env python3
"""
AI 新聞聚合器 - 主程式
自動抓取 AI 新聞、LLM 摘要評分、推送到 Slack
"""
import sys
import traceback
from datetime import datetime

from loguru import logger

from .config import get_config
from .feeds import fetch_all_feeds
from .filters import filter_articles
from .processor import process_articles
from .slack_notifier import send_to_slack, send_error_notification
from .sheets_writer import write_articles_to_sheet


def main() -> int:
    """
    主程式進入點
    
    Returns:
        0 表示成功，1 表示失敗
    """
    start_time = datetime.now()
    logger.info("=" * 50)
    logger.info("🚀 AI 新聞聚合器啟動")
    logger.info(f"⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    try:
        # 載入設定
        config = get_config()
        logger.info("✓ 設定載入完成")
        
        # Step 1: 抓取 RSS feeds
        logger.info("\n📡 Step 1: 抓取 RSS feeds")
        articles = fetch_all_feeds()
        
        if not articles:
            logger.warning("沒有抓取到任何文章，結束執行")
            return 0
        
        # Step 2: 關鍵字過濾
        logger.info("\n🔍 Step 2: 關鍵字過濾")
        filtered_articles = filter_articles(articles)
        
        if not filtered_articles:
            logger.warning("所有文章都被過濾掉了，結束執行")
            return 0
        
        # Step 3: LLM 處理
        logger.info("\n🤖 Step 3: LLM 摘要與評分")
        processed_articles = process_articles(filtered_articles)
        
        if not processed_articles:
            logger.warning("沒有文章通過評分門檻，結束執行")
            return 0
        
        # Step 4: 發送到 Slack
        logger.info("\n📤 Step 4: 發送到 Slack")
        success = send_to_slack(processed_articles)
        
        if not success:
            logger.error("Slack 發送失敗")
            return 1
        
        # Step 5: 寫入 Google Sheet（所有過濾後的文章）
        logger.info("\n📊 Step 5: 寫入 Google Sheet")
        
        # 合併已處理和未處理的文章
        processed_urls = {a.get("url") for a in processed_articles}
        all_articles_for_sheet = list(processed_articles)  # 先加入已處理的
        
        # 加入未被 LLM 處理的過濾後文章
        for article in filtered_articles:
            if article.get("url") not in processed_urls:
                all_articles_for_sheet.append(article)
        
        sheet_success = write_articles_to_sheet(all_articles_for_sheet)
        
        if sheet_success:
            logger.info(f"✓ 已寫入 {len(all_articles_for_sheet)} 篇文章到 Google Sheet")
        else:
            logger.warning("⚠️ Google Sheet 寫入失敗，但 Slack 推送已完成")
        
        # 完成
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 50)
        logger.info("✅ 執行完成！")
        logger.info(f"📊 統計：抓取 {len(articles)} → 過濾後 {len(filtered_articles)} → Slack {len(processed_articles)} 篇 → Sheet {len(all_articles_for_sheet)} 篇")
        logger.info(f"⏱️ 耗時：{duration:.1f} 秒")
        logger.info("=" * 50)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ 使用者中斷執行")
        return 1
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"\n❌ 執行失敗：{error_msg}")
        
        # 嘗試發送錯誤通知
        try:
            send_error_notification(str(e))
        except Exception:
            pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
