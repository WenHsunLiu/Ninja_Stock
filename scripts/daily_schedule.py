#!/usr/bin/env python3
"""
Ninja_Stock - 每日盤後自動化同步排程器
每日於台股盤後 (建議 17:00~19:30 之後) 自動同步當日收盤行情、三大法人買賣超、融資融券數據。

使用方式:
  # 立即執行今日盤後同步 (手動觸發)
  python3 scripts/daily_schedule.py --now

  # 啟動常駐背景監聽，每日 17:30 自動執行
  python3 scripts/daily_schedule.py --time 17:30
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 加入專案路徑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.db.repository import SupabaseRepository
from src.fetchers.finmind import FinMindFetcher
from src.services.sync_service import SyncService


def run_daily_sync():
    """執行單日盤後自動同步"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    print("\n" + "=" * 65)
    print(f"⏰ [盤後同步任務] 觸發時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    if weekday >= 5:
        print(f"ℹ️ 今日為週末 (星期 {weekday + 1})，非台股交易日。")
        # 仍可同步以防週五盤後缺漏，但提示使用者
        print("💡 正在執行近期資料完整性確認...")

    repo = SupabaseRepository()
    fetcher = FinMindFetcher()
    service = SyncService(repo=repo, fetcher=fetcher, request_delay=0.2)

    # 1. 取得同步清單: 自選股 + 核心指標股
    watchlist = repo.get_watchlist_stock_ids()
    target_stocks = list(dict.fromkeys(watchlist + settings.CORE_STOCKS))

    print(f"📋 今日目標股票共 {len(target_stocks)} 檔:")
    print(f"  • 自選清單 ({len(watchlist)} 檔): {watchlist}")
    print(f"  • 核心指標股 ({len(settings.CORE_STOCKS)} 檔)")

    # 2. 同步區間: 取最近 3 天 (確保國定假日或昨日資料完整)
    start_date = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = today_str

    try:
        results = service.sync_stock_bundle(
            stock_ids=target_stocks, start_date=start_date, end_date=end_date
        )
        print("\n✅ 今日盤後自動同步圓滿完成！")
        print(f"  • 日K線寫入: {results.get('daily_quotes', 0)} 筆")
        print(f"  • 三大法人寫入: {results.get('institutional', 0)} 筆")
        print(f"  • 融資融券寫入: {results.get('margin', 0)} 筆")
    except Exception as e:
        print(f"❌ 每日同步發生異常: {e}")


def main():
    parser = argparse.ArgumentParser(description="Ninja_Stock 盤後自動同步排程器")
    parser.add_argument("--now", action="store_true", help="立即執行一次同步")
    parser.add_argument(
        "--time",
        type=str,
        default="17:30",
        help="常駐排程每日觸發時間 (預設 17:30，格式 HH:MM)",
    )
    args = parser.parse_args()

    if args.now:
        run_daily_sync()
        return

    print("=" * 65)
    print("🥷📈 Ninja_Stock 盤後排程守護程序已啟動")
    print(f"⏳ 設定每日於 {args.time} 自動執行盤後資料擷取")
    print("💡 按 Ctrl + C 可隨時停止程式")
    print("=" * 65)

    last_run_date = ""

    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")

        # 每天只在指定時間執行一次
        if current_time == args.time and last_run_date != current_date:
            last_run_date = current_date
            run_daily_sync()

        time.sleep(30)


if __name__ == "__main__":
    main()
