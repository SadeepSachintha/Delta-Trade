import React, { useEffect, useState } from 'react';
import { BookOpen, Cpu } from 'lucide-react';

interface DepthLevel {
  price: number;
  quantity: number;
  cum_quantity: number;
  usd_value: number;
  cum_usd: number;
  depth_pct: number;
}

interface OrderBookData {
  symbol: string;
  exchange: string;
  best_bid: number;
  best_ask: number;
  mid_price: number;
  micro_price: number;
  spread_abs: number;
  spread_bps: number;
  imbalance: number;
  bids: DepthLevel[];
  asks: DepthLevel[];
  total_bid_liquidity_usd: number;
  total_ask_liquidity_usd: number;
}

interface SlippageTier {
  capital_usd: number;
  buy_vwap: number;
  buy_slippage_bps: number;
  buy_fully_filled: boolean;
  sell_vwap: number;
  sell_slippage_bps: number;
  sell_fully_filled: boolean;
}

interface Level2OrderBookProps {
  symbol: string;
  selectedExchange: string;
  onSelectExchange: (exchange: string) => void;
  liveL2Data?: {
    exchange: string;
    symbol: string;
    depth: OrderBookData;
    slippage_curve: SlippageTier[];
  } | null;
}

export const Level2OrderBook: React.FC<Level2OrderBookProps> = ({
  symbol,
  selectedExchange,
  onSelectExchange,
  liveL2Data,
}) => {
  const [snapshotData, setSnapshotData] = useState<{ depth: OrderBookData | null; slippage_curve: SlippageTier[] }>({
    depth: null,
    slippage_curve: [],
  });
  const [activeTab, setActiveTab] = useState<'DEPTH' | 'SLIPPAGE'>('DEPTH');

  const exchanges = ['Binance', 'Bybit', 'OKX'];

  // Derive active orderbook from live WebSocket stream or fallback to REST snapshot
  const bookData = (liveL2Data && liveL2Data.exchange === selectedExchange && liveL2Data.symbol === symbol)
    ? liveL2Data.depth
    : snapshotData.depth;

  const slippageCurve = (liveL2Data && liveL2Data.exchange === selectedExchange && liveL2Data.symbol === symbol && liveL2Data.slippage_curve)
    ? liveL2Data.slippage_curve
    : snapshotData.slippage_curve;

  // Initial single snapshot fetch upon symbol/exchange change
  useEffect(() => {
    let isSubscribed = true;

    const fetchSnapshot = async () => {
      try {
        const res = await fetch(`/api/orderbook/${selectedExchange}/${symbol}`);
        if (!res.ok) return;
        const data = await res.json();
        if (isSubscribed) {
          setSnapshotData({
            depth: data.depth,
            slippage_curve: data.slippage_curve || [],
          });
        }
      } catch {
        // Fallback gracefully
      }
    };

    fetchSnapshot();
    return () => {
      isSubscribed = false;
    };
  }, [symbol, selectedExchange]);



  const imbalance = bookData?.imbalance || 0;
  const imbalancePct = (imbalance * 100).toFixed(1);

  return (
    <div className="glass-panel p-4 flex flex-col h-full">
      {/* Header & Controls */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            L2 Depth Reconstruction (Top 20)
          </h2>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
            {symbol}
          </span>
        </div>

        {/* Venue Selector */}
        <div className="flex items-center gap-1">
          {exchanges.map((ex) => (
            <button
              key={ex}
              onClick={() => onSelectExchange(ex)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                selectedExchange === ex
                  ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
              }`}
            >
              {ex}
            </button>
          ))}
          <div className="h-4 w-[1px] bg-slate-800 mx-1" />
          <button
            onClick={() => setActiveTab(activeTab === 'DEPTH' ? 'SLIPPAGE' : 'DEPTH')}
            className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-300 hover:text-cyan-400 border border-slate-800"
          >
            {activeTab === 'DEPTH' ? 'SLIPPAGE CURVE' : 'ORDER BOOK'}
          </button>
        </div>
      </div>

      {/* Top Telemetry: Micro-Price & Imbalance Gauge */}
      <div className="grid grid-cols-3 gap-2 mb-3 p-2 bg-slate-950/70 rounded border border-slate-900 text-center font-mono">
        <div>
          <div className="text-[9px] text-slate-500 uppercase">Spread (bps)</div>
          <div className="text-xs font-bold text-cyan-400">
            {bookData ? `${bookData.spread_bps.toFixed(2)} bps` : '--'}
          </div>
        </div>
        <div>
          <div className="text-[9px] text-slate-500 uppercase">Micro-Price (VWAP Mid)</div>
          <div className="text-xs font-bold text-slate-200">
            {bookData ? `$${bookData.micro_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}` : '--'}
          </div>
        </div>
        <div>
          <div className="text-[9px] text-slate-500 uppercase">Order Imbalance</div>
          <div className={`text-xs font-bold ${imbalance >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {imbalance >= 0 ? `+${imbalancePct}% (BUY)` : `${imbalancePct}% (SELL)`}
          </div>
        </div>
      </div>

      {/* Main Content: Depth Book OR Non-Linear Slippage Curve */}
      {activeTab === 'DEPTH' ? (
        <div className="flex-1 flex flex-col font-mono text-[11px]">
          {/* Table Headers */}
          <div className="grid grid-cols-3 text-[10px] text-slate-500 pb-1 px-2 uppercase tracking-wider border-b border-slate-900">
            <span>Price (USD)</span>
            <span className="text-right">Size</span>
            <span className="text-right">Total Depth ($)</span>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[300px] divide-y divide-slate-950">
            {/* ASKS (Reversed so lowest ask is at bottom) */}
            <div className="flex flex-col-reverse">
              {bookData?.asks.slice(0, 10).map((ask, idx) => (
                <div key={idx} className="relative grid grid-cols-3 px-2 py-0.5 text-rose-400/90 hover:bg-rose-950/20">
                  <div
                    className="depth-bar-ask"
                    style={{ width: `${ask.depth_pct}%` }}
                  />
                  <span className="font-semibold z-10">{ask.price.toFixed(2)}</span>
                  <span className="text-right text-slate-300 z-10">{ask.quantity.toFixed(4)}</span>
                  <span className="text-right text-slate-400 z-10">${(ask.cum_usd / 1000).toFixed(1)}k</span>
                </div>
              ))}
            </div>

            {/* Mid Price Ribbon */}
            <div className="py-1 px-2 bg-slate-900/90 flex items-center justify-between text-xs font-bold text-slate-300 border-y border-slate-800">
              <span className="text-cyan-400">
                MID: ${bookData?.mid_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-[10px] text-slate-500 font-normal">
                Δ ${(bookData?.spread_abs || 0).toFixed(2)}
              </span>
            </div>

            {/* BIDS */}
            <div>
              {bookData?.bids.slice(0, 10).map((bid, idx) => (
                <div key={idx} className="relative grid grid-cols-3 px-2 py-0.5 text-emerald-400/90 hover:bg-emerald-950/20">
                  <div
                    className="depth-bar-bid"
                    style={{ width: `${bid.depth_pct}%` }}
                  />
                  <span className="font-semibold z-10">{bid.price.toFixed(2)}</span>
                  <span className="text-right text-slate-300 z-10">{bid.quantity.toFixed(4)}</span>
                  <span className="text-right text-slate-400 z-10">${(bid.cum_usd / 1000).toFixed(1)}k</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Non-Linear VWAP Slippage Curve Table */
        <div className="flex-1 font-mono text-xs overflow-y-auto">
          <div className="text-[10px] text-slate-400 mb-2 p-2 bg-slate-950 rounded border border-slate-900 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>Simulated VWAP slippage curve walking reconstructed depth levels</span>
          </div>

          <table className="w-full text-[11px] text-left divide-y divide-slate-800">
            <thead className="text-[10px] text-slate-500 uppercase">
              <tr>
                <th className="py-1">Order Size</th>
                <th className="py-1 text-right">Buy VWAP</th>
                <th className="py-1 text-right">Buy Slip</th>
                <th className="py-1 text-right">Sell VWAP</th>
                <th className="py-1 text-right">Sell Slip</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900">
              {slippageCurve.map((tier) => (
                <tr key={tier.capital_usd} className="hover:bg-slate-900/60">
                  <td className="py-1.5 font-bold text-slate-200">
                    ${(tier.capital_usd / 1000).toFixed(0)}k
                  </td>
                  <td className="py-1.5 text-right text-rose-400">
                    ${tier.buy_vwap.toFixed(2)}
                  </td>
                  <td className="py-1.5 text-right font-bold text-amber-400">
                    +{tier.buy_slippage_bps.toFixed(1)} bps
                  </td>
                  <td className="py-1.5 text-right text-emerald-400">
                    ${tier.sell_vwap.toFixed(2)}
                  </td>
                  <td className="py-1.5 text-right font-bold text-amber-400">
                    +{tier.sell_slippage_bps.toFixed(1)} bps
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
