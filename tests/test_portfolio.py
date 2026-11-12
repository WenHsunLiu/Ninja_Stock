import pytest
from src.services.portfolio_service import PortfolioService


def test_calculate_buy_fee():
    svc = PortfolioService(client=None)
    # 1. 一般金額 (10 萬元，6折手續費) -> 100,000 * 0.001425 * 0.6 = 85.5 -> 86 元
    fee1 = svc.calculate_buy_fee(price=100.0, shares=1000, discount=0.6)
    assert fee1 == 86.0

    # 2. 小額零股交易 (低消 20 元保護) -> 10 元 100 股 = 1000 元 -> 低消 20 元
    fee2 = svc.calculate_buy_fee(price=10.0, shares=100, discount=0.6)
    assert fee2 == 20.0


def test_calculate_sell_fee_and_tax():
    svc = PortfolioService(client=None)
    # 賣出 10 萬元: 手續費 86 元，證券交易稅 0.3% = 300 元
    fee, tax = svc.calculate_sell_fee_and_tax(price=100.0, shares=1000, discount=0.6)
    assert fee == 86.0
    assert tax == 300.0


def test_trust_trend_calculation():
    svc = PortfolioService(client=None)
    # 投信連買測試
    inst_data = [
        {"investor_type": "投信", "net_volume": 500},
        {"investor_type": "外資", "net_volume": -1000},
        {"investor_type": "投信", "net_volume": 200},
        {"investor_type": "投信", "net_volume": 100},
        {"investor_type": "投信", "net_volume": -50},
    ]
    # 應計算前 3 筆投信買超 (500, 200, 100 > 0)
    consecutive = svc._check_trust_trend(inst_data)
    assert consecutive == 3
