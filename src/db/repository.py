import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.db.client import get_market_sync_client

logger = logging.getLogger(__name__)


class SupabaseRepository:
    """Supabase 資料庫操作封裝層，提供分批寫入、查詢與同步記錄"""

    def __init__(self):
        self.client = get_market_sync_client()

    def batch_upsert(
        self,
        table: str,
        records: List[Dict[str, Any]],
        on_conflict: str,
        chunk_size: int = 500,
        *,
        ignore_duplicates: bool = False,
    ) -> int:
        """分批將資料寫入指定資料表 (若主鍵衝突則更新)

        :param table: 資料表名稱 (如 'stocks', 'daily_quotes')
        :param records: 欲寫入的字典列表
        :param on_conflict: 主鍵或唯一鍵欄位名稱 (多欄位以逗號相隔，如 'stock_id,date')
        :param chunk_size: 每批次最大寫入筆數 (預設 500 避免超出 PostgREST 限制)
        :param ignore_duplicates: 主鍵衝突時保留既有資料
        :return: 成功寫入/更新的總筆數
        """
        if not records:
            return 0

        total_saved = 0
        total_records = len(records)

        for i in range(0, total_records, chunk_size):
            chunk = records[i : i + chunk_size]
            try:
                res = (
                    self.client.table(table)
                    .upsert(
                        chunk, on_conflict=on_conflict, ignore_duplicates=ignore_duplicates
                    )
                    .execute()
                )
                returned_count = len(res.data or [])
                total_saved += returned_count if ignore_duplicates else returned_count or len(chunk)
            except Exception as e:
                logger.error(f"寫入資料表 [{table}] 發生錯誤 (批次 {i}~{i+len(chunk)}): {e}")
                raise e

        return total_saved

    def get_existing_stock_ids(self, stock_ids: List[str]) -> set[str]:
        """查詢指定標的是否已有基本資料，包含停用標的。"""
        existing = set()
        for start in range(0, len(stock_ids), 100):
            response = (
                self.client.table("stocks")
                .select("stock_id")
                .in_("stock_id", stock_ids[start : start + 100])
                .execute()
            )
            existing.update(row["stock_id"] for row in response.data or [])
        return existing

    def log_sync(
        self,
        dataset_name: str,
        target_date: Optional[str],
        status: str,
        records_count: int,
        message: str,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
    ) -> None:
        """寫入同步歷史紀錄到 sync_logs 資料表"""
        try:
            payload = {
                "dataset_name": dataset_name,
                "target_date": target_date,
                "status": status,
                "records_count": records_count,
                "message": message[:1000] if message else "",
                "started_at": started_at.isoformat(),
                "finished_at": (finished_at or datetime.now(timezone.utc)).isoformat(),
            }
            self.client.table("sync_logs").insert(payload, returning="minimal").execute()
        except Exception as e:
            logger.warning(f"寫入同步紀錄 sync_logs 失敗: {e}")

    def get_active_stock_ids(self, limit: Optional[int] = None) -> List[str]:
        """取得所有已儲存且處於交易中的股票代號"""
        query = (
            self.client.table("stocks")
            .select("stock_id")
            .eq("is_active", True)
            .order("stock_id")
        )
        if limit:
            query = query.limit(limit)

        res = query.execute()
        return [row["stock_id"] for row in (res.data or [])]

    def get_watchlist_stock_ids(self) -> List[str]:
        """取得自選股清單中的股票代號"""
        res = self.client.rpc("ninja_watchlist_symbols").execute()
        return [row["stock_id"] for row in (res.data or [])]
