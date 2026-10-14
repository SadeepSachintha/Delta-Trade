import React from 'react';
import { Network } from 'lucide-react';

interface MatrixData {
  currencies: string[];
  rates: number[][];
  log_weights: number[][];
}

interface MatrixHeatmapProps {
  matrix: MatrixData | null;
  activePath?: string[];
}

export const MatrixHeatmap: React.FC<MatrixHeatmapProps> = ({ matrix, activePath }) => {
  const currencies = matrix?.currencies || ['USDT', 'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE'];
  const rates = matrix?.rates || [];
  const logWeights = matrix?.log_weights || [];

  const isEdgeInCycle = (fromCurr: string, toCurr: string) => {
    if (!activePath || activePath.length < 2) return false;
    for (let i = 0; i < activePath.length - 1; i++) {
      if (activePath[i] === fromCurr && activePath[i + 1] === toCurr) {
        return true;
      }
    }
    return false;
  };

  return (
    <div className="glass-panel p-4 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Currency Adjacency Matrix & Negative Cycles
          </h2>
        </div>
        <div className="text-[10px] font-mono text-slate-500 flex items-center gap-2">
          <span>Formula: W(u,v) = -ln(R)</span>
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <span className="text-cyan-400 font-semibold">Active Cycle Edge</span>
        </div>
      </div>

      {/* Grid Heatmap Table */}
      <div className="flex-1 overflow-x-auto font-mono text-xs">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-1.5 text-slate-500 font-normal text-[10px] border border-slate-900 bg-slate-950/80">
                FROM \ TO
              </th>
              {currencies.map((c) => (
                <th
                  key={c}
                  className="p-1.5 font-bold text-slate-300 text-[11px] border border-slate-900 bg-slate-950/80 text-center"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {currencies.map((fromCurr, i) => (
              <tr key={fromCurr}>
                <td className="p-1.5 font-bold text-slate-300 text-[11px] border border-slate-900 bg-slate-950/80 text-left">
                  {fromCurr}
                </td>
                {currencies.map((toCurr, j) => {
                  if (i === j) {
                    return (
                      <td
                        key={toCurr}
                        className="p-1.5 text-center text-slate-600 border border-slate-900 bg-slate-950/40 text-[10px]"
                      >
                        1.0000
                      </td>
                    );
                  }

                  const rate = rates[i]?.[j] || 0;
                  const logW = logWeights[i]?.[j] || 0;
                  const inCycle = isEdgeInCycle(fromCurr, toCurr);

                  return (
                    <td
                      key={toCurr}
                      className={`p-1 text-center border border-slate-900 transition-all ${
                        inCycle
                          ? 'bg-cyan-500/30 border-cyan-400 shadow-sm shadow-cyan-400/30'
                          : 'hover:bg-slate-800/60'
                      }`}
                      title={`${fromCurr} -> ${toCurr} | Rate: ${rate} | Log Weight: ${logW}`}
                    >
                      <div className="flex flex-col items-center">
                        <span className={`font-semibold text-[11px] ${inCycle ? 'text-cyan-300' : 'text-slate-200'}`}>
                          {rate < 0.001 ? rate.toExponential(2) : rate < 10 ? rate.toFixed(4) : rate.toFixed(1)}
                        </span>
                        <span className="text-[9px] text-slate-500">
                          {logW.toFixed(2)}
                        </span>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
