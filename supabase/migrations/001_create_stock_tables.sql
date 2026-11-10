-- ==========================================================
-- Ninja_Stock - Sprint 1: 核心台股資料庫結構 (Supabase DDL)
-- 整合 FinMind 台股資料集：基本資料、日K、三大法人、融資融券、自選股
-- ==========================================================

-- 1. 股票基本資料表 (Taiwan Stock Info)
CREATE TABLE IF NOT EXISTS public.stocks (
    stock_id VARCHAR(10) PRIMARY KEY,                  -- 股票代碼 (如: '2330', '0050', '6547')
    stock_name VARCHAR(50) NOT NULL,                   -- 股票名稱 (如: '台積電')
    market_type VARCHAR(10) NOT NULL,                  -- 市場別 ('twse' 上市, 'tpex' 上櫃)
    industry_category VARCHAR(50),                     -- 產業分類 (如: '半導體業', '金融保險')
    listing_date DATE,                                 -- 上市/上櫃日期
    is_active BOOLEAN DEFAULT TRUE,                    -- 是否仍在交易中
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

COMMENT ON TABLE public.stocks IS '台股上市上櫃股票基本清單';

-- 2. 每日盤後行情表 (Taiwan Stock Daily Quotes)
CREATE TABLE IF NOT EXISTS public.daily_quotes (
    stock_id VARCHAR(10) NOT NULL REFERENCES public.stocks(stock_id) ON DELETE CASCADE,
    date DATE NOT NULL,                                -- 交易日期
    open NUMERIC(10, 2),                               -- 開盤價
    high NUMERIC(10, 2),                               -- 最高價
    low NUMERIC(10, 2),                                -- 最低價
    close NUMERIC(10, 2),                              -- 收盤價
    spread NUMERIC(10, 2),                             -- 漲跌價差
    change_percent NUMERIC(6, 2),                      -- 漲跌幅 (%)
    volume BIGINT,                                     -- 成交股數 (Trading_Volume)
    turnover BIGINT,                                   -- 成交金額 (Trading_money)
    transaction_count INTEGER,                         -- 成交筆數 (Trading_turnover)
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    PRIMARY KEY (stock_id, date)
);

COMMENT ON TABLE public.daily_quotes IS '每日盤後行情 (開高低收、成交量值)';

-- 3. 三大法人買賣超 (Taiwan Stock Institutional Investors)
CREATE TABLE IF NOT EXISTS public.institutional_investors (
    stock_id VARCHAR(10) NOT NULL REFERENCES public.stocks(stock_id) ON DELETE CASCADE,
    date DATE NOT NULL,                                -- 交易日期
    investor_type VARCHAR(40) NOT NULL,                -- 外資及陸資 / 投信 / 自營商(自行買賣) / 自營商(避險)
    buy_volume BIGINT DEFAULT 0,                       -- 買進股數
    sell_volume BIGINT DEFAULT 0,                      -- 賣出股數
    net_volume BIGINT GENERATED ALWAYS AS (buy_volume - sell_volume) STORED, -- 買賣超差額
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    PRIMARY KEY (stock_id, date, investor_type)
);

COMMENT ON TABLE public.institutional_investors IS '三大法人每日買賣超數據';

-- 4. 融資融券籌碼表 (Margin Trading & Short Sale)
CREATE TABLE IF NOT EXISTS public.margin_trading (
    stock_id VARCHAR(10) NOT NULL REFERENCES public.stocks(stock_id) ON DELETE CASCADE,
    date DATE NOT NULL,                                -- 交易日期
    margin_buy BIGINT DEFAULT 0,                       -- 融資買進
    margin_sell BIGINT DEFAULT 0,                      -- 融資賣出
    margin_repay BIGINT DEFAULT 0,                     -- 融資現金償還
    margin_balance BIGINT DEFAULT 0,                   -- 融資今日餘額
    short_buy BIGINT DEFAULT 0,                        -- 融券買進 (回補)
    short_sell BIGINT DEFAULT 0,                       -- 融券賣出
    short_repay BIGINT DEFAULT 0,                      -- 融券現券償還
    short_balance BIGINT DEFAULT 0,                    -- 融券今日餘額
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    PRIMARY KEY (stock_id, date)
);

COMMENT ON TABLE public.margin_trading IS '信用交易 (融資融券) 每日籌碼餘額與異動';

-- 5. 自選股與監控清單 (Watchlist)
CREATE TABLE IF NOT EXISTS public.watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_name VARCHAR(50) DEFAULT '我的自選',         -- 群組名稱
    stock_id VARCHAR(10) NOT NULL REFERENCES public.stocks(stock_id) ON DELETE CASCADE,
    target_buy_price NUMERIC(10, 2),                   -- 預設觀察進場價
    target_sell_price NUMERIC(10, 2),                  -- 預設觀察出場價
    notes TEXT,                                        -- 個人備忘筆記
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    UNIQUE (group_name, stock_id)
);

