import os
from pathlib import Path
from dotenv import load_dotenv

# 載入專案根目錄的 .env 檔案 (本地開發時使用)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_env_or_secret(key: str, default: str = "") -> str:
    """
    動態讀取環境變數或 Streamlit Secrets
    銜接規則:
    1. 優先嘗試讀取 Streamlit Secrets (當部署於 Streamlit Community Cloud 時)
    2. 其次讀取系統環境變數或 .env 檔案 (本地端或 GitHub Actions 時)
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


class Settings:
    """全域專案設定與環境變數管理 (動態屬性，確保跨本機、CI/CD 與雲端跨平台無縫銜接)"""

    @property
    def SUPABASE_URL(self) -> str:
        return _get_env_or_secret("SUPABASE_URL", "")

    @property
    def SUPABASE_KEY(self) -> str:
        return _get_env_or_secret("SUPABASE_KEY", "")

    @property
    def FINMIND_API_TOKEN(self) -> str:
        return _get_env_or_secret("FINMIND_API_TOKEN", "")

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

    def validate(self) -> list[str]:
        """驗證必要環境變數"""
        errors = []
        if not self.SUPABASE_URL:
            errors.append("未設定 SUPABASE_URL，請檢查 .env 或 Streamlit Secrets")
        if not self.SUPABASE_KEY:
            errors.append("未設定 SUPABASE_KEY，請檢查 .env 或 Streamlit Secrets")
        return errors


settings = Settings()
