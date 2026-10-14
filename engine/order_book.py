"""
High-Frequency L2 Order Book Depth Reconstruction & VWAP Slippage Engine.
Maintains microsecond sorted bids and asks, calculates liquidity depth,
order book imbalance, micro-price, and exact non-linear VWAP slippage curves.
"""

from typing import List, Tuple, Dict, Optional
import time
import math
from dataclasses import dataclass


@dataclass
class OrderBookLevel:
    price: float
    quantity: float
    value_usd: float = 0.0


class OrderBook:
    """
    High-performance Level-2 Order Book.
    Maintains sorted price levels:
      - Bids sorted descending (highest bid at index 0)
      - Asks sorted ascending (lowest ask at index 0)
    """

    def __init__(self, symbol: str, exchange: str):
        self.symbol: str = symbol
        self.exchange: str = exchange
        # Price to quantity mappings
        self._bids: Dict[float, float] = {}
        self._asks: Dict[float, float] = {}
        
        # Cached sorted lists for microsecond reads
        self._cached_bids: List[Tuple[float, float]] = []
        self._cached_asks: List[Tuple[float, float]] = []
        self._is_dirty: bool = True
        
        # Sequence & latency tracking
        self.last_update_id: int = 0
        self.last_update_time_ns: int = time.perf_counter_ns()
        self.update_count: int = 0

    def apply_snapshot(self, bids: List[List[float]], asks: List[List[float]], update_id: int = 0):
        """Initializes or resets the order book with full depth snapshot."""
        self._bids = {float(p): float(q) for p, q in bids if float(q) > 0}
        self._asks = {float(p): float(q) for p, q in asks if float(q) > 0}
        self.last_update_id = update_id
        self.last_update_time_ns = time.perf_counter_ns()
        self.update_count += 1
        self._is_dirty = True

    def apply_delta(self, bids: List[List[float]], asks: List[List[float]], update_id: int = 0):
        """
        Applies incremental L2 diffs in microseconds.
        Quantity == 0 deletes the level.
        """
        for p, q in bids:
            price = float(p)
            qty = float(q)
            if qty <= 0.0:
                self._bids.pop(price, None)
            else:
                self._bids[price] = qty

        for p, q in asks:
            price = float(p)
            qty = float(q)
            if qty <= 0.0:
                self._asks.pop(price, None)
            else:
                self._asks[price] = qty

        self.last_update_id = update_id
        self.last_update_time_ns = time.perf_counter_ns()
        self.update_count += 1
        self._is_dirty = True

    def _rebuild_cache(self):
        """Re-sorts cached bids and asks when marked dirty."""
        # Bids: descending price
        self._cached_bids = sorted(self._bids.items(), key=lambda x: x[0], reverse=True)
        # Asks: ascending price
        self._cached_asks = sorted(self._asks.items(), key=lambda x: x[0])
        self._is_dirty = False

    @property
    def best_bid(self) -> Optional[Tuple[float, float]]:
        if self._is_dirty:
            self._rebuild_cache()
        return self._cached_bids[0] if self._cached_bids else None

    @property
    def best_ask(self) -> Optional[Tuple[float, float]]:
        if self._is_dirty:
            self._rebuild_cache()
        return self._cached_asks[0] if self._cached_asks else None

    @property
    def mid_price(self) -> Optional[float]:
        bb = self.best_bid
        ba = self.best_ask
        if bb and ba:
            return (bb[0] + ba[0]) / 2.0
        return None

    @property
    def spread_abs(self) -> float:
        bb = self.best_bid
        ba = self.best_ask
        if bb and ba:
            return max(0.0, ba[0] - bb[0])
        return 0.0

    @property
    def spread_bps(self) -> float:
        bb = self.best_bid
        ba = self.best_ask
        if bb and ba and ba[0] > 0:
            return max(0.0, (ba[0] - bb[0]) / ba[0] * 10000.0)
        return 0.0

    @property
    def order_book_imbalance(self) -> float:
        """
        Calculates L2 Order Book Imbalance (OBI) across top 10 levels:
        OBI = (BidVolume - AskVolume) / (BidVolume + AskVolume)
        Ranges from -1.0 (strong sell pressure) to +1.0 (strong buy pressure).
        """
        if self._is_dirty:
            self._rebuild_cache()
        
        bid_vol = sum(q for _, q in self._cached_bids[:10])
        ask_vol = sum(q for _, q in self._cached_asks[:10])
        total_vol = bid_vol + ask_vol
        if total_vol > 0:
            return (bid_vol - ask_vol) / total_vol
        return 0.0

    @property
    def micro_price(self) -> Optional[float]:
        """
        Weighted Mid-Price:
        P_micro = (P_ask * V_bid + P_bid * V_ask) / (V_bid + V_ask)
        Reflects queue imbalance at the top of the book.
        """
        bb = self.best_bid
        ba = self.best_ask
        if bb and ba:
            total_v = bb[1] + ba[1]
            if total_v > 0:
                return (ba[0] * bb[1] + bb[0] * ba[1]) / total_v
            return (bb[0] + ba[0]) / 2.0
        return None

    def get_depth(self, levels: int = 20) -> Dict:
        """
        Returns structured top-N depth with cumulative size,
        cumulative USD value, and visual depth percentages.
        """
        if self._is_dirty:
            self._rebuild_cache()

        bids_slice = self._cached_bids[:levels]
        asks_slice = self._cached_asks[:levels]

        # Calculate bids with cumulative sums
        cum_bid_vol = 0.0
        cum_bid_usd = 0.0
        formatted_bids = []
        for p, q in bids_slice:
            cum_bid_vol += q
            usd_val = p * q
            cum_bid_usd += usd_val
            formatted_bids.append({
                "price": p,
                "quantity": q,
                "cum_quantity": cum_bid_vol,
                "usd_value": usd_val,
                "cum_usd": cum_bid_usd
            })

        # Calculate asks with cumulative sums
        cum_ask_vol = 0.0
        cum_ask_usd = 0.0
        formatted_asks = []
        for p, q in asks_slice:
            cum_ask_vol += q
            usd_val = p * q
            cum_ask_usd += usd_val
            formatted_asks.append({
                "price": p,
                "quantity": q,
                "cum_quantity": cum_ask_vol,
                "usd_value": usd_val,
                "cum_usd": cum_ask_usd
            })

        max_cum_usd = max(cum_bid_usd, cum_ask_usd, 1.0)
        for b in formatted_bids:
            b["depth_pct"] = min(100.0, (b["cum_usd"] / max_cum_usd) * 100.0)
        for a in formatted_asks:
            a["depth_pct"] = min(100.0, (a["cum_usd"] / max_cum_usd) * 100.0)

        bb = self.best_bid
        ba = self.best_ask

        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "best_bid": bb[0] if bb else 0.0,
            "best_ask": ba[0] if ba else 0.0,
            "mid_price": self.mid_price or 0.0,
            "micro_price": self.micro_price or 0.0,
            "spread_abs": self.spread_abs,
            "spread_bps": round(self.spread_bps, 2),
            "imbalance": round(self.order_book_imbalance, 4),
            "bids": formatted_bids,
            "asks": formatted_asks,
            "total_bid_liquidity_usd": cum_bid_usd,
            "total_ask_liquidity_usd": cum_ask_usd,
            "last_update_id": self.last_update_id,
            "timestamp_ns": self.last_update_time_ns
        }

    def walk_book(self, side: str, order_size_usd: float) -> Tuple[float, float, float, bool]:
        """
        Simulates walking the order book for an order of size `order_size_usd`.
        Returns:
          - vwap_price: Volume-Weighted Average Price executed
          - filled_usd: Total USD filled (up to order_size_usd or total book depth)
          - slippage_bps: Slippage relative to best bid/ask in basis points
          - fully_filled: Boolean whether order was fully filled
        """
        if self._is_dirty:
            self._rebuild_cache()

        if side.upper() == "BUY":
            # Buying walks the ASKS (lowest to highest)
            levels = self._cached_asks
            if not levels:
                return (0.0, 0.0, 0.0, False)
            best_price = levels[0][0]
        else:
            # Selling walks the BIDS (highest to lowest)
            levels = self._cached_bids
            if not levels:
                return (0.0, 0.0, 0.0, False)
            best_price = levels[0][0]

        remaining_usd = order_size_usd
        total_qty_filled = 0.0
        total_usd_filled = 0.0

        for price, qty in levels:
            level_usd = price * qty
            if remaining_usd <= level_usd:
                # Partial level fill completes order
                needed_qty = remaining_usd / price
                total_qty_filled += needed_qty
                total_usd_filled += remaining_usd
                remaining_usd = 0.0
                break
            else:
                # Full level fill
                total_qty_filled += qty
                total_usd_filled += level_usd
                remaining_usd -= level_usd

        if total_qty_filled <= 0:
            return (best_price, 0.0, 0.0, False)

        vwap_price = total_usd_filled / total_qty_filled
        fully_filled = (remaining_usd <= 1e-4)

        if side.upper() == "BUY":
            # For BUY, higher price is worse slippage
            slippage_bps = ((vwap_price - best_price) / best_price) * 10000.0 if best_price > 0 else 0.0
        else:
            # For SELL, lower price is worse slippage
            slippage_bps = ((best_price - vwap_price) / best_price) * 10000.0 if best_price > 0 else 0.0

        return (vwap_price, total_usd_filled, max(0.0, slippage_bps), fully_filled)

    def compute_slippage_curve(self, capital_tiers: List[float] = None) -> List[Dict]:
        """Calculates VWAP and slippage for standard capital tiers ($1k, $5k, $10k, $50k, $100k)."""
        if capital_tiers is None:
            capital_tiers = [1000.0, 5000.0, 10000.0, 25000.0, 50000.0, 100000.0]

        results = []
        for cap in capital_tiers:
            buy_vwap, buy_filled, buy_slip, buy_ok = self.walk_book("BUY", cap)
            sell_vwap, sell_filled, sell_slip, sell_ok = self.walk_book("SELL", cap)
            results.append({
                "capital_usd": cap,
                "buy_vwap": buy_vwap,
                "buy_slippage_bps": round(buy_slip, 2),
                "buy_fully_filled": buy_ok,
                "sell_vwap": sell_vwap,
                "sell_slippage_bps": round(sell_slip, 2),
                "sell_fully_filled": sell_ok,
            })
        return results
