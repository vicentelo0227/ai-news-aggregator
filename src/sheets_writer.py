"""
Google Sheets 寫入模組
負責將文章資料寫入 Google Sheet
"""
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

# Google Sheets API 範圍
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Sheet ID
SHEET_ID = "1k3Y-PBop-Cq7KELaQc9BqqySws_6xedH5yDHdcS2ByU"


def get_credentials_path() -> Path:
    """取得憑證檔案路徑"""
    # 優先使用專案目錄下的 credentials.json
    project_root = Path(__file__).parent.parent
    credentials_path = project_root / "credentials.json"
    
    if credentials_path.exists():
        return credentials_path
    
    # 備用路徑
    alt_path = Path.home() / "Downloads" / "stock-bot-484104-481b65221e36.json"
    if alt_path.exists():
        return alt_path
    
    raise FileNotFoundError("找不到 Google 服務帳戶憑證檔案")


def get_gspread_client() -> gspread.Client:
    """建立 gspread 客戶端"""
    credentials_path = get_credentials_path()
    credentials = Credentials.from_service_account_file(
        str(credentials_path),
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


def write_articles_to_sheet(
    articles: list[dict],
    sheet_id: str = SHEET_ID
) -> bool:
    """
    將文章寫入 Google Sheet（每次執行建立新分頁）
    
    Args:
        articles: 文章列表
        sheet_id: Google Sheet ID
        
    Returns:
        True 如果寫入成功
    """
    if not articles:
        logger.warning("沒有文章可寫入 Google Sheet")
        return False
    
    try:
        # 連接 Google Sheet
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)
        
        # 使用查詢時間作為工作表名稱（YYYY/MM/DD HH:MM 格式）
        current_time = datetime.now()
        worksheet_name = current_time.strftime("%Y/%m/%d %H:%M")
        
        # 建立新工作表
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name, 
            rows=len(articles) + 10,  # 預留空間
            cols=10
        )
        logger.info(f"建立新工作表：{worksheet_name}")
        
        # 準備標題列
        headers = [
            "抓取時間",
            "標題",
            "URL",
            "來源",
            "AI 摘要",
            "評分",
            "分類",
            "原始摘要",
            "發布時間"
        ]
        
        # 寫入標題列
        worksheet.append_row(headers)
        
        # 凍結第一行（表頭）
        worksheet.freeze(rows=1)
        logger.info("已凍結第一行（表頭）")
        
        # 準備資料列
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        
        for article in articles:
            row = [
                time_str,
                article.get("title", ""),
                article.get("url", ""),
                article.get("source", ""),
                article.get("ai_summary", ""),
                str(article.get("score", "")),
                article.get("category", ""),
                article.get("summary", "")[:500],  # 限制長度
                article.get("published", "")
            ]
            rows.append(row)
        
        # 批次寫入（更有效率）
        if rows:
            worksheet.append_rows(rows, value_input_option='USER_ENTERED')
            logger.info(f"✓ 成功寫入 {len(rows)} 篇文章到工作表 '{worksheet_name}'")
        
        return True
        
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API 錯誤：{e}")
        return False
    except FileNotFoundError as e:
        logger.error(f"憑證檔案錯誤：{e}")
        return False
    except Exception as e:
        logger.error(f"寫入 Google Sheet 時發生錯誤：{e}")
        return False


def write_daily_digest(
    processed_articles: list[dict],
    all_filtered_articles: list[dict],
    sheet_id: str = SHEET_ID
) -> bool:
    """
    寫入每日摘要到 Google Sheet
    
    Args:
        processed_articles: 經過 LLM 處理的文章（有摘要和評分）
        all_filtered_articles: 所有過濾後的文章
        sheet_id: Google Sheet ID
        
    Returns:
        True 如果寫入成功
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)
        
        # 取得今天的日期作為工作表名稱
        today = datetime.now().strftime("%Y-%m-%d")
        worksheet_name = f"Daily_{today}"
        
        # 建立或取得工作表
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet.clear()  # 清除當天的舊資料
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=500, cols=10)
        
        # 寫入標題
        headers = [
            "抓取時間",
            "標題",
            "URL",
            "來源",
            "AI 摘要",
            "評分",
            "分類",
            "原始摘要",
            "發布時間"
        ]
        worksheet.append_row(headers)
        
        # 準備資料
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        
        # 建立已處理文章的 URL 集合，用於快速查找
        processed_urls = {a.get("url") for a in processed_articles}
        
        # 先寫入已處理的文章（有 AI 摘要和評分）
        for article in processed_articles:
            row = [
                current_time,
                article.get("title", ""),
                article.get("url", ""),
                article.get("source", ""),
                article.get("ai_summary", ""),
                str(article.get("score", "")),
                article.get("category", ""),
                article.get("summary", "")[:500],
                article.get("published", "")
            ]
            rows.append(row)
        
        # 再寫入未處理的文章（只有原始資料）
        for article in all_filtered_articles:
            if article.get("url") not in processed_urls:
                row = [
                    current_time,
                    article.get("title", ""),
                    article.get("url", ""),
                    article.get("source", ""),
                    "",  # 無 AI 摘要
                    "",  # 無評分
                    "",  # 無分類
                    article.get("summary", "")[:500],
                    article.get("published", "")
                ]
                rows.append(row)
        
        # 批次寫入
        if rows:
            worksheet.append_rows(rows, value_input_option='USER_ENTERED')
            logger.info(f"✓ 成功寫入 {len(rows)} 篇文章到工作表 '{worksheet_name}'")
        
        return True
        
    except Exception as e:
        logger.error(f"寫入每日摘要時發生錯誤：{e}")
        return False
