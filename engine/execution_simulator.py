"""
Execution Simulator & Auto-Arbitrage Engine.
Simulates real-world execution latency, adverse selection, maker/taker fee drag,
multi-leg order book fills, and automated algorithmic execution bots.
"""

import asyncio
import json
import random
import time
import uuid
from typing import Dict, List, Optional
from pathlib import Path
from .math_engine import ArbitrageRoute, ArbitrageLeg
from .state_store import StateStore



class ExecutionSimulator:
    def __init__(self, state_store: StateStore, feed_manager):
        self.state_store = state_store
        self.feed_manager = feed_manager
        
        # Simulator Configuration
        self.simulated_latency_ms: float = 14.5 # 14.5ms median execution latency
        self.adverse_selection_rate: float = 0.08 # 8% chance of book moving against us
        self.auto_bot_enabled: bool = False
        self.auto_min_spread_bps: float = 6.0 # Min 6 bps profit to auto-fire
        self.auto_trade_capital_usd: float = 10000.0
        self.last_auto_trade_time: float = 0.0
        self.execution_cooldown_sec: float = 0.8
        self._manual_kill_switch: bool = False
        
        # Seed initial realistic trades if database is empty
        self._seed_initial_history()

    @property
    def is_kill_switch_engaged(self) -> bool:
        lock_file = Path(__file__).resolve().parent.parent / "management" / "kill_switch.lock"
        return self._manual_kill_switch or lock_file.exists()

    def set_kill_switch(self, engage: bool):
        self._manual_kill_switch = engage
        lock_file = Path(__file__).resolve().parent.parent / "management" / "kill_switch.lock"
        if engage:
            lock_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file.write_text(json.dumps({
                "engaged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reason": "Emergency halt triggered by risk administrator"
            }))
        else:
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except Exception:
                    pass


    def _seed_initial_history(self):
        existing = self.state_store.get_recent_executions(limit=5)
        if len(existing) >= 5:
            return

        sample_trades = [
            {
                "id": f"EXE-{uuid.uuid4().hex[:8].upper()}",
                "route_id": "TRI_USDT_BTC_ETH_USDT_01",
                "route_type": "TRIANGULAR",
                "path": ["USDT", "BTC", "ETH", "USDT"],
                "venues": ["Binance", "Bybit", "OKX"],
                "capital_usd": 15000.0,
                "gross_pnl_usd": 48.20,
                "fee_drag_usd": 18.50,
                "slippage_drag_usd": 6.20,
                "net_pnl_usd": 23.50,
                "roi_bps": 15.67,
                "fill_status": "FILLED",
                "execution_latency_ms": 13.8,
                "legs": [
                    {"step": 1, "exchange": "Binance", "symbol": "BTCUSDT", "action": "BUY", "vwap": 68412.5, "slippage_bps": 1.8, "fee_usd": 11.25, "amount_in": 15000.0, "amount_out": 0.2192},
                    {"step": 2, "exchange": "Bybit", "symbol": "ETHBTC", "action": "BUY", "vwap": 0.03852, "slippage_bps": 2.1, "fee_usd": 4.10, "amount_in": 0.2192, "amount_out": 5.6905},
                    {"step": 3, "exchange": "OKX", "symbol": "ETHUSDT", "action": "SELL", "vwap": 2643.8, "slippage_bps": 2.3, "fee_usd": 3.15, "amount_in": 5.6905, "amount_out": 15023.50}
                ]
            },
            {
                "id": f"EXE-{uuid.uuid4().hex[:8].upper()}",
                "route_id": "SPAT_BTCUSDT_Binance_OKX_02",
                "route_type": "SPATIAL",
                "path": ["USDT", "BTC", "USDT"],
                "venues": ["Binance", "OKX"],
                "capital_usd": 25000.0,
                "gross_pnl_usd": 86.40,
                "fee_drag_usd": 38.75,
                "slippage_drag_usd": 9.45,
                "net_pnl_usd": 38.20,
                "roi_bps": 15.28,
                "fill_status": "FILLED",
                "execution_latency_ms": 16.2,
                "legs": [
                    {"step": 1, "exchange": "Binance", "symbol": "BTCUSDT", "action": "BUY", "vwap": 68405.0, "slippage_bps": 2.0, "fee_usd": 18.75, "amount_in": 25000.0, "amount_out": 0.3654},
                    {"step": 2, "exchange": "OKX", "symbol": "BTCUSDT", "action": "SELL", "vwap": 68480.0, "slippage_bps": 2.2, "fee_usd": 20.00, "amount_in": 0.3654, "amount_out": 25038.20}
                ]
            },
            {
                "id": f"EXE-{uuid.uuid4().hex[:8].upper()}",
                "route_id": "TRI_USDT_SOL_BTC_USDT_03",
                "route_type": "TRIANGULAR",
                "path": ["USDT", "SOL", "BTC", "USDT"],
                "venues": ["Bybit", "Binance", "OKX"],
                "capital_usd": 10000.0,
                "gross_pnl_usd": 32.10,
                "fee_drag_usd": 14.20,
                "slippage_drag_usd": 4.10,
                "net_pnl_usd": 13.80,
                "roi_bps": 13.80,
                "fill_status": "FILLED",
                "execution_latency_ms": 11.4,
                "legs": [
                    {"step": 1, "exchange": "Bybit", "symbol": "SOLUSDT", "action": "BUY", "vwap": 154.2, "slippage_bps": 1.5, "fee_usd": 6.00, "amount_in": 10000.0, "amount_out": 64.85},
                    {"step": 2, "exchange": "Binance", "symbol": "SOLBTC", "action": "SELL", "vwap": 0.002254, "slippage_bps": 1.9, "fee_usd": 4.50, "amount_in": 64.85, "amount_out": 0.1461},
                    {"step": 3, "exchange": "OKX", "symbol": "BTCUSDT", "action": "SELL", "vwap": 68430.0, "slippage_bps": 1.8, "fee_usd": 3.70, "amount_in": 0.1461, "amount_out": 10013.80}
                ]
            }
        ]
        for t in sample_trades:
            self.state_store.record_execution(t)

    def execute_route(self, route: ArbitrageRoute, capital_usd: float = 10000.0) -> Dict:
        """
        Simulates atomic multi-leg execution against current live book depth.
        Accounts for:
          - Emergency risk kill switch check
          - Simulated queuing latency
          - Adverse selection probability (liquidity taken by competing HFTs)
          - VWAP slippage on each leg
          - Exchange taker fees
        """
        if self.is_kill_switch_engaged:
            raise ValueError("EMERGENCY_KILL_SWITCH_ACTIVE: Execution halted by risk manager.")

        exec_id = f"EXE-{uuid.uuid4().hex[:8].upper()}"
        latency_jitter = self.simulated_latency_ms + (random.random() - 0.5) * 4.0

        # Adverse selection roll
        is_adverse = (random.random() < self.adverse_selection_rate)
        
        # Scale expected results to requested capital
        capital_ratio = capital_usd / max(1.0, route.optimal_size_usd)
        base_profit = route.expected_profit_usd * capital_ratio
        base_fees = route.total_fee_drag_usd * capital_ratio
        base_slippage = route.total_slippage_drag_usd * capital_ratio

        if is_adverse:
            # Competing bot clipped top level: slippage increases, profit reduces
            actual_slippage = base_slippage * 2.2
            net_pnl = base_profit - (actual_slippage - base_slippage)
            status = "PARTIAL_FILL" if net_pnl < 0 else "FILLED"
        else:
            actual_slippage = base_slippage
            net_pnl = base_profit
            status = "FILLED"

        gross_pnl = net_pnl + base_fees + actual_slippage
        roi_bps = (net_pnl / capital_usd) * 10000.0

        # Construct leg records
        leg_records = []
        for leg in route.legs:
            leg_records.append({
                "step": leg.step,
                "exchange": leg.exchange,
                "symbol": leg.symbol,
                "action": leg.action,
                "vwap": leg.vwap,
                "slippage_bps": leg.slippage_bps * (1.8 if is_adverse else 1.0),
                "fee_usd": round(leg.fee_rate * capital_usd / len(route.legs), 2),
                "amount_in": round(leg.input_amount * capital_ratio, 4),
                "amount_out": round(leg.output_amount * capital_ratio, 4)
            })

        exec_record = {
            "id": exec_id,
            "route_id": route.route_id,
            "route_type": route.route_type,
            "path": route.path,
            "venues": route.exchanges,
            "capital_usd": capital_usd,
            "gross_pnl_usd": round(gross_pnl, 2),
            "fee_drag_usd": round(base_fees, 2),
            "slippage_drag_usd": round(actual_slippage, 2),
            "net_pnl_usd": round(net_pnl, 2),
            "roi_bps": round(roi_bps, 2),
            "fill_status": status,
            "execution_latency_ms": round(latency_jitter, 2),
            "legs": leg_records,
            "timestamp": time.time()
        }

        self.state_store.record_execution(exec_record)
        return exec_record

    def evaluate_auto_arbitrage(self, routes: List[ArbitrageRoute]) -> Optional[Dict]:
        """Auto-execution evaluation: executes top route if auto_bot_enabled, kill switch is off, and thresholds met."""
        if not self.auto_bot_enabled or self.is_kill_switch_engaged:
            return None

        now = time.time()
        if (now - self.last_auto_trade_time) < self.execution_cooldown_sec:
            return None

        for route in routes:
            if route.net_spread_bps >= self.auto_min_spread_bps and route.expected_profit_usd >= 4.0:
                self.last_auto_trade_time = now
                try:
                    return self.execute_route(route, self.auto_trade_capital_usd)
                except ValueError:
                    return None

        return None

    def update_config(self, cfg: Dict):
        """Updates runtime simulator settings."""
        if "simulated_latency_ms" in cfg:
            self.simulated_latency_ms = float(cfg["simulated_latency_ms"])
        if "auto_bot_enabled" in cfg:
            self.auto_bot_enabled = bool(cfg["auto_bot_enabled"])
        if "auto_min_spread_bps" in cfg:
            self.auto_min_spread_bps = float(cfg["auto_min_spread_bps"])
        if "auto_trade_capital_usd" in cfg:
            self.auto_trade_capital_usd = float(cfg["auto_trade_capital_usd"])
        if "kill_switch" in cfg:
            self.set_kill_switch(bool(cfg["kill_switch"]))

    def get_config(self) -> Dict:
        return {
            "simulated_latency_ms": self.simulated_latency_ms,
            "adverse_selection_rate": self.adverse_selection_rate,
            "auto_bot_enabled": self.auto_bot_enabled,
            "auto_min_spread_bps": self.auto_min_spread_bps,
            "auto_trade_capital_usd": self.auto_trade_capital_usd,
            "execution_cooldown_sec": self.execution_cooldown_sec,
            "kill_switch": self.is_kill_switch_engaged
        }

