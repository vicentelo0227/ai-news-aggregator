"""
Google Sheets 寫入模組
負責將文章資料寫入 Google Sheet（含深度分析欄位）
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

# #region agent log
DEBUG_LOG_PATH = "/Users/luoyuxiang/new_catch/.cursor/debug.log"
def _debug_log(hypothesis_id: str, location: str, message: str, data: dict):
    # Log to both file (local) and logger (GitHub Actions)
    log_entry = json.dumps({"hypothesisId": hypothesis_id, "location": location, "message": message, "data": data}, ensure_ascii=False)
    logger.debug(f"[DEBUG] {log_entry}")
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except: pass
# #endregion


def clean_text_for_sheets(text: str) -> str:
    """
    清理文字中的控制字符和特殊 Unicode，確保可以寫入 Google Sheets
    
    Args:
        text: 原始文字
        
    Returns:
        清理後的文字
    """
    if not text:
        return ""
    
    # 移除所有控制字符 (0x00-0x1F)，但保留 \t(0x09) \n(0x0a) \r(0x0d)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    # 移除 DEL 字符和其他特殊控制字符
    text = re.sub(r'[\x7f]', '', text)
    
    # 移除特殊 Unicode 字符
    text = text.replace('\u200b', '')  # 零寬空格
    text = text.replace('\ufeff', '')  # BOM
    text = text.replace('\u200c', '')  # 零寬非連接符
    text = text.replace('\u200d', '')  # 零寬連接符
    text = text.replace('\u2028', '\n')  # 行分隔符 -> 換行
    text = text.replace('\u2029', '\n')  # 段落分隔符 -> 換行
    
    # 移除其他可能導致 JSON 問題的字符
    text = re.sub(r'[\x80-\x9f]', '', text)  # C1 控制字符
    
    return text

# Google Sheets API 範圍
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Sheet ID
SHEET_ID = "1k3Y-PBop-Cq7KELaQc9BqqySws_6xedH5yDHdcS2ByU"

# 新聞類型顯示名稱
NEWS_TYPE_NAMES = {
    "ai": "AI 新聞",
    "tw_stock": "台股新聞",
    "us_stock": "美股新聞"
}


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
    sheet_id: str = SHEET_ID,
    news_type: str = "ai"
) -> bool:
    """
    將文章寫入 Google Sheet（每次執行建立新分頁，含深度分析欄位）
    
    Args:
        articles: 文章列表
        sheet_id: Google Sheet ID
        news_type: 新聞類型（ai/tw_stock/us_stock）
        
    Returns:
        True 如果寫入成功
    """
    if not articles:
        logger.warning("沒有文章可寫入 Google Sheet")
        return False
    
    try:
        # #region agent log
        _debug_log("E", "sheets_writer.py:start", "Starting write_articles_to_sheet", {"article_count": len(articles), "news_type": news_type})
        # #endregion
        
        # 連接 Google Sheet
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)
        
        # #region agent log
        _debug_log("E", "sheets_writer.py:connected", "Connected to spreadsheet", {"sheet_id": sheet_id})
        # #endregion
        
        # 使用查詢時間與類型作為工作表名稱
        current_time = datetime.now()
        type_name = NEWS_TYPE_NAMES.get(news_type, news_type)
        worksheet_name = f"{current_time.strftime('%Y/%m/%d %H:%M')} {type_name}"
        
        # #region agent log
        _debug_log("F", "sheets_writer.py:worksheet_name", "Worksheet name created", {"worksheet_name": worksheet_name})
        # #endregion
        
        # 建立新工作表
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name, 
            rows=len(articles) + 10,
            cols=12  # 增加欄位數
        )
        logger.info(f"建立新工作表：{worksheet_name}")
        
        # #region agent log
        _debug_log("E", "sheets_writer.py:worksheet_created", "Worksheet created successfully", {})
        # #endregion
        
        # 準備標題列（新增深度分析欄位）
        headers = [
            "抓取時間",
            "類型",
            "標題",
            "URL",
            "來源",
            "評分",
            "分類",
            "AI 摘要",
            "關聯企業",
            "市場影響",
            "投資觀點",
            "發布時間"
        ]
        
        # 寫入標題列
        worksheet.append_row(headers)
        
        # #region agent log
        _debug_log("E", "sheets_writer.py:headers_written", "Headers written successfully", {})
        # #endregion
        
        # 凍結第一行（表頭）
        worksheet.freeze(rows=1)
        logger.info("已凍結第一行（表頭）")
        
        # #region agent log
        _debug_log("E", "sheets_writer.py:frozen", "Row frozen successfully", {})
        # #endregion
        
        # 準備資料列
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        type_display = NEWS_TYPE_NAMES.get(news_type, news_type)
        rows = []
        
        # #region agent log
        _debug_log("A", "sheets_writer.py:prepare_rows", "Starting to prepare rows", {"article_count": len(articles)})
        # #endregion
        
        for idx, article in enumerate(articles):
            # #region agent log
            # Check for control characters in each field BEFORE cleaning
            fields_to_check = ["title", "ai_summary", "related_companies", "market_impact", "investment_insight", "summary"]
            for field in fields_to_check:
                val = article.get(field, "")
                if val:
                    # Find ALL control characters (0x00-0x1F)
                    control_chars = re.findall(r'[\x00-\x1f]', val)
                    if control_chars:
                        _debug_log("A", f"sheets_writer.py:article_{idx}:{field}", "Found control characters BEFORE clean", {"field": field, "chars": [hex(ord(c)) for c in control_chars[:10]], "char_count": len(control_chars), "title": article.get("title", "")[:50]})
            # #endregion
            
            row = [
                time_str,
                type_display,
                clean_text_for_sheets(article.get("title", "")),
                article.get("url", ""),
                clean_text_for_sheets(article.get("source", "")),
                str(article.get("score", "")),
                article.get("category", ""),
                clean_text_for_sheets(article.get("ai_summary", "")),  # 不截斷，完整保留
                clean_text_for_sheets(article.get("related_companies", "")),  # 關聯企業分析
                clean_text_for_sheets(article.get("market_impact", "")),  # 市場影響
                clean_text_for_sheets(article.get("investment_insight", "")),  # 投資觀點
                article.get("published", "")
            ]
            rows.append(row)
        
        # #region agent log
        _debug_log("B", "sheets_writer.py:before_append", "About to call append_rows", {"row_count": len(rows), "first_row_lengths": [len(str(c)) for c in rows[0]] if rows else []})
        # #endregion
        
        # 批次寫入（更有效率）
        if rows:
            try:
                worksheet.append_rows(rows, value_input_option='USER_ENTERED')
                logger.info(f"✓ 成功寫入 {len(rows)} 篇文章到工作表 '{worksheet_name}'")
                # #region agent log
                _debug_log("B", "sheets_writer.py:after_append", "append_rows succeeded", {"row_count": len(rows)})
                # #endregion
            except Exception as append_err:
                # #region agent log
                _debug_log("B", "sheets_writer.py:append_error", "append_rows failed", {"error": str(append_err), "error_type": type(append_err).__name__})
                # #endregion
                raise
        
        # 調整欄寬（可選，讓內容更易讀）
        try:
            # 設定較寬的欄位給長文字欄位
            worksheet.set_column_width(worksheet.col_values(1), 150)  # 抓取時間
            worksheet.set_column_width(worksheet.col_values(3), 300)  # 標題
            worksheet.set_column_width(worksheet.col_values(8), 500)  # AI 摘要
            worksheet.set_column_width(worksheet.col_values(9), 400)  # 關聯企業
            worksheet.set_column_width(worksheet.col_values(10), 400)  # 市場影響
            worksheet.set_column_width(worksheet.col_values(11), 400)  # 投資觀點
        except Exception:
            pass  # 欄寬設定失敗不影響主要功能
        
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
    sheet_id: str = SHEET_ID,
    news_type: str = "ai"
) -> bool:
    """
    寫入每日摘要到 Google Sheet
    
    Args:
        processed_articles: 經過 LLM 處理的文章（有摘要和評分）
        all_filtered_articles: 所有過濾後的文章
        sheet_id: Google Sheet ID
        news_type: 新聞類型
        
    Returns:
        True 如果寫入成功
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)
        
        # 取得今天的日期與類型作為工作表名稱
        today = datetime.now().strftime("%Y-%m-%d")
        type_name = NEWS_TYPE_NAMES.get(news_type, news_type)
        worksheet_name = f"Daily_{today}_{type_name}"
        
        # 建立或取得工作表
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet.clear()  # 清除當天的舊資料
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=500, cols=12)
        
        # 寫入標題
        headers = [
            "抓取時間",
            "類型",
            "標題",
            "URL",
            "來源",
            "評分",
            "分類",
            "AI 摘要",
            "關聯企業",
            "市場影響",
            "投資觀點",
            "發布時間"
        ]
        worksheet.append_row(headers)
        worksheet.freeze(rows=1)
        
        # 準備資料
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        type_display = NEWS_TYPE_NAMES.get(news_type, news_type)
        rows = []
        
        # 建立已處理文章的 URL 集合
        processed_urls = {a.get("url") for a in processed_articles}
        
        # 先寫入已處理的文章
        for article in processed_articles:
            row = [
                current_time,
                type_display,
                article.get("title", ""),
                article.get("url", ""),
                article.get("source", ""),
                str(article.get("score", "")),
                article.get("category", ""),
                article.get("ai_summary", ""),
                article.get("related_companies", ""),
                article.get("market_impact", ""),
                article.get("investment_insight", ""),
                article.get("published", "")
            ]
            rows.append(row)
        
        # 再寫入未處理的文章
        for article in all_filtered_articles:
            if article.get("url") not in processed_urls:
                row = [
                    current_time,
                    type_display,
                    article.get("title", ""),
                    article.get("url", ""),
                    article.get("source", ""),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
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
