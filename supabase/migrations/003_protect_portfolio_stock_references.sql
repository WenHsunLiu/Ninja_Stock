BEGIN;

SET LOCAL lock_timeout = '5s';

ALTER TABLE public.holdings
    DROP CONSTRAINT holdings_stock_id_fkey,
    ADD CONSTRAINT holdings_stock_id_fkey
        FOREIGN KEY (stock_id) REFERENCES public.stocks (stock_id) ON DELETE RESTRICT;

ALTER TABLE public.transactions
    DROP CONSTRAINT transactions_stock_id_fkey,
    ADD CONSTRAINT transactions_stock_id_fkey
        FOREIGN KEY (stock_id) REFERENCES public.stocks (stock_id) ON DELETE RESTRICT;

COMMIT;
