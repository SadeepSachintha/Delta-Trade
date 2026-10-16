import pytest
from engine.order_book import OrderBook


def test_order_book_snapshot_and_sorting():
    book = OrderBook("BTCUSDT", "Binance")
    bids = [[68400.0, 1.5], [68410.0, 0.5], [68390.0, 2.0]]
    asks = [[68420.0, 1.0], [68415.0, 0.8], [68430.0, 3.0]]

    book.apply_snapshot(bids, asks)

    # Best bid should be highest price (68410.0)
    assert book.best_bid == (68410.0, 0.5)
    # Best ask should be lowest price (68415.0)
    assert book.best_ask == (68415.0, 0.8)
    # Mid-price should be (68410 + 68415) / 2 = 68412.5
    assert book.mid_price == 68412.5
    # Spread abs should be 5.0
    assert book.spread_abs == 5.0


def test_order_book_micro_price_and_imbalance():
    book = OrderBook("ETHUSDT", "Bybit")
    # Imbalance: more bids than asks
    bids = [[2630.0, 10.0]]
    asks = [[2632.0, 2.0]]
    book.apply_snapshot(bids, asks)

    # OBI = (10 - 2) / 12 = 8 / 12 = 0.6667 (buy pressure)
    assert book.order_book_imbalance == pytest.approx(8.0 / 12.0, rel=1e-3)

    # Micro-price should be weighted towards the ask: (2632 * 10 + 2630 * 2) / 12 = 31580 / 12 = 2631.67
    assert book.micro_price == pytest.approx(2631.6667, rel=1e-3)


def test_order_book_delta_update():
    book = OrderBook("SOLUSDT", "OKX")
    book.apply_snapshot([[150.0, 10.0], [149.0, 5.0]], [[151.0, 8.0], [152.0, 12.0]])

    # Delete 151.0 ask and add tighter 150.5 ask
    book.apply_delta([], [[151.0, 0.0], [150.5, 4.0]])

    assert book.best_ask == (150.5, 4.0)
    assert book.spread_abs == 0.5


def test_walk_book_buy_quote_budget():
    book = OrderBook("BTCUSDT", "Binance")
    # Asks: 1 BTC @ 50,000, 2 BTC @ 55,000
    book.apply_snapshot([[49000.0, 1.0]], [[50000.0, 1.0], [55000.0, 2.0]])

    # Buy with $50,000 budget (consumes level 1 fully)
    vwap, filled, slip_bps, is_full = book.walk_book("BUY", 50000.0, is_quote_quantity=True)
    assert is_full is True
    assert vwap == 50000.0
    assert slip_bps == 0.0

    # Buy with $105,000 budget:
    # 50k @ 50k (1.0 BTC) + 55k @ 55k (1.0 BTC) = 2.0 BTC for $105,000
    # VWAP = 105,000 / 2.0 = 52,500
    vwap2, filled2, slip_bps2, is_full2 = book.walk_book("BUY", 105000.0, is_quote_quantity=True)
    assert is_full2 is True
    assert vwap2 == 52500.0
    # Slippage relative to best ask (50,000): (52,500 - 50,000) / 50,000 * 10000 = 500 bps
    assert slip_bps2 == pytest.approx(500.0, rel=1e-2)


def test_walk_book_sell_base_quantity():
    book = OrderBook("BTCUSDT", "Binance")
    # Bids: 1 BTC @ 60,000, 1 BTC @ 58,000
    book.apply_snapshot([[60000.0, 1.0], [58000.0, 1.0]], [[61000.0, 1.0]])

    # Sell 1.5 BTC:
    # 1.0 BTC @ 60,000 ($60,000) + 0.5 BTC @ 58,000 ($29,000) = $89,000 total quote
    # VWAP = 89,000 / 1.5 = 59,333.33
    vwap, filled_quote, slip_bps, is_full = book.walk_book("SELL", 1.5, is_quote_quantity=False)
    assert is_full is True
    assert vwap == pytest.approx(59333.33, rel=1e-3)
    # Slippage relative to 60,000: (60,000 - 59,333.33) / 60,000 * 10,000 = 111.11 bps
    assert slip_bps == pytest.approx(111.11, rel=1e-2)


def test_slippage_curve_with_quote_conversion():
    book = OrderBook("ETHBTC", "Binance")
    # Bids & Asks in BTC
    book.apply_snapshot([[0.0385, 10.0]], [[0.0386, 10.0]])

    # If quote currency is BTC, 1 BTC = $68,400 USD
    curve = book.compute_slippage_curve([1000.0, 5000.0], quote_usd_rate=68400.0)
    assert len(curve) == 2
    assert curve[0]["capital_usd"] == 1000.0
    assert curve[0]["buy_fully_filled"] is True
    assert curve[0]["buy_vwap"] == 0.0386
