-- Run on an isolated database after migrations 001–004.
BEGIN;

INSERT INTO auth.users (id, email) VALUES
    ('f149c780-39f0-4ddf-aa2d-d00bde8b9751', 'owner@example.invalid'),
    ('f149c780-39f0-4ddf-aa2d-d00bde8b9752', 'sync@example.invalid'),
    ('f149c780-39f0-4ddf-aa2d-d00bde8b9753', 'other@example.invalid');
INSERT INTO ninja_stock_private.account_roles (user_id, access_role) VALUES
    ('f149c780-39f0-4ddf-aa2d-d00bde8b9751', 'owner'),
    ('f149c780-39f0-4ddf-aa2d-d00bde8b9752', 'market_sync');

INSERT INTO public.stocks (stock_id, stock_name, market_type) VALUES ('TEST', 'Fixture', 'twse');
INSERT INTO public.holdings (stock_id, shares, cost_price) VALUES ('TEST', 1, 100);
INSERT INTO public.transactions (stock_id, action, transacted_at, price, shares, total_amount)
VALUES ('TEST', 'BUY', '2026-01-01', 100, 1, 100);
INSERT INTO public.portfolio_snapshots (date, total_market_value, total_cost, unrealized_pnl, unrealized_roi)
VALUES ('2026-01-01', 100, 100, 0, 0);
INSERT INTO public.watchlist (stock_id, group_name, notes)
VALUES ('TEST', 'Fixture', 'Synthetic private note');

SET LOCAL ROLE anon;
DO $$
BEGIN
    BEGIN
        PERFORM * FROM public.holdings;
        RAISE EXCEPTION 'anon read holdings';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    BEGIN
        PERFORM public.ninja_stock_role();
        RAISE EXCEPTION 'anon resolved application role';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;
RESET ROLE;

SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claims = '{"sub":"f149c780-39f0-4ddf-aa2d-d00bde8b9753","role":"authenticated","user_metadata":{"access_role":"owner"}}';
DO $$
BEGIN
    ASSERT public.ninja_stock_role() IS NULL;
    ASSERT NOT EXISTS (SELECT FROM public.holdings);
    ASSERT NOT EXISTS (SELECT FROM public.transactions);
    ASSERT NOT EXISTS (SELECT FROM public.portfolio_snapshots);
    ASSERT NOT EXISTS (SELECT FROM public.watchlist);
    ASSERT NOT EXISTS (SELECT FROM public.ninja_watchlist_symbols());
    BEGIN
        INSERT INTO public.transactions (stock_id, action, transacted_at, price, shares, total_amount)
        VALUES ('TEST', 'BUY', '2026-01-01', 1, 1, 1);
        RAISE EXCEPTION 'unassigned account inserted an entry';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;

SET LOCAL request.jwt.claims = '{"sub":"f149c780-39f0-4ddf-aa2d-d00bde8b9751","role":"authenticated"}';
DO $$
BEGIN
    ASSERT public.ninja_stock_role() = 'owner';
    ASSERT EXISTS (SELECT FROM public.holdings WHERE stock_id = 'TEST');
    ASSERT EXISTS (SELECT FROM public.transactions WHERE stock_id = 'TEST');
    ASSERT EXISTS (SELECT FROM public.portfolio_snapshots WHERE date = '2026-01-01');
    ASSERT (SELECT notes FROM public.watchlist WHERE stock_id = 'TEST') = 'Synthetic private note';
    ASSERT EXISTS (SELECT FROM public.stocks WHERE stock_id = 'TEST');
    UPDATE public.holdings SET shares = 2 WHERE stock_id = 'TEST';
    ASSERT FOUND;
    BEGIN
        INSERT INTO public.daily_quotes (stock_id, date, close) VALUES ('TEST', '2026-01-01', 100);
        RAISE EXCEPTION 'owner inserted market data';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;

SET LOCAL request.jwt.claims = '{"sub":"f149c780-39f0-4ddf-aa2d-d00bde8b9752","role":"authenticated"}';
DO $$
BEGIN
    ASSERT public.ninja_stock_role() = 'market_sync';
    ASSERT NOT EXISTS (SELECT FROM public.holdings);
    ASSERT NOT EXISTS (SELECT FROM public.transactions);
    ASSERT NOT EXISTS (SELECT FROM public.portfolio_snapshots);
    ASSERT NOT EXISTS (SELECT FROM public.watchlist);
    ASSERT (SELECT stock_id FROM public.ninja_watchlist_symbols()) = 'TEST';
    INSERT INTO public.daily_quotes (stock_id, date, close) VALUES ('TEST', '2026-01-01', 100);
    INSERT INTO public.daily_quotes (stock_id, date, close) VALUES ('TEST', '2026-01-01', 105)
    ON CONFLICT (stock_id, date) DO UPDATE SET close = EXCLUDED.close;
    ASSERT (SELECT close FROM public.daily_quotes WHERE stock_id = 'TEST') = 105;
    INSERT INTO public.sync_logs (dataset_name, status) VALUES ('daily_quotes', 'SUCCESS');
    UPDATE public.holdings SET shares = 999 WHERE stock_id = 'TEST';
    ASSERT NOT FOUND;
    BEGIN
        DELETE FROM public.daily_quotes WHERE stock_id = 'TEST';
        RAISE EXCEPTION 'market sync deleted market data';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    BEGIN
        PERFORM * FROM ninja_stock_private.account_roles;
        RAISE EXCEPTION 'market sync read role mappings';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    BEGIN
        PERFORM * FROM public.sync_logs;
        RAISE EXCEPTION 'market sync read stored logs';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;
RESET ROLE;

SET LOCAL ROLE service_role;
DO $$
BEGIN
    BEGIN
        PERFORM * FROM public.holdings;
        RAISE EXCEPTION 'service role read holdings';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;
RESET ROLE;

ROLLBACK;
