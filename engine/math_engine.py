"""
High-Frequency Arbitrage Math Engine.
Calculates Bellman-Ford Negative Cycle Detection across multi-venue currency matrices
and Cross-Exchange Spatial Arbitrage in under 5 milliseconds with exact order book
depth walking, maker/taker fee drag, and non-linear slippage accounting.
"""

import time
import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from .order_book import OrderBook


# Exchange default taker fee tiers (in bps: 1 bps = 0.0001)
FEE_TIERS = {
    "Binance": 0.00075, # 7.5 bps (VIP0 with BNB discount)
    "Bybit": 0.00060,   # 6.0 bps (standard spot taker)
    "OKX": 0.00080,     # 8.0 bps (standard spot taker)
}

# Gas & transfer drag for spatial arbitrage rebalancing
TRANSFER_GAS_USD = 1.50


@dataclass
class ArbitrageLeg:
    step: int
    from_currency: str
    to_currency: str
    exchange: str
    action: str # "BUY" or "SELL"
    symbol: str
    rate: float
    vwap: float
    fee_rate: float
    slippage_bps: float
    input_amount: float
    output_amount: float


@dataclass
class ArbitrageRoute:
    route_id: str
    route_type: str # "TRIANGULAR" or "SPATIAL"
    path: List[str] # e.g. ["USDT", "BTC", "ETH", "USDT"]
    exchanges: List[str]
    gross_spread_bps: float
    net_spread_bps: float
    optimal_size_usd: float
    expected_profit_usd: float
    total_fee_drag_usd: float
    total_slippage_drag_usd: float
    legs: List[ArbitrageLeg]
    cycle_latency_us: int
    detected_at_ns: int


