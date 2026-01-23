"""
設定載入模組
負責從 .env 和 config.yaml 載入所有設定，支援多新聞類型
"""
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from loguru import logger

# 載入 .env 檔案
load_dotenv()


class Config:
    """應用程式設定類別"""
    
    # 從環境變數載入的機密設定
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __init__(self, config_path: str | None = None, news_type: str | None = None):
        """
        初始化設定
        
        Args:
            config_path: config.yaml 的路徑，預設為專案根目錄
            news_type: 新聞類型（ai/tw_stock/us_stock），預設從設定檔讀取
        """
        if config_path is None:
            # 預設路徑：專案根目錄的 config.yaml
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self._config_path = Path(config_path)
        self._yaml_config: dict[str, Any] = {}
        self._news_type: str = news_type or "ai"
        
        self._load_yaml_config()
        
        # 設定預設新聞類型
        if news_type is None:
            global_config = self._yaml_config.get("global", {})
            self._news_type = global_config.get("default_news_type", "ai")
        
        self._validate_config()
        self._setup_logging()
    
    def _load_yaml_config(self) -> None:
        """載入 YAML 設定檔"""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._yaml_config = yaml.safe_load(f) or {}
            logger.debug(f"已載入設定檔：{self._config_path}")
        except FileNotFoundError:
            logger.warning(f"找不到設定檔：{self._config_path}，使用預設值")
            self._yaml_config = {}
        except yaml.YAMLError as e:
            logger.error(f"設定檔格式錯誤：{e}")
            raise
    
    def _validate_config(self) -> None:
        """驗證必要設定是否存在"""
        errors = []
        
        if not self.SLACK_WEBHOOK_URL:
            errors.append("缺少 SLACK_WEBHOOK_URL 環境變數")
        
        if not self.OPENAI_API_KEY:
            errors.append("缺少 OPENAI_API_KEY 環境變數")
        
        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError("設定驗證失敗，請檢查 .env 檔案")
    
    def _setup_logging(self) -> None:
        """設定日誌"""
        log_config = self.logging
        logger.remove()  # 移除預設 handler
        logger.add(
            sink=lambda msg: print(msg, end=""),
            format=log_config.get("format", "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"),
            level=self.LOG_LEVEL,
            colorize=True
        )
    
    @property
    def news_type(self) -> str:
        """取得當前新聞類型"""
        return self._news_type
    
    @news_type.setter
    def news_type(self, value: str) -> None:
        """設定新聞類型"""
        available_types = self.available_news_types
        if value not in available_types:
            logger.warning(f"無效的新聞類型：{value}，使用預設值 'ai'")
            value = "ai"
        self._news_type = value
    
    @property
    def available_news_types(self) -> list[str]:
        """取得所有可用的新聞類型"""
        news_types = self._yaml_config.get("news_types", {})
        return list(news_types.keys())
    
    def get_news_type_config(self, news_type: str | None = None) -> dict[str, Any]:
        """取得指定新聞類型的完整設定"""
        if news_type is None:
            news_type = self._news_type
        
        news_types = self._yaml_config.get("news_types", {})
        return news_types.get(news_type, {})
    
    @property
    def news_type_name(self) -> str:
        """取得當前新聞類型的顯示名稱"""
        type_config = self.get_news_type_config()
        return type_config.get("name", self._news_type)
    
    @property
    def slack_title(self) -> str:
        """取得當前新聞類型的 Slack 標題"""
        type_config = self.get_news_type_config()
        return type_config.get("slack_title", f"📰 {self.news_type_name}")
    
    @property
    def feeds(self) -> list[dict[str, Any]]:
        """取得當前新聞類型啟用的 RSS feed 列表"""
        type_config = self.get_news_type_config()
        all_feeds = type_config.get("feeds", [])
        # 只回傳 enabled: true 的 feeds
        return [f for f in all_feeds if f.get("enabled", True)]
    
    @property
    def filters(self) -> dict[str, Any]:
        """取得當前新聞類型的過濾設定"""
        type_config = self.get_news_type_config()
        keywords = type_config.get("keywords", {})
        return {
            "required_keywords": keywords.get("required", []),
            "blocked_keywords": keywords.get("blocked", [])
        }
    
    @property
    def digest(self) -> dict[str, Any]:
        """取得摘要設定"""
        return self._yaml_config.get("digest", {
            "max_articles": 20,
            "min_score": 5,
            "articles_per_feed": 15,
            "process_all_filtered": True
        })
    
    @property
    def llm(self) -> dict[str, Any]:
        """取得 LLM 設定"""
        return self._yaml_config.get("llm", {
            "model": "gpt-4o-mini",
            "max_completion_tokens": 2000,
            "temperature": 0.3,
            "timeout": 60
        })
    
    @property
    def slack(self) -> dict[str, Any]:
        """取得 Slack 設定"""
        return self._yaml_config.get("slack", {
            "show_source": True,
            "show_score": True,
            "show_category": True
        })
    
    @property
    def logging(self) -> dict[str, Any]:
        """取得日誌設定"""
        return self._yaml_config.get("logging", {
            "level": "INFO",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
        })


# 建立全域設定實例（延遲初始化）
_config: Config | None = None


def get_config(news_type: str | None = None) -> Config:
    """
    取得設定實例
    
    Args:
        news_type: 新聞類型，如果提供則會更新設定
        
    Returns:
        Config 實例
    """
    global _config
    if _config is None:
        _config = Config(news_type=news_type)
    elif news_type is not None:
        _config.news_type = news_type
    return _config


def reset_config() -> None:
    """重置設定實例（用於測試或重新載入）"""
    global _config
    _config = None
