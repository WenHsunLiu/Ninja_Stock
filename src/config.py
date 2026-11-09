import os
from pathlib import Path
from dotenv import load_dotenv

# 載入專案根目錄的 .env 檔案
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """全域專案設定與環境變數管理"""

    # Supabase 連線設定
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # FinMind API Token (免費註冊後取得，未設定則受限於免 token 速率限制)
    FINMIND_API_TOKEN: str = os.getenv("FINMIND_API_TOKEN", "")

    @classmethod
    def validate(cls) -> list[str]:
        """驗證必要環境變數"""
        errors = []
        if not cls.SUPABASE_URL:
            errors.append("未設定 SUPABASE_URL，請檢查 .env 檔案")
        if not cls.SUPABASE_KEY:
            errors.append("未設定 SUPABASE_KEY，請檢查 .env 檔案")
        return errors


settings = Settings()
