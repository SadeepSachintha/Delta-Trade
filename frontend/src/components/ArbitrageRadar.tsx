import React, { useState } from 'react';
import { ArrowRight, Radio, Sparkles, TrendingUp } from 'lucide-react';

interface Leg {
  step: number;
  from_currency: string;
  to_currency: string;
  exchange: string;
  action: string;
  symbol: string;
  rate: number;
  vwap: number;
  fee_rate: number;
  slippage_bps: number;
  input_amount: number;
  output_amount: number;
}

interface ArbitrageRoute {
  route_id: string;
  route_type: string;
  path: string[];
  exchanges: string[];
  gross_spread_bps: number;
  net_spread_bps: number;
  optimal_size_usd: number;
  expected_profit_usd: number;
  total_fee_drag_usd: number;
  total_slippage_drag_usd: number;
  cycle_latency_us: number;
  legs: Leg[];
}

interface ArbitrageRadarProps {
  opportunities: ArbitrageRoute[];
  onExecuteTrade: (route: ArbitrageRoute, capital: number) => void;
  isExecuting: boolean;
}

export const ArbitrageRadar: React.FC<ArbitrageRadarProps> = ({
  opportunities,
  onExecuteTrade,
  isExecuting,
}) => {
  const [selectedCapital, setSelectedCapital] = useState<number>(10000);
  const [filterType, setFilterType] = useState<string>('ALL');

  const filteredOpportunities = opportunities.filter((op) => {
    if (filterType === 'ALL') return true;
    return op.route_type === filterType;
  });

  return (
    <div className="glass-panel p-4 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Arbitrage Radar & Opportunities
          </h2>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-500/30">
            {opportunities.length} Active
          </span>
        </div>

        {/* Filter & Capital selector */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex rounded-md bg-slate-900 border border-slate-800 p-0.5">
            {['ALL', 'TRIANGULAR', 'SPATIAL'].map((f) => (
              <button
                key={f}
                onClick={() => setFilterType(f)}
                className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                  filterType === f
                    ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          <select
            value={selectedCapital}
            onChange={(e) => setSelectedCapital(Number(e.target.value))}
            className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[11px] font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value={1000}>$1,000</option>
            <option value={5000}>$5,000</option>
            <option value={10000}>$10,000</option>
            <option value={25000}>$25,000</option>
            <option value={50000}>$50,000</option>
          </select>
        </div>
      </div>

      {/* Routes List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 max-h-[380px]">
        {filteredOpportunities.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-slate-500 text-xs font-mono border border-dashed border-slate-800 rounded-lg">
            <Sparkles className="w-6 h-6 text-slate-600 mb-2 animate-bounce" />
            <span>Scanning Level-2 order books across venues...</span>
            <span className="text-[10px] text-slate-600 mt-1">Bellman-Ford negative-cycle solver running sub-5ms</span>
          </div>
        ) : (
          filteredOpportunities.map((op) => {
            const isTriangular = op.route_type === 'TRIANGULAR';
            const scale = selectedCapital / op.optimal_size_usd;
            const scaledProfit = op.expected_profit_usd * scale;
            const scaledFees = op.total_fee_drag_usd * scale;
            const scaledSlippage = op.total_slippage_drag_usd * scale;

            return (
              <div
                key={op.route_id}
                className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-cyan-500/40 transition-all hover:bg-slate-900/90 group"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  {/* Route Type & Path */}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                        isTriangular
                          ? 'bg-cyan-950/80 text-cyan-400 border border-cyan-500/40'
                          : 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                      }`}
                    >
                      {op.route_type}
                    </span>

                    <div className="flex items-center gap-1 text-xs font-mono text-slate-200 font-semibold">
                      {op.path.map((curr, idx) => (
                        <React.Fragment key={idx}>
                          <span className="text-cyan-300">{curr}</span>
                          {idx < op.path.length - 1 && (
                            <ArrowRight className="w-3 h-3 text-slate-500" />
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>

                  {/* Net Spread Bps Pill */}
                  <div className="flex items-center gap-1.5">
                    <div className="text-right">
                      <div className="text-xs font-mono font-extrabold text-emerald-400">
                        +{op.net_spread_bps.toFixed(2)} bps
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        Gross: +{op.gross_spread_bps.toFixed(2)} bps
                      </div>
                    </div>
                  </div>
                </div>

                {/* Venues & Leg Sequence */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 my-2 py-1.5 px-2 bg-slate-950/70 rounded border border-slate-900 text-[11px] font-mono">
                  {op.legs.map((leg) => (
                    <div key={leg.step} className="flex flex-col">
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span className="font-semibold text-slate-300">
                          Leg {leg.step}: {leg.action} {leg.symbol}
                        </span>
                        <span className="text-cyan-400">{leg.exchange}</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400 text-[10px] mt-0.5">
                        <span>VWAP: {leg.vwap}</span>
                        <span className="text-amber-400/90">+{leg.slippage_bps.toFixed(1)}bps slip</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Financial Summary & Action Footer */}
                <div className="flex items-center justify-between pt-1 text-xs font-mono">
                  <div className="flex items-center gap-3 text-[11px]">
                    <div>
                      <span className="text-slate-500">Exp. Net: </span>
                      <span className="font-bold text-emerald-400">
                        +${scaledProfit.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-slate-500 hidden sm:inline">
                      Fees: <span className="text-slate-400">-${scaledFees.toFixed(2)}</span>
                    </div>
                    <div className="text-slate-500 hidden sm:inline">
                      Slippage: <span className="text-slate-400">-${scaledSlippage.toFixed(2)}</span>
                    </div>
                    <div className="text-slate-500">
                      Solver: <span className="text-cyan-400">{op.cycle_latency_us}µs</span>
                    </div>
                  </div>

                  <button
                    onClick={() => onExecuteTrade(op, selectedCapital)}
                    disabled={isExecuting}
                    className="btn-cyber btn-cyber-sm btn-cyber-green"
                  >
                    <TrendingUp className="w-3 h-3" />
                    <span>SIMULATE FILL</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
