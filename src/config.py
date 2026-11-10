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

    # 預設核心追蹤股票清單 (台灣重要權值股與高人氣 ETF)
    CORE_STOCKS: list[str] = [
        "0050",   # 元大台灣50
        "0056",   # 元大高股息
        "00878",  # 國泰永續高股息
        "00919",  # 群益台灣精選高息
        "00929",  # 復華台灣科技優息
        "2330",   # 台積電
        "2317",   # 鴻海
        "2454",   # 聯發科
        "2308",   # 台達電
        "2382",   # 廣達
        "2412",   # 中華電
        "2881",   # 富邦金
        "2882",   # 國泰金
        "2603",   # 長榮
        "3711",   # 日月光投控
        "2891",   # 中信金
        "2357",   # 華碩
        "3008",   # 大立光
        "2886",   # 兆豐金
        "2303",   # 聯電
    ]

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
