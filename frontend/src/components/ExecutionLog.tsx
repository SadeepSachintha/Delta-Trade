import React, { useState } from 'react';
import { History, CheckCircle2, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react';

interface ExecutionLeg {
  step: number;
  exchange: string;
  symbol: string;
  action: string;
  vwap: number;
  slippage_bps: number;
  fee_usd: number;
  amount_in: number;
  amount_out: number;
}

interface SimulatedExecution {
  id: string;
  route_id: string;
  route_type: string;
  path: string[];
  venues: string[];
  capital_usd: number;
  gross_pnl_usd: number;
  fee_drag_usd: number;
  slippage_drag_usd: number;
  net_pnl_usd: number;
  roi_bps: number;
  fill_status: string;
  execution_latency_ms: number;
  created_at?: string;
  legs?: ExecutionLeg[];
}

interface ExecutionLogProps {
  executions: SimulatedExecution[];
  stats: any;
}

export const ExecutionLog: React.FC<ExecutionLogProps> = ({ executions, stats }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="glass-panel p-4 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Simulated Execution Log & PnL Accounting
          </h2>
        </div>

        {/* Quick Stats Pills */}
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
            Trades: <strong className="text-slate-200">{stats?.total_trades || 0}</strong>
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
            Win Rate: <strong className="text-emerald-400">{stats?.win_rate_pct || 0}%</strong>
          </span>
          <span className="px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-500/40 text-emerald-400 font-bold">
            Net PnL: ${stats?.total_net_pnl_usd ? stats.total_net_pnl_usd.toFixed(2) : '0.00'}
          </span>
        </div>
      </div>

      {/* Execution Stream Table */}
      <div className="flex-1 overflow-y-auto max-h-[360px] font-mono text-xs">
        <table className="w-full text-left border-collapse">
          <thead className="text-[10px] text-slate-500 uppercase sticky top-0 bg-slate-950/90 backdrop-blur z-10 border-b border-slate-900">
            <tr>
              <th className="py-2 px-2">Exec ID</th>
              <th className="py-2 px-2">Route & Path</th>
              <th className="py-2 px-2 text-right">Capital</th>
              <th className="py-2 px-2 text-right">Net PnL</th>
              <th className="py-2 px-2 text-right">ROI (bps)</th>
              <th className="py-2 px-2 text-center">Latency</th>
              <th className="py-2 px-2 text-center">Status</th>
              <th className="py-2 px-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900/80">
            {executions.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500">
                  No simulated executions logged yet. Click "Simulate Fill" or enable the Bot.
                </td>
              </tr>
            ) : (
              executions.map((trade) => {
                const isProfit = trade.net_pnl_usd >= 0;
                const isExpanded = expandedId === trade.id;

                return (
                  <React.Fragment key={trade.id}>
                    <tr
                      onClick={() => toggleExpand(trade.id)}
                      className="hover:bg-slate-900/60 cursor-pointer transition-colors"
                    >
                      <td className="py-2 px-2 text-cyan-400 font-semibold text-[11px]">
                        {trade.id}
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-300">
                            {trade.route_type}
                          </span>
                          <span className="text-slate-200">
                            {trade.path ? trade.path.join(' → ') : '--'}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 px-2 text-right text-slate-300">
                        ${trade.capital_usd ? trade.capital_usd.toLocaleString() : '10,000'}
                      </td>
                      <td
                        className={`py-2 px-2 text-right font-bold ${
                          isProfit ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isProfit ? '+' : ''}${trade.net_pnl_usd ? trade.net_pnl_usd.toFixed(2) : '0.00'}
                      </td>
                      <td className="py-2 px-2 text-right font-semibold text-slate-300">
                        {isProfit ? '+' : ''}{trade.roi_bps ? trade.roi_bps.toFixed(2) : '0.00'} bps
                      </td>
                      <td className="py-2 px-2 text-center text-slate-400 text-[11px]">
                        {trade.execution_latency_ms ? `${trade.execution_latency_ms.toFixed(1)}ms` : '14ms'}
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            trade.fill_status === 'FILLED'
                              ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/30'
                              : 'bg-amber-950/70 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {trade.fill_status === 'FILLED' ? (
                            <CheckCircle2 className="w-2.5 h-2.5" />
                          ) : (
                            <AlertCircle className="w-2.5 h-2.5" />
                          )}
                          {trade.fill_status}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-slate-500">
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </td>
                    </tr>

                    {/* Expandable Multi-Leg Details */}
                    {isExpanded && (
                      <tr className="bg-slate-950/80">
                        <td colSpan={8} className="p-3">
                          <div className="border border-slate-800 rounded p-3 bg-slate-950/50">
                            <div className="text-[10px] uppercase font-bold text-slate-400 mb-2 flex items-center justify-between">
                              <span>Multi-Leg Execution & VWAP Slippage Breakdown</span>
                              <div className="flex items-center gap-3 text-slate-500">
                                <span>Fee Drag: -${trade.fee_drag_usd ? trade.fee_drag_usd.toFixed(2) : '0.00'}</span>
                                <span>Slippage Drag: -${trade.slippage_drag_usd ? trade.slippage_drag_usd.toFixed(2) : '0.00'}</span>
                                <span>Gross PnL: +${trade.gross_pnl_usd ? trade.gross_pnl_usd.toFixed(2) : '0.00'}</span>
                              </div>
                            </div>

                            {trade.legs && trade.legs.length > 0 ? (
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                                {trade.legs.map((leg) => (
                                  <div
                                    key={leg.step}
                                    className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px]"
                                  >
                                    <div className="flex justify-between items-center text-slate-300 font-semibold mb-1">
                                      <span>Leg {leg.step}: {leg.action} {leg.symbol}</span>
                                      <span className="text-cyan-400">{leg.exchange}</span>
                                    </div>
                                    <div className="text-slate-400 text-[10px] space-y-0.5">
                                      <div className="flex justify-between">
                                        <span>VWAP Exec:</span>
                                        <span className="text-slate-200">{leg.vwap}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span>Slippage:</span>
                                        <span className="text-amber-400">+{leg.slippage_bps.toFixed(1)} bps</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span>Fee:</span>
                                        <span className="text-slate-300">${leg.fee_usd.toFixed(2)}</span>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-[10px] text-slate-500">
                                Route: {trade.path?.join(' -> ')} executed across venues: {trade.venues?.join(', ')}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
