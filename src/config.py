"""
設定載入模組
負責從 .env 和 config.yaml 載入所有設定
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
    
    def __init__(self, config_path: str | None = None):
        """
        初始化設定
        
        Args:
            config_path: config.yaml 的路徑，預設為專案根目錄
        """
        if config_path is None:
            # 預設路徑：專案根目錄的 config.yaml
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self._config_path = Path(config_path)
        self._yaml_config: dict[str, Any] = {}
        
        self._load_yaml_config()
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
    def feeds(self) -> list[dict[str, Any]]:
        """取得啟用的 RSS feed 列表"""
        all_feeds = self._yaml_config.get("feeds", [])
        # 只回傳 enabled: true 的 feeds
        return [f for f in all_feeds if f.get("enabled", True)]
    
    @property
    def filters(self) -> dict[str, Any]:
        """取得過濾設定"""
        return self._yaml_config.get("filters", {
            "required_keywords": ["AI", "machine learning", "LLM"],
            "blocked_keywords": ["sponsored", "advertisement"]
        })
    
    @property
    def digest(self) -> dict[str, Any]:
        """取得摘要設定"""
        return self._yaml_config.get("digest", {
            "max_articles": 10,
            "min_score": 6,
            "articles_per_feed": 15,
            "max_articles_to_process": 50
        })
    
    @property
    def llm(self) -> dict[str, Any]:
        """取得 LLM 設定"""
        return self._yaml_config.get("llm", {
            "model": "gpt-4o-mini",
            "max_tokens": 300,
            "temperature": 0.3,
            "timeout": 30
        })
    
    @property
    def slack(self) -> dict[str, Any]:
        """取得 Slack 設定"""
        return self._yaml_config.get("slack", {
            "title": "📰 AI 新聞摘要",
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


def get_config() -> Config:
    """取得設定實例（單例模式）"""
    global _config
    if _config is None:
        _config = Config()
    return _config
