from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from src.db import client as db_client

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_connection_error_displays_only_safe_setup_guidance(monkeypatch):
    connect = Mock(side_effect=RuntimeError("synthetic-credential"))
    monkeypatch.setattr(db_client, "get_supabase_client", connect)

    app = AppTest.from_file(APP_PATH, default_timeout=20).run()

    assert not app.exception
    assert app.error
    guidance = " ".join(element.value for element in [*app.error, *app.info])
    assert "synthetic-credential" not in guidance
    assert "supabase.co" not in guidance
    assert not app.button


def test_trade_provider_error_does_not_expose_provider_details(monkeypatch):
    _, transactions = fake_portfolio_client(monkeypatch)
    transactions.insert.return_value.execute.side_effect = ValueError(
        "synthetic-credential in upstream response"
    )

    app = submit_trade()

    assert not app.exception
    assert len(app.error) == 1
    assert "synthetic-credential" not in app.error[0].value
    assert "請先檢查交易帳本" in app.error[0].value
    transactions.insert.assert_called_once()


@pytest.mark.parametrize(
    ("holdings", "message"),
    [
        ([], "目前並未持有 2330"),
        ([{"shares": 50, "cost_price": 90}], "超過目前在庫持股數"),
    ],
)
def test_sell_validation_still_explains_why_trade_was_rejected(monkeypatch, holdings, message):
    _, transactions = fake_portfolio_client(monkeypatch, holdings=holdings)

    app = submit_trade("賣出 (SELL)")

    assert not app.exception
    assert len(app.error) == 1
    assert message in app.error[0].value
    transactions.insert.assert_not_called()


def test_buy_form_still_records_trade_and_updates_holdings(monkeypatch):
    client, transactions = fake_portfolio_client(monkeypatch)

    app = submit_trade()

    assert not app.exception
    assert not app.error
    transactions.insert.assert_called_once()
    assert transactions.insert.call_args.args[0]["stock_id"] == "2330"
    client.table("holdings").insert.assert_called_once()


def test_sell_form_still_records_trade_and_updates_holdings(monkeypatch):
    client, transactions = fake_portfolio_client(
        monkeypatch, holdings=[{"shares": 1000, "cost_price": 90}]
    )

    app = submit_trade("賣出 (SELL)")

    assert not app.exception
    assert not app.error
    transactions.insert.assert_called_once()
    assert transactions.insert.call_args.args[0]["action"] == "SELL"
    client.table("holdings").delete.assert_called_once()


def fake_portfolio_client(monkeypatch, *, holdings=()):
    tables = {name: Mock() for name in ("holdings", "transactions", "daily_quotes")}
    empty = SimpleNamespace(data=[])
    for table in tables.values():
        table.select.return_value.execute.return_value = empty
        filtered = table.select.return_value.eq.return_value
        filtered.execute.return_value = empty
        filtered.order.return_value.limit.return_value.execute.return_value = empty
        table.select.return_value.order.return_value.limit.return_value.execute.return_value = empty
    tables["holdings"].select.return_value.eq.return_value.execute.return_value = (
        SimpleNamespace(data=list(holdings))
    )

    client = Mock()
    client.table.side_effect = tables.__getitem__
    monkeypatch.setattr(db_client, "get_supabase_client", lambda: client)
    return client, tables["transactions"]


def submit_trade(action="買進 (BUY)"):
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    app.sidebar.radio[0].set_value(action)
    app.sidebar.text_input[0].set_value("2330")
    return app.sidebar.button[0].click().run()
