import numpy as np
import pandas as pd
import pytest
from src.config import settings
from src.fetchers.finmind import FinMindFetcher, INVESTOR_TYPE_MAP


def test_config_settings():
    assert settings.SUPABASE_URL != ""
    assert settings.SUPABASE_KEY != ""
    assert len(settings.CORE_STOCKS) > 0
    assert "2330" in settings.CORE_STOCKS
    assert "0050" in settings.CORE_STOCKS


def test_clean_records():
    df = pd.DataFrame({
        "stock_id": ["2330", "2317"],
        "price": [1000.0, np.nan],
        "name": ["台積電", None],
    })
    cleaned = FinMindFetcher._clean_records(df)
    assert len(cleaned) == 2
    assert cleaned[0]["stock_id"] == "2330"
    assert cleaned[0]["price"] == 1000.0
    assert cleaned[1]["price"] is None
    assert cleaned[1]["name"] is None


def test_investor_type_mapping():
    assert INVESTOR_TYPE_MAP["Foreign_Investor"] == "外資及陸資"
    assert INVESTOR_TYPE_MAP["Investment_Trust"] == "投信"
    assert INVESTOR_TYPE_MAP["Dealer_self"] == "自營商(自行買賣)"
    assert INVESTOR_TYPE_MAP["Dealer_Hedging"] == "自營商(避險)"
