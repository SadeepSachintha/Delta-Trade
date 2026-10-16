import os
import pytest
from engine.feeds.market_feed_manager import MarketFeedManager
from engine.math_engine import ArbitrageRoute, ArbitrageLeg
from engine.state_store import StateStore
from engine.execution_simulator import ExecutionSimulator


from pathlib import Path


@pytest.fixture
def sim_env(tmp_path):
    lock_file = Path(__file__).resolve().parent.parent / "management" / "kill_switch.lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except Exception:
            pass

    db_file = str(tmp_path / "test_arb.db")
    store = StateStore(db_file)
    fm = MarketFeedManager()
    sim = ExecutionSimulator(store, fm)
    sim.set_kill_switch(False)
    yield store, fm, sim

    if lock_file.exists():
        try:
            lock_file.unlink()
        except Exception:
            pass



def test_kill_switch_blocks_execution(sim_env):
    _, _, sim = sim_env

    dummy_leg = ArbitrageLeg(
        step=1,
        from_currency="USDT",
        to_currency="BTC",
        exchange="Binance",
        action="BUY",
        symbol="BTCUSDT",
        rate=1.0 / 68000.0,
        vwap=68000.0,
        fee_rate=0.00075,
        slippage_bps=2.0,
        input_amount=10000.0,
        output_amount=0.147
    )
    dummy_route = ArbitrageRoute(
        route_id="ROUTE_TEST",
        route_type="TRIANGULAR",
        path=["USDT", "BTC", "USDT"],
        exchanges=["Binance"],
        gross_spread_bps=12.0,
        net_spread_bps=8.0,
        optimal_size_usd=10000.0,
        expected_profit_usd=8.0,
        total_fee_drag_usd=1.5,
        total_slippage_drag_usd=0.5,
        legs=[dummy_leg],
        cycle_latency_us=950,
        detected_at_ns=0
    )

    # When kill switch is disengaged, trade executes cleanly
    res = sim.execute_route(dummy_route, 10000.0)
    assert res["id"].startswith("EXE-")
    assert res["fill_status"] in ["FILLED", "PARTIAL_FILL"]

    # When kill switch is engaged, trade is blocked immediately
    sim.set_kill_switch(True)
    assert sim.is_kill_switch_engaged is True
    with pytest.raises(ValueError, match="EMERGENCY_KILL_SWITCH_ACTIVE"):
        sim.execute_route(dummy_route, 10000.0)

    # Disengage again
    sim.set_kill_switch(False)
    assert sim.is_kill_switch_engaged is False


def test_evaluate_auto_arbitrage_thresholds(sim_env):
    _, _, sim = sim_env
    sim.auto_bot_enabled = True
    sim.auto_min_spread_bps = 5.0

    low_route = ArbitrageRoute(
        route_id="R_LOW",
        route_type="SPATIAL",
        path=["USDT", "BTC", "USDT"],
        exchanges=["Binance", "Bybit"],
        gross_spread_bps=4.0,
        net_spread_bps=2.0, # Below 5.0 bps threshold
        optimal_size_usd=10000.0,
        expected_profit_usd=2.0,
        total_fee_drag_usd=1.0,
        total_slippage_drag_usd=0.5,
        legs=[],
        cycle_latency_us=800,
        detected_at_ns=0
    )

    high_route = ArbitrageRoute(
        route_id="R_HIGH",
        route_type="SPATIAL",
        path=["USDT", "ETH", "USDT"],
        exchanges=["Binance", "OKX"],
        gross_spread_bps=15.0,
        net_spread_bps=10.0, # Meets threshold!
        optimal_size_usd=10000.0,
        expected_profit_usd=10.0,
        total_fee_drag_usd=1.0,
        total_slippage_drag_usd=0.5,
        legs=[],
        cycle_latency_us=800,
        detected_at_ns=0
    )

    # Should not trigger on low_route
    trade = sim.evaluate_auto_arbitrage([low_route])
    assert trade is None

    # Should trigger on high_route
    trade_high = sim.evaluate_auto_arbitrage([high_route])
    assert trade_high is not None
    assert trade_high["route_id"] == "R_HIGH"