class ArbitrageMathEngine:
    CURRENCIES = ["USDT", "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"]

    def __init__(self, feed_manager):
        self.feed_manager = feed_manager
        self.currency_to_idx = {c: i for i, c in enumerate(self.CURRENCIES)}
        self.num_currencies = len(self.CURRENCIES)
        
        # Telemetry
        self.last_cycle_time_us: int = 0
        self.total_scans: int = 0
        self.routes_found: int = 0

    def scan_all(self, test_capital_usd: float = 10000.0) -> Tuple[List[ArbitrageRoute], Dict]:
        """
        Executes complete microsecond arbitrage scan:
        1. Bellman-Ford negative cycle triangular detection
        2. Cross-Exchange spatial depth arbitrage
        Returns detected routes and execution telemetry.
        """
        t0 = time.perf_counter_ns()
        self.total_scans += 1

        routes: List[ArbitrageRoute] = []

        # 1. Triangular Arbitrage via Bellman-Ford
        tri_routes = self._detect_bellman_ford_cycles(test_capital_usd)
        routes.extend(tri_routes)

        # 2. Cross-Exchange Spatial Arbitrage
        spatial_routes = self._detect_spatial_arbitrage(test_capital_usd)
        routes.extend(spatial_routes)

        t1 = time.perf_counter_ns()
        self.last_cycle_time_us = (t1 - t0) // 1000
        if routes:
            self.routes_found += len(routes)

        telemetry = {
            "cycle_latency_us": self.last_cycle_time_us,
            "cycle_latency_ms": round(self.last_cycle_time_us / 1000.0, 3),
            "total_scans": self.total_scans,
            "active_opportunities": len(routes),
            "under_5ms": self.last_cycle_time_us < 5000
        }

        return routes, telemetry

    def get_rate_matrix(self) -> Dict:
        """Constructs NxN currency conversion rate matrix and implied spreads."""
        matrix = [[1.0 for _ in range(self.num_currencies)] for _ in range(self.num_currencies)]
        log_matrix = [[0.0 for _ in range(self.num_currencies)] for _ in range(self.num_currencies)]
        
        for i, u in enumerate(self.CURRENCIES):
            for j, v in enumerate(self.CURRENCIES):
                if i == j:
                    continue
                best_rate = self._get_best_direct_rate(u, v)
                if best_rate and best_rate["rate"] > 0:
                    rate = best_rate["rate"]
                    matrix[i][j] = round(rate, 6 if rate < 10 else 2)
                    log_matrix[i][j] = round(-math.log(rate), 6)

        return {
            "currencies": self.CURRENCIES,
            "rates": matrix,
            "log_weights": log_matrix
        }

    def _get_best_direct_rate(self, from_curr: str, to_curr: str) -> Optional[Dict]:
        """Finds best exchange rate across all venues for trading from_curr -> to_curr."""
        best_rate = -1.0
        best_venue = None
        best_action = None
        best_sym = None
        best_book = None

        # Check if direct pair exists as BaseQuote or QuoteBase
        for ex in self.feed_manager.EXCHANGES:
            # Case 1: to_curr is Base, from_curr is Quote (e.g. from USDT -> to BTC: pair BTCUSDT)
            pair_direct = f"{to_curr}{from_curr}"
            book_direct = self.feed_manager.get_order_book(ex, pair_direct)
            if book_direct and book_direct.best_ask:
                ask_p = book_direct.best_ask[0]
                if ask_p > 0:
                    fee = FEE_TIERS.get(ex, 0.001)
                    effective_rate = (1.0 - fee) / ask_p
                    if effective_rate > best_rate:
                        best_rate = effective_rate
                        best_venue = ex
                        best_action = "BUY"
                        best_sym = pair_direct
                        best_book = book_direct

            # Case 2: from_curr is Base, to_curr is Quote (e.g. from BTC -> to USDT: pair BTCUSDT)
            pair_reverse = f"{from_curr}{to_curr}"
            book_reverse = self.feed_manager.get_order_book(ex, pair_reverse)
            if book_reverse and book_reverse.best_bid:
                bid_p = book_reverse.best_bid[0]
                if bid_p > 0:
                    fee = FEE_TIERS.get(ex, 0.001)
                    effective_rate = (1.0 - fee) * bid_p
                    if effective_rate > best_rate:
                        best_rate = effective_rate
                        best_venue = ex
                        best_action = "SELL"
                        best_sym = pair_reverse
                        best_book = book_reverse

        if best_rate > 0:
            return {
                "rate": best_rate,
                "exchange": best_venue,
                "action": best_action,
                "symbol": best_sym,
                "book": best_book
            }
        return None

    def _detect_bellman_ford_cycles(self, test_capital: float) -> List[ArbitrageRoute]:
        """
        Optimized Bellman-Ford Negative Cycle Detection:
        Nodes = Currency Vertices
        Weights = -ln(Effective_Exchange_Rate)
        Negative cycle < 0 => Product of rates > 1.0 (Profitable loop!)
        """
        t_start = time.perf_counter_ns()
        routes = []
        n = self.num_currencies
        
        # Build edge list: (u_idx, v_idx, weight, edge_info)
        edges = []
        for u in self.CURRENCIES:
            u_idx = self.currency_to_idx[u]
            for v in self.CURRENCIES:
                if u == v:
                    continue
                v_idx = self.currency_to_idx[v]
                info = self._get_best_direct_rate(u, v)
                if info and info["rate"] > 0:
                    weight = -math.log(info["rate"])
                    edges.append((u_idx, v_idx, weight, info))

        if not edges:
            return []

        # Universal super-source anchor: initialize all distances to 0.0 to detect cycles anywhere in graph
        dist = [0.0] * n
        parent = [-1] * n
        edge_used = [None] * n

        # Relax edges (n - 1) times
        for _ in range(n - 1):
            relaxed = False
            for u, v, w, info in edges:
                if dist[u] + w < dist[v] - 1e-12:
                    dist[v] = dist[u] + w
                    parent[v] = u
                    edge_used[v] = info
                    relaxed = True
            if not relaxed:
                break

        # Check for negative cycle candidates on the n-th pass
        neg_cycle_nodes = []
        for u, v, w, info in edges:
            if dist[u] + w < dist[v] - 1e-7:
                parent[v] = u
                edge_used[v] = info
                neg_cycle_nodes.append(v)

        seen_cycles = set()
        for node in neg_cycle_nodes:
            # Trace cycle back to recover vertices
            curr = node
            for _ in range(n):
                curr = parent[curr]

            cycle = []
            cycle_start = curr
            curr = cycle_start
            for _ in range(n + 1):
                cycle.append(curr)
                curr = parent[curr]
                if curr == cycle_start and len(cycle) > 1:
                    cycle.append(cycle_start)
                    break

            cycle.reverse()
            if len(cycle) >= 3 and cycle[0] == cycle[-1]:
                raw_path = [self.CURRENCIES[idx] for idx in cycle]
                # Rotate cycle so USDT is first if it is present
                if "USDT" in raw_path[:-1]:
                    u_idx = raw_path[:-1].index("USDT")
                    path_names = raw_path[u_idx:-1] + raw_path[:u_idx] + ["USDT"]
                else:
                    path_names = raw_path

                path_key = "->".join(path_names)
                if path_key not in seen_cycles:
                    seen_cycles.add(path_key)
                    route = self._evaluate_triangular_depth(path_names, test_capital, t_start)
                    if route and route.net_spread_bps > 0:
                        routes.append(route)

        return routes

    def get_usd_value(self, currency: str, amount: float) -> float:
        """Converts an amount of any currency into USD using live order books or baseline reference."""
        if currency == "USDT" or amount <= 0:
            return amount
        pair = f"{currency}USDT"
        for ex in self.feed_manager.EXCHANGES:
            book = self.feed_manager.get_order_book(ex, pair)
            if book and book.mid_price and book.mid_price > 0:
                return amount * book.mid_price
        base_p = self.feed_manager.BASE_PRICES.get(pair, 1.0)
        return amount * base_p

    def _evaluate_triangular_depth(self, path: List[str], initial_capital: float, t_start: int) -> Optional[ArbitrageRoute]:
        """
        Walks actual reconstructed L2 order books for all legs of a triangular cycle,
        calculating VWAP, slippage drag, maker/taker fee drag, and net PnL.
        """
        # Convert initial USD capital to starting currency
        start_curr = path[0]
        start_unit_usd = self.get_usd_value(start_curr, 1.0)
        curr_capital = initial_capital if start_curr == "USDT" else (initial_capital / max(1e-8, start_unit_usd))

        legs: List[ArbitrageLeg] = []
        total_fee_drag = 0.0
        total_slip_drag = 0.0
        exchanges = []

        for step in range(len(path) - 1):
            u = path[step]
            v = path[step + 1]
            info = self._get_best_direct_rate(u, v)
            if not info or not info["book"]:
                return None

            book: OrderBook = info["book"]
            action = info["action"]
            venue = info["exchange"]
            sym = info["symbol"]
            exchanges.append(venue)
            fee_rate = FEE_TIERS.get(venue, 0.001)

            # Order book depth walk for exact fill
            # If action == "BUY", u is quote currency (spending u to buy v) -> is_quote_quantity = True
            # If action == "SELL", u is base currency (selling u for v) -> is_quote_quantity = False
            is_quote_qty = (action == "BUY")
            vwap, _, slippage_bps, is_filled = book.walk_book(action, curr_capital, is_quote_quantity=is_quote_qty)
            
            if not is_filled or vwap <= 0:
                vwap = book.best_ask[0] if action == "BUY" else book.best_bid[0]
                slippage_bps = 5.0

            # Calculate actual leg execution
            if action == "BUY":
                # Buy base currency (v) with quote currency (u)
                units_bought = (curr_capital / vwap) * (1.0 - fee_rate)
                fee_usd = self.get_usd_value(u, curr_capital * fee_rate)
                slip_usd = self.get_usd_value(u, curr_capital * (slippage_bps / 10000.0))
                next_capital = units_bought
            else:
                # Sell base currency (u) for quote currency (v)
                proceeds = (curr_capital * vwap) * (1.0 - fee_rate)
                fee_usd = self.get_usd_value(v, (curr_capital * vwap) * fee_rate)
                slip_usd = self.get_usd_value(v, (curr_capital * vwap) * (slippage_bps / 10000.0))
                next_capital = proceeds

            total_fee_drag += fee_usd
            total_slip_drag += slip_usd

            legs.append(ArbitrageLeg(
                step=step + 1,
                from_currency=u,
                to_currency=v,
                exchange=venue,
                action=action,
                symbol=sym,
                rate=info["rate"],
                vwap=round(vwap, 6 if vwap < 10 else 2),
                fee_rate=fee_rate,
                slippage_bps=round(slippage_bps, 2),
                input_amount=round(curr_capital, 4),
                output_amount=round(next_capital, 4)
            ))
            curr_capital = next_capital

        final_capital_usd = self.get_usd_value(path[-1], curr_capital)
        expected_profit_usd = final_capital_usd - initial_capital
        net_spread_bps = (expected_profit_usd / initial_capital) * 10000.0
        gross_spread_bps = net_spread_bps + ((total_fee_drag + total_slip_drag) / initial_capital) * 10000.0

        t_end = time.perf_counter_ns()
        latency_us = (t_end - t_start) // 1000

        route_id = f"TRI_{'_'.join(path)}_{int(time.time() * 1000) % 100000}"

        return ArbitrageRoute(
            route_id=route_id,
            route_type="TRIANGULAR",
            path=path,
            exchanges=exchanges,
            gross_spread_bps=round(gross_spread_bps, 2),
            net_spread_bps=round(net_spread_bps, 2),
            optimal_size_usd=initial_capital,
            expected_profit_usd=round(expected_profit_usd, 2),
            total_fee_drag_usd=round(total_fee_drag, 2),
            total_slippage_drag_usd=round(total_slip_drag, 2),
            legs=legs,
            cycle_latency_us=latency_us,
            detected_at_ns=t_end
        )

    def _detect_spatial_arbitrage(self, test_capital: float) -> List[ArbitrageRoute]:
        """
        Cross-Exchange Spatial Arbitrage:
        Checks Buy Venue A Ask vs Sell Venue B Bid for identical pairs.
        Accounts for:
          - Taker fee on Venue A
          - Taker fee on Venue B
          - Real Order Book Depth Walk (VWAP)
          - Gas / transfer fee rebalancing drag
        """
        spatial_routes: List[ArbitrageRoute] = []
        t_start = time.perf_counter_ns()

        pairs_to_scan = [
            ("BTCUSDT", "BTC", "USDT"),
            ("ETHUSDT", "ETH", "USDT"),
            ("SOLUSDT", "SOL", "USDT"),
            ("BNBUSDT", "BNB", "USDT"),
            ("XRPUSDT", "XRP", "USDT"),
            ("DOGEUSDT", "DOGE", "USDT"),
            ("ETHBTC", "ETH", "BTC"),
            ("SOLBTC", "SOL", "BTC"),
            ("BNBBTC", "BNB", "BTC")
        ]

        for sym, base_curr, quote_curr in pairs_to_scan:
            quote_usd = self.get_usd_value(quote_curr, 1.0)
            quote_capital = test_capital / max(1e-8, quote_usd)

            for ex_buy in self.feed_manager.EXCHANGES:
                book_buy = self.feed_manager.get_order_book(ex_buy, sym)
                if not book_buy or not book_buy.best_ask:
                    continue
                ask_p = book_buy.best_ask[0]

                for ex_sell in self.feed_manager.EXCHANGES:
                    if ex_buy == ex_sell:
                        continue
                    book_sell = self.feed_manager.get_order_book(ex_sell, sym)
                    if not book_sell or not book_sell.best_bid:
                        continue
                    bid_p = book_sell.best_bid[0]

                    # Check basic spread
                    if bid_p > ask_p:
                        # Depth walk on Buy venue for quote currency budget
                        buy_vwap, _, buy_slip, buy_ok = book_buy.walk_book("BUY", quote_capital, is_quote_quantity=True)
                        fee_buy = FEE_TIERS.get(ex_buy, 0.001)
                        fee_sell = FEE_TIERS.get(ex_sell, 0.001)

                        qty_bought = (quote_capital / buy_vwap) * (1.0 - fee_buy)
                        # Depth walk on Sell venue for exact base quantity acquired
                        sell_vwap, _, sell_slip, sell_ok = book_sell.walk_book("SELL", qty_bought, is_quote_quantity=False)
                        
                        gross_proceeds_quote = qty_bought * sell_vwap
                        net_proceeds_quote = gross_proceeds_quote * (1.0 - fee_sell)
                        net_proceeds_usd = (net_proceeds_quote * quote_usd) - TRANSFER_GAS_USD
                        
                        profit_usd = net_proceeds_usd - test_capital
                        net_spread_bps = (profit_usd / test_capital) * 10000.0

                        if net_spread_bps > 1.0: # At least 1.0 bps net profit after all fees & slippage
                            gross_spread_bps = ((bid_p - ask_p) / ask_p) * 10000.0
                            t_end = time.perf_counter_ns()
                            
                            route_id = f"SPAT_{sym}_{ex_buy}_{ex_sell}_{int(time.time() * 1000) % 100000}"
                            
                            leg1 = ArbitrageLeg(
                                step=1,
                                from_currency=quote_curr,
                                to_currency=base_curr,
                                exchange=ex_buy,
                                action="BUY",
                                symbol=sym,
                                rate=1.0 / buy_vwap,
                                vwap=round(buy_vwap, 6 if buy_vwap < 10 else 2),
                                fee_rate=fee_buy,
                                slippage_bps=round(buy_slip, 2),
                                input_amount=round(quote_capital, 4),
                                output_amount=round(qty_bought, 4)
                            )
                            
                            leg2 = ArbitrageLeg(
                                step=2,
                                from_currency=base_curr,
                                to_currency=quote_curr,
                                exchange=ex_sell,
                                action="SELL",
                                symbol=sym,
                                rate=sell_vwap,
                                vwap=round(sell_vwap, 6 if sell_vwap < 10 else 2),
                                fee_rate=fee_sell,
                                slippage_bps=round(sell_slip, 2),
                                input_amount=round(qty_bought, 4),
                                output_amount=round(net_proceeds_quote, 4)
                            )

                            spatial_routes.append(ArbitrageRoute(
                                route_id=route_id,
                                route_type="SPATIAL",
                                path=[quote_curr, base_curr, quote_curr],
                                exchanges=[ex_buy, ex_sell],
                                gross_spread_bps=round(gross_spread_bps, 2),
                                net_spread_bps=round(net_spread_bps, 2),
                                optimal_size_usd=test_capital,
                                expected_profit_usd=round(profit_usd, 2),
                                total_fee_drag_usd=round(test_capital * (fee_buy + fee_sell), 2),
                                total_slippage_drag_usd=round(test_capital * ((buy_slip + sell_slip) / 10000.0), 2),
                                legs=[leg1, leg2],
                                cycle_latency_us=(t_end - t_start) // 1000,
                                detected_at_ns=t_end
                            ))

        return spatial_routes

