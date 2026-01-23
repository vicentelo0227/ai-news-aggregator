#!/usr/bin/env python3
"""
多類型新聞聚合器 - 主程式
支援 AI 新聞、台股新聞、美股新聞的自動抓取、LLM 深度分析、推送到 Slack 與 Google Sheet
"""
import argparse
import sys
import traceback
from datetime import datetime

from loguru import logger

from .config import get_config, reset_config
from .feeds import fetch_all_feeds
from .filters import filter_articles
from .processor import process_articles
from .slack_notifier import send_to_slack, send_error_notification
from .sheets_writer import write_articles_to_sheet


def parse_args() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="多類型新聞聚合器 - 支援 AI、台股、美股新聞"
    )
    parser.add_argument(
        "--news-type", "-t",
        type=str,
        choices=["ai", "tw_stock", "us_stock"],
        default="ai",
        help="新聞類型：ai（AI新聞）、tw_stock（台股）、us_stock（美股），預設為 ai"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式：只抓取和處理，不發送通知"
    )
    return parser.parse_args()


def main() -> int:
    """
    主程式進入點
    
    Returns:
        0 表示成功，1 表示失敗
    """
    # 解析參數
    args = parse_args()
    news_type = args.news_type
    dry_run = args.dry_run
    
    # 重置並載入設定
    reset_config()
    
    start_time = datetime.now()
    
    try:
        # 載入設定（指定新聞類型）
        config = get_config(news_type=news_type)
        
        logger.info("=" * 60)
        logger.info(f"🚀 新聞聚合器啟動 - {config.news_type_name}")
        logger.info(f"⏰ 執行時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📋 新聞類型：{news_type}")
        if dry_run:
            logger.info("🧪 測試模式：不會發送通知")
        logger.info("=" * 60)
        
        logger.info("✓ 設定載入完成")
        
        # Step 1: 抓取 RSS feeds
        logger.info(f"\n📡 Step 1: 抓取 RSS feeds（{config.news_type_name}）")
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
        
        # Step 3: LLM 深度分析（處理所有過濾後的文章）
        logger.info("\n🤖 Step 3: LLM 深度分析")
        process_all = config.digest.get("process_all_filtered", True)
        top_articles, all_processed = process_articles(
            filtered_articles,
            news_type=news_type,
            process_all=process_all
        )
        
        if not all_processed:
            logger.warning("沒有文章處理成功，結束執行")
            return 0
        
        # Step 4: 發送到 Slack（只發送 top 文章）
        if not dry_run:
            logger.info("\n📤 Step 4: 發送到 Slack")
            if top_articles:
                success = send_to_slack(top_articles, title=config.slack_title)
                if not success:
                    logger.error("Slack 發送失敗")
                    return 1
            else:
                logger.info("沒有文章通過評分門檻，跳過 Slack 推送")
        else:
            logger.info("\n📤 Step 4: [測試模式] 跳過 Slack 發送")
        
        # Step 5: 寫入 Google Sheet（所有處理過的文章）
        if not dry_run:
            logger.info("\n📊 Step 5: 寫入 Google Sheet")
            sheet_success = write_articles_to_sheet(all_processed, news_type=news_type)
            
            if sheet_success:
                logger.info(f"✓ 已寫入 {len(all_processed)} 篇文章到 Google Sheet")
            else:
                logger.warning("⚠️ Google Sheet 寫入失敗")
        else:
            logger.info("\n📊 Step 5: [測試模式] 跳過 Google Sheet 寫入")
        
        # 完成
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 執行完成！")
        logger.info(f"📋 類型：{config.news_type_name}")
        logger.info(f"📊 統計：抓取 {len(articles)} → 過濾 {len(filtered_articles)} → 分析 {len(all_processed)} → Slack {len(top_articles)} 篇")
        logger.info(f"⏱️ 耗時：{duration:.1f} 秒")
        logger.info("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ 使用者中斷執行")
        return 1
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"\n❌ 執行失敗：{error_msg}")
        
        # 嘗試發送錯誤通知
        if not dry_run:
            try:
                send_error_notification(str(e))
            except Exception:
                pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
