from unittest.mock import Mock, call

import pytest

from scripts import sync_data
from src.services.sync_service import SyncService


def market_fetcher():
    fetcher = Mock()
    fetcher.fetch_stock_info.return_value = [
        {"stock_id": "2330", "stock_name": "目錄中的既有標的", "market_type": "twse"},
        {"stock_id": "0050", "stock_name": "缺少的 ETF", "market_type": "twse"},
        {"stock_id": "2454", "stock_name": "其他標的", "market_type": "twse"},
    ]

    def market_records(stock_id, start_date, end_date):
        return [{"stock_id": stock_id, "date": end_date}]

    fetcher.fetch_daily_quotes.side_effect = market_records
    fetcher.fetch_institutional_investors.side_effect = market_records
    fetcher.fetch_margin_trading.side_effect = market_records
    return fetcher


def test_watchlist_fallback_inserts_missing_stock_before_market_writes(monkeypatch):
    repo = Mock()
    fetcher = market_fetcher()
    stocks = {"2330": {"stock_id": "2330", "stock_name": "保留的名稱", "is_active": False}}
    repo.get_watchlist_stock_ids.return_value = []
    repo.get_existing_stock_ids.side_effect = lambda ids: set(ids) & stocks.keys()

    def write_market(table, records, on_conflict, *, ignore_duplicates=False):
        if table == "stocks":
            assert ignore_duplicates
            assert on_conflict == "stock_id"
            for record in records:
                stocks.setdefault(record["stock_id"], record)
        elif any(record["stock_id"] not in stocks for record in records):
            raise RuntimeError("23503: missing stock reference")
        return len(records)

    repo.batch_upsert.side_effect = write_market
    monkeypatch.setattr(sync_data, "SupabaseRepository", lambda: repo)
    monkeypatch.setattr(sync_data, "FinMindFetcher", lambda: fetcher)
    monkeypatch.setattr(sync_data.settings, "CORE_STOCKS", ["2330", "0050"])
    monkeypatch.setattr(
        "sys.argv",
        ["sync_data.py", "--action", "bundle", "--source", "watchlist", "--days", "3", "--delay", "0"],
    )

    sync_data.main()
    sync_data.main()

    fetcher.fetch_stock_info.assert_called_once_with()
    assert repo.batch_upsert.call_args_list[0] == call(
        table="stocks",
        records=[{"stock_id": "0050", "stock_name": "缺少的 ETF", "market_type": "twse"}],
        on_conflict="stock_id",
        ignore_duplicates=True,
    )
    assert set(stocks) == {"2330", "0050"}
    assert stocks["2330"]["stock_name"] == "保留的名稱"
    assert stocks["2330"]["is_active"] is False
    assert repo.batch_upsert.call_count == 13


def test_bundle_reports_missing_catalog_stock_after_syncing_existing_stock():
    repo = Mock()
    repo.get_existing_stock_ids.return_value = {"2330"}
    repo.batch_upsert.return_value = 1
    fetcher = market_fetcher()
    service = SyncService(repo, fetcher, request_delay=0)

    with pytest.raises(RuntimeError, match="股票基本資料缺少對應標的：9999"):
        service.sync_stock_bundle(["2330", "9999"], "2026-11-20", "2026-11-23")

    assert repo.batch_upsert.call_count == 3
    fetcher.fetch_daily_quotes.assert_called_once_with("2330", "2026-11-20", "2026-11-23")


def test_bundle_reports_upsert_failure_after_other_datasets_finish():
    repo = Mock()
    repo.get_existing_stock_ids.return_value = {"2330"}
    repo.batch_upsert.side_effect = [RuntimeError("write failed"), 1, 1]
    fetcher = market_fetcher()
    service = SyncService(repo, fetcher, request_delay=0)

    with pytest.raises(RuntimeError, match="1 個標的資料集同步失敗"):
        service.sync_stock_bundle(["2330"], "2026-11-20", "2026-11-23")

    fetcher.fetch_stock_info.assert_not_called()
    assert repo.batch_upsert.call_count == 3
