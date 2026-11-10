#!/usr/bin/env python3
"""
Ninja_Stock - 台股資料手動/批次同步腳本
支援全台股清單、日K線行情、三大法人買賣超、融資融券籌碼

使用範例:
  # 1. 僅同步台股上市上櫃股票清單
  python3 scripts/sync_data.py --action stocks

  # 2. 同步預設核心股票 (0050, 2330, 2317 等) 最近 5 天行情與籌碼
  python3 scripts/sync_data.py --action bundle --source core --days 5

  # 3. 同步自選股清單 (watchlist) 最近 10 天數據
  python3 scripts/sync_data.py --action bundle --source watchlist --days 10

  # 4. 同步指定個股特定日期區間
  python3 scripts/sync_data.py --action bundle --stocks 2330,2454,0050 --start-date 2026-11-01 --end-date 2026-11-09

  # 5. 一鍵完整同步 (更新股票清單 + 核心股最近 5 天行情與籌碼)
  python3 scripts/sync_data.py --action all
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 加入專案路徑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.db.repository import SupabaseRepository
from src.fetchers.finmind import FinMindFetcher
from src.services.sync_service import SyncService


def parse_args():
    parser = argparse.ArgumentParser(description="Ninja_Stock 台股資料同步工具")

    parser.add_argument(
        "--action",
        choices=["all", "stocks", "bundle", "daily", "inst", "margin"],
        default="all",
        help="同步動作: stocks(股票清單), bundle(行情+法人+資券), daily(僅日K), inst(僅三大法人), margin(僅融資券), all(全套)",
    )
    parser.add_argument(
        "--source",
        choices=["core", "watchlist", "custom", "all_active"],
        default="core",
        help="個股清單來源: core(預設核心權值股), watchlist(自選清單), custom(自訂), all_active(所有上市櫃股票)",
    )
    parser.add_argument(
        "--stocks",
        type=str,
        default="",
        help="自訂股票代號 (逗號分隔，例如: 2330,2317,0050)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="",
        help="開始日期 (格式: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="",
        help="結束日期 (格式: YYYY-MM-DD，預設為今日)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="回溯天數 (當未指定 start-date 時自動計算，預設 5 天)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="每次 API 請求間隔秒數 (預設 0.2 秒以防被限流)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制同步個股數量 (用於測試或全市場抽樣)",
    )

    return parser.parse_args()


def resolve_stock_list(args, repo: SupabaseRepository) -> list[str]:
    """依據 source 決定欲同步的股票代號清單"""
    if args.stocks:
        stocks = [s.strip() for s in args.stocks.split(",") if s.strip()]
        return stocks

    if args.source == "watchlist":
        stocks = repo.get_watchlist_stock_ids()
        if not stocks:
            print("⚠️ 目前 watchlist (自選股) 表中沒有股票，將自動回退使用預設 core 核心股票！")
            return settings.CORE_STOCKS
        return stocks

    if args.source == "all_active":
        stocks = repo.get_active_stock_ids(limit=args.limit)
        if not stocks:
            print("⚠️ 目前資料庫中尚未建立股票清單，請先執行 `--action stocks` 同步上市櫃清單！")
            return settings.CORE_STOCKS
        return stocks

    # 預設: core 核心指標股
    stocks = settings.CORE_STOCKS
    if args.limit:
        stocks = stocks[: args.limit]
    return stocks


def resolve_date_range(args) -> tuple[str, str]:
    """計算起始與結束日期字串"""
    today = datetime.now().date()
    end_date = args.end_date if args.end_date else today.strftime("%Y-%m-%d")

    if args.start_date:
        start_date = args.start_date
    else:
        start_dt = today - timedelta(days=args.days)
        start_date = start_dt.strftime("%Y-%m-%d")

    return start_date, end_date


def main():
    args = parse_args()
    print("=" * 60)
    print("🥷📈 Ninja_Stock 資料同步任務啟動")
    print("=" * 60)

    repo = SupabaseRepository()
    fetcher = FinMindFetcher()
    service = SyncService(repo=repo, fetcher=fetcher, request_delay=args.delay)

    start_date, end_date = resolve_date_range(args)
    target_stocks = resolve_stock_list(args, repo)

    print(f"📌 設定參數:")
    print(f"  • 同步動作: {args.action}")
    print(f"  • 日期區間: {start_date} ~ {end_date}")
    print(f"  • 股票來源: {args.source} (共 {len(target_stocks)} 檔: {target_stocks[:5]}...)")
    print(f"  • 請求間隔: {args.delay} 秒")
    print("-" * 60)

    # 1. 執行股票基本清單同步
    if args.action in ["stocks", "all"]:
        service.sync_stocks_info()

    # 2. 執行行情與籌碼同步
    if args.action == "all" or args.action == "bundle":
        service.sync_stock_bundle(
            stock_ids=target_stocks, start_date=start_date, end_date=end_date
        )
    elif args.action == "daily":
        service.sync_daily_quotes(
            stock_ids=target_stocks, start_date=start_date, end_date=end_date
        )
    elif args.action == "inst":
        service.sync_institutional_investors(
            stock_ids=target_stocks, start_date=start_date, end_date=end_date
        )
    elif args.action == "margin":
        service.sync_margin_trading(
            stock_ids=target_stocks, start_date=start_date, end_date=end_date
        )

    print("\n" + "=" * 60)
    print("🎉 同步任務全數完成！詳細執行記錄可於 Supabase 的 `sync_logs` 查看。")
    print("=" * 60)


if __name__ == "__main__":
    main()
