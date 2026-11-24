BEGIN;

SET LOCAL lock_timeout = '5s';

CREATE SCHEMA ninja_stock_private;
REVOKE ALL ON SCHEMA ninja_stock_private FROM PUBLIC, anon, authenticated, service_role;

CREATE TABLE ninja_stock_private.account_roles (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    access_role text UNIQUE NOT NULL CHECK (access_role IN ('owner', 'market_sync'))
);
REVOKE ALL ON TABLE ninja_stock_private.account_roles FROM PUBLIC, anon, authenticated, service_role;

CREATE FUNCTION public.ninja_stock_role()
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT access_role
    FROM ninja_stock_private.account_roles
    WHERE user_id = (SELECT auth.uid())
$$;
REVOKE ALL ON FUNCTION public.ninja_stock_role() FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.ninja_stock_role() TO authenticated;

DO $$
DECLARE
    protected_table text;
    existing_policy record;
BEGIN
    FOREACH protected_table IN ARRAY ARRAY[
        'holdings', 'transactions', 'portfolio_snapshots', 'watchlist',
        'stocks', 'daily_quotes', 'institutional_investors', 'margin_trading', 'sync_logs'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', protected_table);
        FOR existing_policy IN
            SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = protected_table
        LOOP
            EXECUTE format('DROP POLICY %I ON public.%I', existing_policy.policyname, protected_table);
        END LOOP;
        EXECUTE format(
            'REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role',
            protected_table
        );
    END LOOP;

    FOREACH protected_table IN ARRAY ARRAY['holdings', 'transactions', 'portfolio_snapshots', 'watchlist'] LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO authenticated', protected_table);
        EXECUTE format(
            'CREATE POLICY owner_access ON public.%I FOR ALL TO authenticated
             USING ((SELECT public.ninja_stock_role()) = %L)
             WITH CHECK ((SELECT public.ninja_stock_role()) = %L)',
            protected_table, 'owner', 'owner'
        );
    END LOOP;

    FOREACH protected_table IN ARRAY ARRAY['stocks', 'daily_quotes', 'institutional_investors', 'margin_trading'] LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE ON public.%I TO authenticated', protected_table);
        EXECUTE format(
            'CREATE POLICY market_read ON public.%I FOR SELECT TO authenticated
             USING ((SELECT public.ninja_stock_role()) IN (%L, %L))',
            protected_table, 'owner', 'market_sync'
        );
        EXECUTE format(
            'CREATE POLICY market_insert ON public.%I FOR INSERT TO authenticated
             WITH CHECK ((SELECT public.ninja_stock_role()) = %L)',
            protected_table, 'market_sync'
        );
        EXECUTE format(
            'CREATE POLICY market_update ON public.%I FOR UPDATE TO authenticated
             USING ((SELECT public.ninja_stock_role()) = %L)
             WITH CHECK ((SELECT public.ninja_stock_role()) = %L)',
            protected_table, 'market_sync', 'market_sync'
        );
    END LOOP;
END;
$$;

GRANT INSERT ON public.sync_logs TO authenticated;
CREATE POLICY sync_log_insert ON public.sync_logs FOR INSERT TO authenticated
    WITH CHECK ((SELECT public.ninja_stock_role()) = 'market_sync');
REVOKE ALL ON SEQUENCE public.sync_logs_id_seq FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SEQUENCE public.sync_logs_id_seq TO authenticated;

CREATE FUNCTION public.ninja_watchlist_symbols()
RETURNS TABLE(stock_id text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT DISTINCT w.stock_id::text
    FROM public.watchlist AS w
    WHERE (SELECT public.ninja_stock_role()) = 'market_sync'
    ORDER BY 1
$$;
REVOKE ALL ON FUNCTION public.ninja_watchlist_symbols() FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.ninja_watchlist_symbols() TO authenticated;

COMMIT;
