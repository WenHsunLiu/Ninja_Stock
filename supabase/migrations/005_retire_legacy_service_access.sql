-- On an existing deployment, apply after verifying the website and sync
-- have switched to their dedicated authenticated accounts.
BEGIN;

SET LOCAL lock_timeout = '5s';

REVOKE ALL PRIVILEGES ON TABLE
    public.holdings,
    public.transactions,
    public.portfolio_snapshots,
    public.watchlist,
    public.stocks,
    public.daily_quotes,
    public.institutional_investors,
    public.margin_trading,
    public.sync_logs
FROM service_role;

REVOKE ALL PRIVILEGES ON SEQUENCE public.sync_logs_id_seq FROM service_role;

COMMIT;
