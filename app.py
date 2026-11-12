import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

from src.services.portfolio_service import PortfolioService
from src.db.client import get_supabase_client

# 設置 Streamlit 頁面設定
st.set_page_config(
    page_title="Ninja_Stock 🥷 投資儀表板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 套用現代高質感深色主題 CSS
st.markdown(
    """
    <style>
    /* 主背景與字體風格 */
    .stApp {
        background-color: #0d1117;
        color: #f0f6fc;
    }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .metric-title {
        font-size: 13px;
        color: #8b949e;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        font-family: monospace;
    }
    .metric-sub {
        font-size: 12px;
        margin-top: 4px;
        font-weight: 600;
    }
    /* 台股色彩 */
    .color-up { color: #f85149; }
    .color-down { color: #3fb950; }
    .color-neutral { color: #8b949e; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_service():
    return PortfolioService()


service = get_service()
supabase = get_supabase_client()


# -------------------------------------------------------------
# 側邊欄：快速記帳與設定
# -------------------------------------------------------------
with st.sidebar:
    st.title("🥷 Ninja_Stock")
    st.caption("雲端跨裝置台股投資管理系統")

    st.markdown("---")
    st.subheader("📝 快速買賣記帳")

    with st.form("trade_form", clear_on_submit=True):
        action = st.radio("交易動作", ["買進 (BUY)", "賣出 (SELL)"], horizontal=True)
        stock_id = st.text_input("股票代號 (例如: 2330, 2317)", max_chars=10).strip()
        trans_date = st.date_input("成交日期", datetime.now().date())
        price = st.number_input("成交單價 (元)", min_value=0.1, value=100.0, step=0.5, format="%.2f")
        shares = st.number_input("成交股數 (1張 = 1000股)", min_value=1, value=1000, step=100)
        fee_discount = st.slider("券商手續費折數", min_value=0.1, max_value=1.0, value=0.6, step=0.05, help="常見電子下單折數約 6 折 (0.6) 或 28 折 (0.28)")
        notes = st.text_input("投資備註 (選填，如: 突破月線進場)")

        submitted = st.form_submit_button("確認送出並更新庫存", use_container_width=True)

        if submitted:
            if not stock_id:
                st.error("請輸入有效的股票代號！")
            else:
                date_str = trans_date.strftime("%Y-%m-%d")
                action_type = "BUY" if "買進" in action else "SELL"
                try:
                    if action_type == "BUY":
                        res = service.record_buy(
                            stock_id=stock_id,
                            transacted_at=date_str,
                            price=float(price),
                            shares=int(shares),
                            fee_discount=float(fee_discount),
                            notes=notes,
                        )
                        st.success(f"✅ 成功記錄買進 {stock_id} {shares} 股！庫存均價已自動更新。")
                    else:
                        res = service.record_sell(
                            stock_id=stock_id,
                            transacted_at=date_str,
                            price=float(price),
                            shares=int(shares),
                            fee_discount=float(fee_discount),
                            notes=notes,
                        )
                        pnl = res.get("realized_pnl", 0)
                        roi = res.get("realized_roi", 0)
                        st.success(f"✅ 成功記錄賣出 {stock_id}！已實現損益: NT$ {pnl:,.0f} ({roi:+.2f}%)")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 交易失敗: {str(e)}")

    st.markdown("---")
    st.info("💡 每天 17:30 GitHub Actions 會自動更新最新收盤價與三大法人籌碼。")


# -------------------------------------------------------------
# 主畫面：頂部 KPI 指標卡片 (版本 2 原型)
# -------------------------------------------------------------
st.title("🥷 Ninja_Stock 台股投資管理儀表板")
st.caption("雲端跨裝置即時總覽 • 自動技術分析 • 新手停損停利守護")

with st.spinner("⏳ 正在連線雲端資料庫載入最新持股與行情..."):
    try:
        kpis = service.get_portfolio_kpis()
    except Exception as e:
        st.info("💡 尚未在 Supabase 建立 Sprint 2 資料表，或目前暫無庫存資料。已為您切換為展示模式。")
        kpis = {
            "total_market_value": 0,
            "total_cost": 0,
            "total_unrealized_pnl": 0,
            "total_unrealized_roi": 0.0,
            "total_realized_pnl": 0,
            "win_rate": 0.0,
            "total_trades": 0,
            "holdings_count": 0,
        }

    try:
        holdings = service.get_holdings_summary()
    except Exception as e:
        holdings = []

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">總持股市值</div>
            <div class="metric-value">NT$ {kpis['total_market_value']:,}</div>
            <div class="metric-sub color-neutral">持有成本: NT$ {kpis['total_cost']:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    pnl = kpis['total_unrealized_pnl']
    roi = kpis['total_unrealized_roi']
    color_cls = "color-up" if pnl >= 0 else "color-down"
    sign = "+" if pnl > 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">今日未實現總損益</div>
            <div class="metric-value {color_cls}">{sign}NT$ {pnl:,}</div>
            <div class="metric-sub {color_cls}">{sign}{roi:.2f}% (含稅費預估)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    realized = kpis['total_realized_pnl']
    r_color = "color-up" if realized >= 0 else "color-down"
    r_sign = "+" if realized > 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">歷史累計已實現損益</div>
            <div class="metric-value {r_color}">{r_sign}NT$ {realized:,}</div>
            <div class="metric-sub color-neutral">已結算 {kpis['total_trades']} 筆交易</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    win_rate = kpis['win_rate']
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">交易勝率</div>
            <div class="metric-value">{win_rate:.1f}%</div>
            <div class="metric-sub color-neutral">在手持股數: {kpis['holdings_count']} 檔</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)


# -------------------------------------------------------------
# 當前在手庫存清單 (Holdings Table)
# -------------------------------------------------------------
st.subheader("📋 當前在手持股明細", anchor=False)

if not holdings:
    st.info("📌 目前尚無持股記錄！您可以在左側側邊欄輸入「買進記錄」建立第一筆投資。")
else:
    table_rows = []
    for h in holdings:
        diag_tags = " ".join([d["text"] for d in h["diagnostics"]])
        pnl_val = h["unrealized_pnl"]
        roi_val = h["unrealized_roi"]
        sign = "+" if pnl_val > 0 else ""

        table_rows.append({
            "代碼": h["stock_id"],
            "名稱": h["stock_name"],
            "產業": h["industry"],
            "股數": f"{h['shares']:,}",
            "買進均價": f"{h['cost_price']:.2f}",
            "最新市價": f"{h['current_price']:.2f}",
            "今日漲跌": f"{h['today_change']:+.2f} ({h['today_change_percent']:+.2f}%)",
            "未實現損益": f"{sign}NT$ {pnl_val:,} ({sign}{roi_val:.2f}%)",
            "停損警戒價": f"{h['stop_loss_price']:.2f}",
            "新手守護診斷": diag_tags,
        })

    df = pd.DataFrame(table_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

# -------------------------------------------------------------
# 個股深度技術線圖與籌碼分析
# -------------------------------------------------------------
st.subheader("📈 個股技術分析與籌碼診斷", anchor=False)

selected_stock = None
if holdings:
    stock_options = [f"{h['stock_id']} {h['stock_name']}" for h in holdings]
    selected_option = st.selectbox("選擇要分析的在手持股：", stock_options)
    selected_stock = selected_option.split()[0]
else:
    selected_stock = st.text_input("輸入股票代碼以查看K線 (如 2330)", value="2330")

if selected_stock:
    # 抓取最近 60 天歷史行情繪製 K 線
    try:
        q_res = (
            supabase.table("daily_quotes")
            .select("date, open, high, low, close, volume")
            .eq("stock_id", selected_stock)
            .order("date", desc=False)
            .limit(60)
            .execute()
        )
        quote_data = q_res.data or []
    except Exception as e:
        quote_data = []

    if quote_data:
        df_k = pd.DataFrame(quote_data)
        df_k["date"] = pd.to_datetime(df_k["date"])
        df_k["close"] = df_k["close"].astype(float)
        df_k["open"] = df_k["open"].astype(float)
        df_k["high"] = df_k["high"].astype(float)
        df_k["low"] = df_k["low"].astype(float)
        df_k["volume"] = df_k["volume"].astype(float)

        # 計算 5MA 與 20MA
        df_k["MA5"] = df_k["close"].rolling(5).mean()
        df_k["MA20"] = df_k["close"].rolling(20).mean()

        fig = go.Figure()

        # K線主圖 (台股慣例: 紅漲綠跌)
        fig.add_trace(
            go.Candlestick(
                x=df_k["date"],
                open=df_k["open"],
                high=df_k["high"],
                low=df_k["low"],
                close=df_k["close"],
                name="日K線",
                increasing_line_color="#f85149",
                decreasing_line_color="#3fb950",
            )
        )

        # 5MA 短期週線
        fig.add_trace(
            go.Scatter(
                x=df_k["date"],
                y=df_k["MA5"],
                line=dict(color="#e3b341", width=1.5),
                name="5日均線 (週線)",
            )
        )

        # 20MA 中期月線 (多空分水嶺)
        fig.add_trace(
            go.Scatter(
                x=df_k["date"],
                y=df_k["MA20"],
                line=dict(color="#58a6ff", width=2),
                name="20日均線 (月線/多空線)",
            )
        )

        fig.update_layout(
            template="plotly_dark",
            height=450,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_rangeslider_visible=False,
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"目前資料庫中尚無 {selected_stock} 的歷史日K數據。您可以執行數據同步或等待盤後排程自動收集！")

# -------------------------------------------------------------
# 歷史交易明細記錄 (Transactions History)
# -------------------------------------------------------------
with st.expander("📜 查看歷史完整交易紀錄與帳本"):
    try:
        history = service.get_transactions_history(limit=30)
    except Exception as e:
        history = []
    if not history:
        st.write("尚無歷史交易紀錄。")
    else:
        tx_rows = []
        for t in history:
            action_tag = "🟢 買進" if t["action"] == "BUY" else "🔴 賣出"
            tx_rows.append({
                "日期": t["transacted_at"],
                "動作": action_tag,
                "代碼": t["stock_id"],
                "單價": f"{float(t['price']):.2f}",
                "股數": f"{int(t['shares']):,}",
                "手續費": f"NT$ {float(t['fee']):.0f}",
                "證交稅": f"NT$ {float(t['tax']):.0f}",
                "總金額": f"NT$ {float(t['total_amount']):,.0f}",
                "已實現損益": f"NT$ {float(t['realized_pnl']):,.0f}" if t["action"] == "SELL" else "-",
                "備註": t.get("notes") or "",
            })
        st.dataframe(pd.DataFrame(tx_rows), use_container_width=True, hide_index=True)
