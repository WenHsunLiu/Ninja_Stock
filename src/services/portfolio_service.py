from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import pandas as pd
from supabase import Client

from src.db.client import get_supabase_client


class PortfolioService:
    """個人持股庫存管理與損益結算服務 (專為台股交易規則量身打造)"""

    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase_client()
        # 台股表定手續費率 0.1425%，一般電子下單預設以 6 折 (0.6) 計，最低收費 20 元
        self.default_fee_rate = 0.001425
        self.default_fee_discount = 0.6
        self.tax_rate = 0.003  # 台股證券交易稅 0.3%

    def calculate_buy_fee(
        self, price: float, shares: int, discount: Optional[float] = None
    ) -> float:
        """計算買進手續費 (最低 20 元)"""
        disc = discount if discount is not None else self.default_fee_discount
        fee = round(price * shares * self.default_fee_rate * disc)
        return max(20.0, float(fee))

    def calculate_sell_fee_and_tax(
        self, price: float, shares: int, discount: Optional[float] = None
    ) -> tuple[float, float]:
        """計算賣出手續費與證交稅"""
        disc = discount if discount is not None else self.default_fee_discount
        fee = max(20.0, float(round(price * shares * self.default_fee_rate * disc)))
        tax = float(round(price * shares * self.tax_rate))
        return fee, tax

    # -------------------------------------------------------------
    # 庫存查詢與即時損益估算
    # -------------------------------------------------------------
    def get_holdings_summary(self) -> List[Dict[str, Any]]:
        """
        取得當前持股清單並整合最新報價、損益與新手技術/籌碼診斷
        """
        holdings_res = self.client.table("holdings").select("*").execute()
        holdings = holdings_res.data or []
        if not holdings:
            return []

        summary = []
        for h in holdings:
            stock_id = h["stock_id"]
            shares = int(h["shares"])
            cost_price = float(h["cost_price"])

            # 抓取該股票基本資料
            stock_info = (
                self.client.table("stocks")
                .select("stock_name, market_type, industry_category")
                .eq("stock_id", stock_id)
                .execute()
            )
            s_name = (
                stock_info.data[0]["stock_name"]
                if stock_info.data
                else stock_id
            )
            industry = (
                stock_info.data[0]["industry_category"]
                if stock_info.data
                else "未知"
            )

            # 抓取最近 25 個交易日歷史日K行情 (用以計算 MA20 月線與今日漲跌)
            quotes_res = (
                self.client.table("daily_quotes")
                .select("date, close, open, high, low, volume, spread, change_percent")
                .eq("stock_id", stock_id)
                .order("date", desc=True)
                .limit(25)
                .execute()
            )
            quotes = quotes_res.data or []

            current_price = cost_price
            today_change = 0.0
            today_change_percent = 0.0
            ma20 = None
            above_ma20 = True

            if quotes:
                current_price = float(quotes[0]["close"])
                today_change = float(quotes[0].get("spread") or 0.0)
                today_change_percent = float(quotes[0].get("change_percent") or 0.0)

                # 計算 20 日均線 (月線，新手最關鍵的多空分水嶺)
                closes = [float(q["close"]) for q in quotes if q.get("close")]
                if len(closes) >= 20:
                    ma20 = round(sum(closes[:20]) / 20.0, 2)
                    above_ma20 = current_price >= ma20

            # 抓取法人買賣超 (最近 5 天外資與投信動態)
            inst_res = (
                self.client.table("institutional_investors")
                .select("date, investor_type, net_volume")
                .eq("stock_id", stock_id)
                .order("date", desc=True)
                .limit(10)
                .execute()
            )
            inst_data = inst_res.data or []
            trust_consecutive_buy = self._check_trust_trend(inst_data)

            # 計算市值與損益
            market_value = current_price * shares
            cost_total = cost_price * shares
            # 預估賣出時的手續費與證券交易稅
            est_fee, est_tax = self.calculate_sell_fee_and_tax(
                current_price, shares
            )
            est_net_amount = market_value - est_fee - est_tax
            unrealized_pnl = est_net_amount - cost_total
            unrealized_roi = (
                (unrealized_pnl / cost_total * 100) if cost_total > 0 else 0.0
            )

            # 診斷警報 (專為新手設計的自動守護邏輯)
            diagnostics = []
            stop_loss = (
                float(h["stop_loss_price"]) if h.get("stop_loss_price") else round(cost_price * 0.92, 2)
            )

            if current_price <= stop_loss:
                diagnostics.append(
                    {"type": "danger", "text": f"🚨 觸及停損警戒線 ({stop_loss}元)"}
                )
            elif not above_ma20 and ma20:
                diagnostics.append(
                    {"type": "warning", "text": f"⚠️ 跌破月線 MA20 ({ma20}元)"}
                )
            else:
                diagnostics.append(
                    {"type": "success", "text": "✓ 站上月線 (偏多格局)"}
                )

            if trust_consecutive_buy >= 3:
                diagnostics.append(
                    {"type": "highlight", "text": f"🔥 投信連買 {trust_consecutive_buy} 天"}
                )

            summary.append(
                {
                    "holding_id": h["id"],
                    "stock_id": stock_id,
                    "stock_name": s_name,
                    "industry": industry,
                    "shares": shares,
                    "cost_price": cost_price,
                    "current_price": current_price,
                    "market_value": round(market_value),
                    "cost_total": round(cost_total),
                    "today_change": today_change,
                    "today_change_percent": today_change_percent,
                    "unrealized_pnl": round(unrealized_pnl),
                    "unrealized_roi": round(unrealized_roi, 2),
                    "stop_loss_price": stop_loss,
                    "take_profit_price": h.get("take_profit_price"),
                    "ma20": ma20,
                    "diagnostics": diagnostics,
                    "notes": h.get("notes") or "",
                }
            )

        return summary

    def _check_trust_trend(self, inst_data: list) -> int:
        """檢查投信近期連續買超天數"""
        trust_buys = [
            d for d in inst_data if d.get("investor_type") == "投信"
        ]
        consecutive = 0
        for item in trust_buys:
            if (item.get("net_volume") or 0) > 0:
                consecutive += 1
            else:
                break
        return consecutive

    # -------------------------------------------------------------
    # 總體帳戶 KPI 統計
    # -------------------------------------------------------------
    def get_portfolio_kpis(self) -> Dict[str, Any]:
        """計算頂部四大核心 KPI 指標"""
        holdings = self.get_holdings_summary()

        total_market_value = sum(h["market_value"] for h in holdings)
        total_cost = sum(h["cost_total"] for h in holdings)
        total_unrealized_pnl = sum(h["unrealized_pnl"] for h in holdings)
        total_unrealized_roi = (
            (total_unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
        )

        # 查詢歷史已實現損益
        tx_res = (
            self.client.table("transactions")
            .select("realized_pnl, action")
            .eq("action", "SELL")
            .execute()
        )
        sell_txs = tx_res.data or []
        total_realized_pnl = sum(
            float(t["realized_pnl"] or 0) for t in sell_txs
        )
        win_trades = sum(
            1 for t in sell_txs if float(t["realized_pnl"] or 0) > 0
        )
        total_trades = len(sell_txs)
        win_rate = (
            (win_trades / total_trades * 100) if total_trades > 0 else 0.0
        )

        return {
            "total_market_value": round(total_market_value),
            "total_cost": round(total_cost),
            "total_unrealized_pnl": round(total_unrealized_pnl),
            "total_unrealized_roi": round(total_unrealized_roi, 2),
            "total_realized_pnl": round(total_realized_pnl),
            "win_rate": round(win_rate, 1),
            "total_trades": total_trades,
            "holdings_count": len(holdings),
        }

    # -------------------------------------------------------------
    # 買進與賣出交易記帳邏輯
    # -------------------------------------------------------------
    def record_buy(
        self,
        stock_id: str,
        transacted_at: str,
        price: float,
        shares: int,
        fee_discount: float = 0.6,
        notes: str = "",
    ) -> Dict[str, Any]:
        """記錄買進交易，並自動更新持股庫存與均價"""
        fee = self.calculate_buy_fee(price, shares, fee_discount)
        total_amount = round(price * shares + fee, 2)

        # 1. 寫入交易流水帳
        tx_data = {
            "stock_id": stock_id,
            "action": "BUY",
            "transacted_at": transacted_at,
            "price": price,
            "shares": shares,
            "fee": fee,
            "tax": 0.0,
            "total_amount": total_amount,
            "realized_pnl": 0.0,
            "realized_roi": 0.0,
            "notes": notes,
        }
        self.client.table("transactions").insert(tx_data).execute()

        # 2. 更新或新增持股庫存 (加權平均成本)
        curr_holding = (
            self.client.table("holdings")
            .select("*")
            .eq("stock_id", stock_id)
            .execute()
        )
        if curr_holding.data:
            existing = curr_holding.data[0]
            old_shares = int(existing["shares"])
            old_cost = float(existing["cost_price"])
            new_shares = old_shares + shares
            # 加權平均成本
            new_avg_cost = round(
                (old_shares * old_cost + shares * price) / new_shares, 2
            )

            self.client.table("holdings").update(
                {
                    "shares": new_shares,
                    "cost_price": new_avg_cost,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("stock_id", stock_id).execute()
        else:
            # 新增一檔持股，預設停損價為買進成本 -8%
            default_stop_loss = round(price * 0.92, 2)
            self.client.table("holdings").insert(
                {
                    "stock_id": stock_id,
                    "shares": shares,
                    "cost_price": price,
                    "stop_loss_price": default_stop_loss,
                    "notes": notes,
                }
            ).execute()

        return {"status": "success", "action": "BUY", "stock_id": stock_id}

    def record_sell(
        self,
        stock_id: str,
        transacted_at: str,
        price: float,
        shares: int,
        fee_discount: float = 0.6,
        notes: str = "",
    ) -> Dict[str, Any]:
        """記錄賣出交易，計算已實現損益並相應減少或清空持股"""
        curr_holding = (
            self.client.table("holdings")
            .select("*")
            .eq("stock_id", stock_id)
            .execute()
        )
        if not curr_holding.data:
            raise ValueError(f"您目前並未持有 {stock_id}，無法進行賣出！")

        holding = curr_holding.data[0]
        curr_shares = int(holding["shares"])
        cost_price = float(holding["cost_price"])

        if shares > curr_shares:
            raise ValueError(
                f"賣出股數 ({shares}) 超過目前在庫持股數 ({curr_shares})！"
            )

        fee, tax = self.calculate_sell_fee_and_tax(price, shares, fee_discount)
        total_amount = round(price * shares - fee - tax, 2)

        # 計算這筆賣出的已實現損益
        sold_cost = shares * cost_price
        realized_pnl = round(total_amount - sold_cost, 2)
        realized_roi = (
            round((realized_pnl / sold_cost * 100), 2) if sold_cost > 0 else 0.0
        )

        # 1. 寫入交易明細
        tx_data = {
            "stock_id": stock_id,
            "action": "SELL",
            "transacted_at": transacted_at,
            "price": price,
            "shares": shares,
            "fee": fee,
            "tax": tax,
            "total_amount": total_amount,
            "realized_pnl": realized_pnl,
            "realized_roi": realized_roi,
            "notes": notes,
        }
        self.client.table("transactions").insert(tx_data).execute()

        # 2. 更新庫存股數
        rem_shares = curr_shares - shares
        if rem_shares <= 0:
            # 庫存已全數賣出，刪除持股
            self.client.table("holdings").delete().eq(
                "stock_id", stock_id
            ).execute()
        else:
            self.client.table("holdings").update(
                {
                    "shares": rem_shares,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("stock_id", stock_id).execute()

        return {
            "status": "success",
            "action": "SELL",
            "stock_id": stock_id,
            "realized_pnl": realized_pnl,
            "realized_roi": realized_roi,
        }

    def get_transactions_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """取得歷史買賣交易記錄"""
        res = (
            self.client.table("transactions")
            .select("*, stocks(stock_name)")
            .order("transacted_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
