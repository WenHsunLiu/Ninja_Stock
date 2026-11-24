#!/usr/bin/env python3
"""
驗證 Supabase 連線與資料表建立狀態腳本
執行方式: python3 scripts/verify_connection.py
"""

import sys
from pathlib import Path

# 加入專案路徑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.db.client import get_market_sync_client

REQUIRED_TABLES = [
    "stocks",
    "daily_quotes",
    "institutional_investors",
    "margin_trading",
]


def check_setup():
    print("🔍 [1/2] 檢查環境變數設定...")
    errors = settings.validate()
    if errors:
        for err in errors:
            print(f"  ❌ {err}")
        print("\n請先依 .env.example 設定資料庫及行情排程帳號。")
        return False
    print("  ✅ 環境變數檢查通過！")

    print("\n🔍 [2/2] 測試 Supabase 資料庫連線與資料表狀態...")
    try:
        supabase = get_market_sync_client()
        missing_tables = []

        for table in REQUIRED_TABLES:
            try:
                # 測試讀取 1 筆資料確認資料表存在且可存取
                supabase.table(table).select("stock_id").limit(1).execute()
                print(f"  ✅ 資料表 [{table}] 存在且可存取")
            except Exception:
                missing_tables.append(table)
                print(f"  ❌ 資料表 [{table}] 存取失敗")

        supabase.rpc("ninja_watchlist_symbols").execute()
        if not missing_tables:
            print("\n行情資料表與自選股代號均可讀取。")
            return True
        else:
            print(f"\n⚠️ 尚有 {len(missing_tables)} 個資料表未建立或無法存取: {missing_tables}")
            print("請由管理者核對遷移與行情排程帳號的權限。")
            return False

    except Exception:
        print("  ❌ 無法驗證行情排程帳號或取得自選股代號")
        return False


if __name__ == "__main__":
    success = check_setup()
    sys.exit(0 if success else 1)
