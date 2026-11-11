-- ==========================================================
-- Ninja_Stock - Sprint 2: 庫存管理與歷史收益資料庫結構 (Supabase DDL)
-- 包含：在手庫存 (holdings)、歷史交易紀錄 (transactions)、每日資產快照 (portfolio_snapshots)
-- ==========================================================

-- 1. 當前在手庫存表 (Current Portfolio Holdings)
CREATE TABLE IF NOT EXISTS public.holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id VARCHAR(10) NOT NULL REFERENCES public.stocks(stock_id) ON DELETE CASCADE,
    shares INTEGER NOT NULL CHECK (shares > 0),             -- 現有股數 (如 1000 股 = 1 張)
    cost_price NUMERIC(10, 2) NOT NULL,                     -- 買進平均成本價
    stop_loss_price NUMERIC(10, 2),                         -- 自訂停損警示價 (建議為成本價 -7%~-10%)
    take_profit_price NUMERIC(10, 2),                       -- 自訂停利警示價
    notes TEXT,                                             -- 個人投資筆記或策略備忘
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    CONSTRAINT uq_holdings_stock UNIQUE (stock_id)
);

COMMENT ON TABLE public.holdings IS '個人台股投資在手庫存持股明細';

-- 2. 歷史買賣交易記錄表 (Trade Transactions & Realized PnL)
CREATE TABLE IF NOT EXISTS public.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id VARCHAR(10) NOT NULL REFERENCES public.stocks(stock_id) ON DELETE CASCADE,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')), -- 交易動作 ('BUY' 買進 / 'SELL' 賣出)
    transacted_at DATE NOT NULL,                            -- 成交日期
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),        -- 成交單價
    shares INTEGER NOT NULL CHECK (shares > 0),             -- 成交股數
    fee NUMERIC(10, 2) DEFAULT 0,                           -- 券商手續費 (台股表定 0.1425%，依折數計算)
    tax NUMERIC(10, 2) DEFAULT 0,                           -- 證券交易稅 (賣出時為 0.3%)
    total_amount NUMERIC(12, 2) NOT NULL,                   -- 總結算金額 (買進為 成本+手續費；賣出為 市值-手續費-證交稅)
    realized_pnl NUMERIC(12, 2) DEFAULT 0,                  -- 已實現損益 (僅賣出 SELL 時計算，買進為 0)
    realized_roi NUMERIC(6, 2) DEFAULT 0,                   -- 已實現報酬率 %
    notes TEXT,                                             -- 備註 (例如「破月線停損」、「獲利了結」)
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

COMMENT ON TABLE public.transactions IS '歷史交易紀錄與已實現收益帳本';

-- 3. 每日資產總值與收益快照表 (Daily Portfolio Snapshots)
CREATE TABLE IF NOT EXISTS public.portfolio_snapshots (
    date DATE PRIMARY KEY,                                  -- 結算日期
    total_market_value NUMERIC(14, 2) NOT NULL,             -- 當日總持股市值
    total_cost NUMERIC(14, 2) NOT NULL,                     -- 當日總持有成本
    unrealized_pnl NUMERIC(14, 2) NOT NULL,                 -- 未實現總損益
    unrealized_roi NUMERIC(6, 2) NOT NULL,                  -- 未實現報酬率 %
    realized_pnl_cum NUMERIC(14, 2) DEFAULT 0,              -- 歷史累計已實現損益
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

COMMENT ON TABLE public.portfolio_snapshots IS '每日收盤後資產總值與未實現/已實現收益走勢紀錄';

-- ==========================================================
-- 效能索引
-- ==========================================================
CREATE INDEX IF NOT EXISTS idx_transactions_stock ON public.transactions(stock_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON public.transactions(transacted_at DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_stock ON public.holdings(stock_id);

-- ==========================================================
-- RLS 安全存取政策
-- ==========================================================
ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read on holdings" ON public.holdings FOR SELECT USING (true);
CREATE POLICY "Allow full access for service role on holdings" ON public.holdings FOR ALL USING (true);

CREATE POLICY "Allow public read on transactions" ON public.transactions FOR SELECT USING (true);
CREATE POLICY "Allow full access for service role on transactions" ON public.transactions FOR ALL USING (true);

CREATE POLICY "Allow public read on portfolio_snapshots" ON public.portfolio_snapshots FOR SELECT USING (true);
CREATE POLICY "Allow full access for service role on portfolio_snapshots" ON public.portfolio_snapshots FOR ALL USING (true);
