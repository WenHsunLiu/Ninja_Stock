import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from src.config import settings
from src.db.repository import SupabaseRepository
from src.fetchers.finmind import FinMindFetcher

logger = logging.getLogger(__name__)


class SyncService:
    """台股資料同步服務核心，負責排程與批次資料的更新、日誌記錄與異常容錯"""

    def __init__(
        self,
        repo: Optional[SupabaseRepository] = None,
        fetcher: Optional[FinMindFetcher] = None,
        request_delay: float = 0.2,
    ):
        self.repo = repo or SupabaseRepository()
        self.fetcher = fetcher or FinMindFetcher()
        self.request_delay = request_delay

    def sync_stocks_info(self) -> int:
        """同步台股上市上櫃清單 (public.stocks)"""
        started_at = datetime.now(timezone.utc)
        print("🚀 [1/1] 開始同步全台股股票基本資料 (TaiwanStockInfo)...")
        try:
            records = self.fetcher.fetch_stock_info()
            if not records:
                print("  ⚠️ 未取得任何股票清單資料。")
                self.repo.log_sync(
                    dataset_name="stocks",
                    target_date=None,
                    status="SUCCESS",
                    records_count=0,
                    message="未取得任何股票清單資料",
                    started_at=started_at,
                )
                return 0

            saved = self.repo.batch_upsert(
                table="stocks",
                records=records,
                on_conflict="stock_id",
                chunk_size=500,
            )
            msg = f"成功同步全台股清單共 {saved} 檔股票"
            print(f"  ✅ {msg}！")
            self.repo.log_sync(
                dataset_name="stocks",
                target_date=None,
                status="SUCCESS",
                records_count=saved,
                message=msg,
                started_at=started_at,
            )
            return saved
        except Exception as e:
            err_msg = f"同步股票清單失敗: {e}"
            print(f"  ❌ {err_msg}")
            self.repo.log_sync(
                dataset_name="stocks",
                target_date=None,
                status="FAILED",
                records_count=0,
                message=err_msg,
                started_at=started_at,
            )
            raise e

    def sync_daily_quotes(
        self, stock_ids: List[str], start_date: str, end_date: str
    ) -> int:
        """同步多檔個股的每日盤後行情 (public.daily_quotes)"""
        started_at = datetime.now(timezone.utc)
        total_saved = 0
        total_stocks = len(stock_ids)
        print(f"\n📊 開始同步日 K 行情 (區間: {start_date} ~ {end_date})，共 {total_stocks} 檔...")

        for idx, sid in enumerate(stock_ids, 1):
            try:
                records = self.fetcher.fetch_daily_quotes(
                    stock_id=sid, start_date=start_date, end_date=end_date
                )
                if records:
                    saved = self.repo.batch_upsert(
                        table="daily_quotes",
                        records=records,
                        on_conflict="stock_id,date",
                    )
                    total_saved += saved
                    print(f"  [{idx}/{total_stocks}] 個股 {sid}: 成功寫入 {saved} 筆行情")
                else:
                    print(f"  [{idx}/{total_stocks}] 個股 {sid}: 無交易行情")

                time.sleep(self.request_delay)
            except Exception as e:
                print(f"  ⚠️ [{idx}/{total_stocks}] 個股 {sid} 日行情處理失敗: {e}")

        self.repo.log_sync(
            dataset_name="daily_quotes",
            target_date=end_date,
            status="SUCCESS",
            records_count=total_saved,
            message=f"同步 {total_stocks} 檔股票日K，共寫入 {total_saved} 筆",
            started_at=started_at,
        )
        return total_saved

    def sync_institutional_investors(
        self, stock_ids: List[str], start_date: str, end_date: str
    ) -> int:
        """同步多檔個股的三大法人買賣超 (public.institutional_investors)"""
        started_at = datetime.now(timezone.utc)
        total_saved = 0
        total_stocks = len(stock_ids)
        print(f"\n🏛️ 開始同步三大法人買賣超 (區間: {start_date} ~ {end_date})，共 {total_stocks} 檔...")

        for idx, sid in enumerate(stock_ids, 1):
            try:
                records = self.fetcher.fetch_institutional_investors(
                    stock_id=sid, start_date=start_date, end_date=end_date
                )
                if records:
                    saved = self.repo.batch_upsert(
                        table="institutional_investors",
                        records=records,
                        on_conflict="stock_id,date,investor_type",
                    )
                    total_saved += saved
                    print(f"  [{idx}/{total_stocks}] 個股 {sid}: 成功寫入 {saved} 筆法人數據")
                else:
                    print(f"  [{idx}/{total_stocks}] 個股 {sid}: 無三大法人數據")

                time.sleep(self.request_delay)
            except Exception as e:
                print(f"  ⚠️ [{idx}/{total_stocks}] 個股 {sid} 三大法人處理失敗: {e}")

        self.repo.log_sync(
            dataset_name="institutional_investors",
            target_date=end_date,
            status="SUCCESS",
            records_count=total_saved,
            message=f"同步 {total_stocks} 檔股票三大法人，共寫入 {total_saved} 筆",
            started_at=started_at,
        )
        return total_saved

    def sync_margin_trading(
        self, stock_ids: List[str], start_date: str, end_date: str
    ) -> int:
        """同步多檔個股的融資融券 (public.margin_trading)"""
        started_at = datetime.now(timezone.utc)
        total_saved = 0
        total_stocks = len(stock_ids)
        print(f"\n💳 開始同步融資融券籌碼 (區間: {start_date} ~ {end_date})，共 {total_stocks} 檔...")

        for idx, sid in enumerate(stock_ids, 1):
            try:
                records = self.fetcher.fetch_margin_trading(
                    stock_id=sid, start_date=start_date, end_date=end_date
                )
                if records:
                    saved = self.repo.batch_upsert(
                        table="margin_trading",
                        records=records,
                        on_conflict="stock_id,date",
                    )
                    total_saved += saved
                    print(f"  [{idx}/{total_stocks}] 個股 {sid}: 成功寫入 {saved} 筆融資融券籌碼")
                else:
                    print(f"  [{idx}/{total_stocks}] 個股 {sid}: 無信用交易數據")

                time.sleep(self.request_delay)
            except Exception as e:
                print(f"  ⚠️ [{idx}/{total_stocks}] 個股 {sid} 融資券處理失敗: {e}")

        self.repo.log_sync(
            dataset_name="margin_trading",
            target_date=end_date,
            status="SUCCESS",
            records_count=total_saved,
            message=f"同步 {total_stocks} 檔股票融資券，共寫入 {total_saved} 筆",
            started_at=started_at,
        )
        return total_saved

    def _prepare_stock_references(self, stock_ids: List[str]) -> tuple[List[str], List[str]]:
        """補齊行情外鍵所需的基本資料，回傳可同步與無法識別的標的。"""
        stock_ids = list(dict.fromkeys(stock_ids))
        existing = self.repo.get_existing_stock_ids(stock_ids)
        missing = set(stock_ids) - existing
        if missing:
            records = {
                record["stock_id"]: record
                for record in self.fetcher.fetch_stock_info()
                if record["stock_id"] in missing
            }
            if records:
                saved = self.repo.batch_upsert(
                    table="stocks",
                    records=list(records.values()),
                    on_conflict="stock_id",
                    ignore_duplicates=True,
                )
                existing.update(records)
                print(f"  股票基本資料補登 {saved} 檔。")

        ready = [stock_id for stock_id in stock_ids if stock_id in existing]
        unresolved = [stock_id for stock_id in stock_ids if stock_id not in existing]
        return ready, unresolved

    def sync_stock_bundle(
        self, stock_ids: List[str], start_date: str, end_date: str
    ) -> Dict[str, int]:
        """單一循環同時同步日K、三大法人、融資券（減少股票遍歷次數）"""
        stock_ids, unresolved = self._prepare_stock_references(stock_ids)
        problems = []
        if unresolved:
            message = f"股票基本資料缺少對應標的：{', '.join(unresolved)}"
            logger.warning(message)
            problems.append(message)

        total_stocks = len(stock_ids)
        print(f"\n📦 整合同步個股數據 (日K + 三大法人 + 融資券)，共 {total_stocks} 檔 (區間: {start_date} ~ {end_date})...")

        datasets = (
            (
                "daily_quotes", "daily_quotes", "日K",
                self.fetcher.fetch_daily_quotes, "stock_id,date",
            ),
            (
                "institutional", "institutional_investors", "法人",
                self.fetcher.fetch_institutional_investors, "stock_id,date,investor_type",
            ),
            (
                "margin", "margin_trading", "資券",
                self.fetcher.fetch_margin_trading, "stock_id,date",
            ),
        )
        results = {"daily_quotes": 0, "institutional": 0, "margin": 0}
        failed_datasets = 0

        for idx, sid in enumerate(stock_ids, 1):
            outcomes = []
            for dataset, table, label, fetch, on_conflict in datasets:
                try:
                    records = fetch(sid, start_date, end_date)
                    saved = self.repo.batch_upsert(table, records, on_conflict) if records else 0
                    results[dataset] += saved
                    outcomes.append(f"{label}：寫入 {saved} 筆")
                except Exception as error:
                    failed_datasets += 1
                    logger.warning("%s %s錯誤: %s", sid, label, error)
                    outcomes.append(f"{label}：失敗")
                time.sleep(self.request_delay)
            print(f"  [{idx}/{total_stocks}] {sid}: {', '.join(outcomes)}")

        if failed_datasets:
            problems.append(f"{failed_datasets} 個標的資料集同步失敗")
        if problems:
            raise RuntimeError(f"行情同步未完成：{'，'.join(problems)}")
        return results
