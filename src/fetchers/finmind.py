import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from FinMind.data import DataLoader
from src.config import settings

logger = logging.getLogger(__name__)

INVESTOR_TYPE_MAP = {
    "Foreign_Investor": "外資及陸資",
    "Investment_Trust": "投信",
    "Dealer_self": "自營商(自行買賣)",
    "Dealer_Hedging": "自營商(避險)",
    "Foreign_Dealer_Self": "外資自營商",
}


class FinMindFetcher:
    """FinMind 台股公開資料擷取器，負責呼叫 API 並將資料正規化"""

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or settings.FINMIND_API_TOKEN
        self.loader = DataLoader()
        if self.api_token:
            try:
                self.loader.login_by_token(api_token=self.api_token)
                logger.info("已成功登入 FinMind API Token")
            except Exception as e:
                logger.warning(f"FinMind Token 登入失敗: {e}，將使用免登入公共模式")

    @staticmethod
    def _clean_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """將 DataFrame 中的 NaN / NaT 轉為 None，並轉為字典列表"""
        if df.empty:
            return []
        cleaned_df = df.replace({np.nan: None})
        return cleaned_df.to_dict(orient="records")

    def fetch_stock_info(self) -> List[Dict[str, Any]]:
        """擷取全台股上市上櫃股票清單"""
        try:
            df = self.loader.taiwan_stock_info()
            if df.empty:
                return []

            # 篩選上市 (twse) 與上櫃 (tpex) 股票
            valid_types = ["twse", "tpex"]
            filtered = df[df["type"].isin(valid_types)].copy()

            # 欄位映射與清理
            records = []
            for _, row in filtered.iterrows():
                stock_id = str(row["stock_id"]).strip()
                stock_name = str(row["stock_name"]).strip()
                market_type = str(row["type"]).strip().lower()
                industry = row.get("industry_category")
                industry_category = str(industry).strip() if pd.notnull(industry) else None

                date_val = row.get("date")
                listing_date = str(date_val).strip() if pd.notnull(date_val) and str(date_val) != "None" else None

                records.append({
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "market_type": market_type,
                    "industry_category": industry_category,
                    "listing_date": listing_date,
                    "is_active": True,
                })

            return records
        except Exception as e:
            logger.error(f"擷取股票清單 (TaiwanStockInfo) 失敗: {e}")
            raise e

    def fetch_daily_quotes(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """擷取指定個股的日 K 行情 (開高低收、成交量值)"""
        try:
            df = self.loader.taiwan_stock_daily(
                stock_id=stock_id, start_date=start_date, end_date=end_date
            )
            if df.empty:
                return []

            records = []
            for _, row in df.iterrows():
                close_price = float(row["close"]) if pd.notnull(row["close"]) else None
                spread = float(row["spread"]) if pd.notnull(row["spread"]) else 0.0

                # 計算漲跌幅 (%) = spread / (close - spread) * 100
                change_percent = None
                if close_price is not None:
                    prev_close = close_price - spread
                    if prev_close > 0:
                        change_percent = round((spread / prev_close) * 100, 2)
                    else:
                        change_percent = 0.0

                records.append({
                    "stock_id": str(row["stock_id"]),
                    "date": str(row["date"]),
                    "open": float(row["open"]) if pd.notnull(row["open"]) else None,
                    "high": float(row["max"]) if pd.notnull(row["max"]) else None,
                    "low": float(row["min"]) if pd.notnull(row["min"]) else None,
                    "close": close_price,
                    "spread": spread,
                    "change_percent": change_percent,
                    "volume": int(row["Trading_Volume"]) if pd.notnull(row["Trading_Volume"]) else 0,
                    "turnover": int(row["Trading_money"]) if pd.notnull(row["Trading_money"]) else 0,
                    "transaction_count": int(row["Trading_turnover"]) if pd.notnull(row["Trading_turnover"]) else 0,
                })

            return records
        except Exception as e:
            logger.error(f"擷取個股 [{stock_id}] 日行情失敗: {e}")
            raise e

    def fetch_institutional_investors(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """擷取三大法人每日買賣超數據"""
        try:
            df = self.loader.taiwan_stock_institutional_investors(
                stock_id=stock_id, start_date=start_date, end_date=end_date
            )
            if df.empty:
                return []

            records = []
            for _, row in df.iterrows():
                raw_type = str(row["name"]).strip()
                investor_type = INVESTOR_TYPE_MAP.get(raw_type, raw_type)

                records.append({
                    "stock_id": str(row["stock_id"]),
                    "date": str(row["date"]),
                    "investor_type": investor_type,
                    "buy_volume": int(row["buy"]) if pd.notnull(row["buy"]) else 0,
                    "sell_volume": int(row["sell"]) if pd.notnull(row["sell"]) else 0,
                    # 注意: net_volume 在資料庫為自動計算欄位 (STORED)，此處不可傳入
                })

            return records
        except Exception as e:
            logger.error(f"擷取個股 [{stock_id}] 三大法人失敗: {e}")
            raise e

    def fetch_margin_trading(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """擷取融資融券 (信用交易) 每日籌碼餘額"""
        try:
            df = self.loader.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_id, start_date=start_date, end_date=end_date
            )
            if df.empty:
                return []

            records = []
            for _, row in df.iterrows():
                records.append({
                    "stock_id": str(row["stock_id"]),
                    "date": str(row["date"]),
                    "margin_buy": int(row["MarginPurchaseBuy"]) if pd.notnull(row["MarginPurchaseBuy"]) else 0,
                    "margin_sell": int(row["MarginPurchaseSell"]) if pd.notnull(row["MarginPurchaseSell"]) else 0,
                    "margin_repay": int(row["MarginPurchaseCashRepayment"]) if pd.notnull(row["MarginPurchaseCashRepayment"]) else 0,
                    "margin_balance": int(row["MarginPurchaseTodayBalance"]) if pd.notnull(row["MarginPurchaseTodayBalance"]) else 0,
                    "short_buy": int(row["ShortSaleBuy"]) if pd.notnull(row["ShortSaleBuy"]) else 0,
                    "short_sell": int(row["ShortSaleSell"]) if pd.notnull(row["ShortSaleSell"]) else 0,
                    "short_repay": int(row["ShortSaleCashRepayment"]) if pd.notnull(row["ShortSaleCashRepayment"]) else 0,
                    "short_balance": int(row["ShortSaleTodayBalance"]) if pd.notnull(row["ShortSaleTodayBalance"]) else 0,
                })

            return records
        except Exception as e:
            logger.error(f"擷取個股 [{stock_id}] 融資融券失敗: {e}")
            raise e