COMMENT ON TABLE public.watchlist IS '跨裝置自選股與策略監控清單';

-- 6. 資料同步歷史紀錄 (Data Sync Logs)
CREATE TABLE IF NOT EXISTS public.sync_logs (
    id BIGSERIAL PRIMARY KEY,
    dataset_name VARCHAR(50) NOT NULL,                 -- 同步目標 ('stocks', 'daily_quotes', etc.)
    target_date DATE,                                  -- 數據日期
    status VARCHAR(20) NOT NULL,                       -- 'RUNNING', 'SUCCESS', 'FAILED'
    records_count INTEGER DEFAULT 0,                   -- 本次寫入筆數
    message TEXT,                                      -- 執行狀態訊息或錯誤資訊
    started_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    finished_at TIMESTAMPTZ
);

COMMENT ON TABLE public.sync_logs IS 'FinMind 資料擷取與排程執行記錄';

-- ==========================================================
-- 效能索引 (Performance Indexes)
-- ==========================================================
CREATE INDEX IF NOT EXISTS idx_daily_quotes_date ON public.daily_quotes(date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_quotes_stock ON public.daily_quotes(stock_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_institutional_date ON public.institutional_investors(date DESC);
CREATE INDEX IF NOT EXISTS idx_institutional_stock ON public.institutional_investors(stock_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_margin_date ON public.margin_trading(date DESC);
CREATE INDEX IF NOT EXISTS idx_margin_stock ON public.margin_trading(stock_id, date DESC);

-- ==========================================================
-- 啟用 Row Level Security (RLS) - 預設開放後端 Service Role & 讀取權限
-- ==========================================================
ALTER TABLE public.stocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.institutional_investors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.margin_trading ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_logs ENABLE ROW LEVEL SECURITY;

-- 建立允許公開讀取 (anon / authenticated 均可 SELECT，方便跨裝置讀取行情)
DROP POLICY IF EXISTS "Allow public read on stocks" ON public.stocks;
CREATE POLICY "Allow public read on stocks" ON public.stocks FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public read on daily_quotes" ON public.daily_quotes;
CREATE POLICY "Allow public read on daily_quotes" ON public.daily_quotes FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public read on institutional_investors" ON public.institutional_investors;
CREATE POLICY "Allow public read on institutional_investors" ON public.institutional_investors FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public read on margin_trading" ON public.margin_trading;
CREATE POLICY "Allow public read on margin_trading" ON public.margin_trading FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public read on watchlist" ON public.watchlist;
CREATE POLICY "Allow public read on watchlist" ON public.watchlist FOR SELECT USING (true);

-- 允許已認證身分或後端 Service Role 完整操作
DROP POLICY IF EXISTS "Allow full access for service role on stocks" ON public.stocks;
CREATE POLICY "Allow full access for service role on stocks" ON public.stocks FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow full access for service role on daily_quotes" ON public.daily_quotes;
CREATE POLICY "Allow full access for service role on daily_quotes" ON public.daily_quotes FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow full access for service role on institutional_investors" ON public.institutional_investors;
CREATE POLICY "Allow full access for service role on institutional_investors" ON public.institutional_investors FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow full access for service role on margin_trading" ON public.margin_trading;
CREATE POLICY "Allow full access for service role on margin_trading" ON public.margin_trading FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow full access for service role on watchlist" ON public.watchlist;
CREATE POLICY "Allow full access for service role on watchlist" ON public.watchlist FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow full access for service role on sync_logs" ON public.sync_logs;
CREATE POLICY "Allow full access for service role on sync_logs" ON public.sync_logs FOR ALL USING (true);
