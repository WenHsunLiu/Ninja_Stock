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

    def sync_stock_bundle(
        self, stock_ids: List[str], start_date: str, end_date: str
    ) -> Dict[str, int]:
        """單一循環同時同步日K、三大法人、融資券（減少股票遍歷次數）"""
        total_stocks = len(stock_ids)
        print(f"\n📦 整合同步個股數據 (日K + 三大法人 + 融資券)，共 {total_stocks} 檔 (區間: {start_date} ~ {end_date})...")

        results = {"daily_quotes": 0, "institutional": 0, "margin": 0}

        for idx, sid in enumerate(stock_ids, 1):
            # 1. 日K
            try:
                q_records = self.fetcher.fetch_daily_quotes(sid, start_date, end_date)
                if q_records:
                    results["daily_quotes"] += self.repo.batch_upsert(
                        "daily_quotes", q_records, "stock_id,date"
                    )
            except Exception as e:
                logger.warning(f"{sid} 日K錯誤: {e}")
            time.sleep(self.request_delay)

            # 2. 三大法人
            try:
                inst_records = self.fetcher.fetch_institutional_investors(
                    sid, start_date, end_date
                )
                if inst_records:
                    results["institutional"] += self.repo.batch_upsert(
                        "institutional_investors",
                        inst_records,
                        "stock_id,date,investor_type",
                    )
            except Exception as e:
                logger.warning(f"{sid} 三大法人錯誤: {e}")
            time.sleep(self.request_delay)

            # 3. 融資融券
            try:
                m_records = self.fetcher.fetch_margin_trading(sid, start_date, end_date)
                if m_records:
                    results["margin"] += self.repo.batch_upsert(
                        "margin_trading", m_records, "stock_id,date"
                    )
            except Exception as e:
                logger.warning(f"{sid} 融資券錯誤: {e}")
            time.sleep(self.request_delay)

            print(
                f"  [{idx}/{total_stocks}] {sid}: 完成同步 (日K: {len(q_records) if 'q_records' in locals() and q_records else 0} 筆, "
                f"法人: {len(inst_records) if 'inst_records' in locals() and inst_records else 0} 筆, "
                f"資券: {len(m_records) if 'm_records' in locals() and m_records else 0} 筆)"
            )

        return results
