import time
import pytest
from engine.feeds.market_feed_manager import MarketFeedManager
from engine.math_engine import ArbitrageMathEngine


@pytest.fixture
def math_env():
    feed_manager = MarketFeedManager()
    engine = ArbitrageMathEngine(feed_manager)
    return feed_manager, engine


def test_rate_matrix_structure(math_env):
    _, engine = math_env
    matrix = engine.get_rate_matrix()
    assert "currencies" in matrix
    assert "rates" in matrix
    assert "log_weights" in matrix
    assert len(matrix["currencies"]) == len(engine.CURRENCIES)
    # Diagonal should be 1.0
    for i in range(len(engine.CURRENCIES)):
        assert matrix["rates"][i][i] == 1.0
        assert matrix["log_weights"][i][i] == 0.0


def test_bellman_ford_sub_5ms_benchmark(math_env):
    _, engine = math_env
    t0 = time.perf_counter_ns()
    routes, telemetry = engine.scan_all(test_capital_usd=10000.0)
    t1 = time.perf_counter_ns()
    elapsed_us = (t1 - t0) // 1000

    # Ensure engine telemetry reports sub-5ms latency
    assert telemetry["cycle_latency_us"] < 5000
    assert telemetry["under_5ms"] is True
    # And total wall-clock scan is well within 5ms (typically 200-1500 us)
    assert elapsed_us < 5000


def test_detects_injected_triangular_arbitrage(math_env):
    feed_manager, engine = math_env

    # Inject an explicit profitable triangular arbitrage cycle:
    # 1. Buy BTC with USDT on Binance @ 50,000
    # 2. Buy ETH with BTC on Bybit @ 0.04 (giving 1 / 0.04 = 25 ETH per BTC)
    # 3. Sell ETH for USDT on OKX @ 2,500 (giving 25 * 2,500 = 62,500 USDT)
    # Gross multiplier: (1 / 50000) * (1 / 0.04) * 2500 = 62,500 / 50,000 = 1.25 (+25% gross!)
    book_btc = feed_manager.get_order_book("Binance", "BTCUSDT")
    book_ethbtc = feed_manager.get_order_book("Bybit", "ETHBTC")
    book_eth = feed_manager.get_order_book("OKX", "ETHUSDT")

    book_btc.apply_snapshot([[49900.0, 10.0]], [[50000.0, 10.0]])
    book_ethbtc.apply_snapshot([[0.039, 100.0]], [[0.040, 100.0]])
    book_eth.apply_snapshot([[2500.0, 100.0]], [[2510.0, 100.0]])

    routes, _ = engine.scan_all(test_capital_usd=10000.0)
    tri_routes = [r for r in routes if r.route_type == "TRIANGULAR"]

    assert len(tri_routes) > 0
    top_route = tri_routes[0]
    assert top_route.net_spread_bps > 100.0
    assert top_route.expected_profit_usd > 100.0
    assert len(top_route.legs) >= 2



def test_detects_injected_spatial_arbitrage(math_env):
    feed_manager, engine = math_env

    # Inject spatial price discrepancy:
    # Binance SOLUSDT Best Ask: 140.0
    # Bybit SOLUSDT Best Bid: 145.0 (+3.57% spread)
    book_binance = feed_manager.get_order_book("Binance", "SOLUSDT")
    book_bybit = feed_manager.get_order_book("Bybit", "SOLUSDT")

    book_binance.apply_snapshot([[139.0, 50.0]], [[140.0, 50.0]])
    book_bybit.apply_snapshot([[145.0, 50.0]], [[146.0, 50.0]])

    routes, _ = engine.scan_all(test_capital_usd=5000.0)
    spatial_routes = [r for r in routes if r.route_type == "SPATIAL" and "SOL" in r.path]

    assert len(spatial_routes) > 0
    route = spatial_routes[0]
    assert route.net_spread_bps > 50.0
    assert route.expected_profit_usd > 20.0
