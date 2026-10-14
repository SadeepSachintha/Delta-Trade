import React, { useState } from 'react';
import { X, Sliders, AlertTriangle } from 'lucide-react';

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: any;
  onSaveConfig: (newConfig: any) => void;
}

export const ConfigModal: React.FC<ConfigModalProps> = ({
  isOpen,
  onClose,
  config,
  onSaveConfig,
}) => {
  const [latencyMs, setLatencyMs] = useState<number>(config?.simulated_latency_ms || 14.5);
  const [minSpreadBps, setMinSpreadBps] = useState<number>(config?.auto_min_spread_bps || 6.0);
  const [capitalUsd, setCapitalUsd] = useState<number>(config?.auto_trade_capital_usd || 10000.0);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveConfig({
      simulated_latency_ms: latencyMs,
      auto_min_spread_bps: minSpreadBps,
      auto_trade_capital_usd: capitalUsd,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md p-5 border border-cyan-500/30 shadow-2xl shadow-cyan-950/50">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-100">
              HFT Simulation & Risk Parameters
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-100 rounded hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Fields */}
        <div className="space-y-4 font-mono text-xs">
          {/* Latency Slider */}
          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Simulated Execution Queue Latency:</span>
              <span className="font-bold text-cyan-400">{latencyMs.toFixed(1)} ms</span>
            </div>
            <input
              type="range"
              min="2.0"
              max="50.0"
              step="0.5"
              value={latencyMs}
              onChange={(e) => setLatencyMs(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
              <span>2.0ms (Co-located Colocation)</span>
              <span>50.0ms (Cross-Regional Transit)</span>
            </div>
          </div>

          {/* Min Spread Threshold */}
          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Auto-Execution Min Net Spread:</span>
              <span className="font-bold text-emerald-400">+{minSpreadBps.toFixed(1)} bps</span>
            </div>
            <input
              type="range"
              min="2.0"
              max="25.0"
              step="0.5"
              value={minSpreadBps}
              onChange={(e) => setMinSpreadBps(Number(e.target.value))}
              className="w-full accent-emerald-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
              <span>2.0 bps (Aggressive)</span>
              <span>25.0 bps (Conservative)</span>
            </div>
          </div>

          {/* Capital Tier */}
          <div>
            <div className="text-slate-300 mb-1">Default Order Size:</div>
            <div className="grid grid-cols-4 gap-2">
              {[2500, 5000, 10000, 25000].map((cap) => (
                <button
                  key={cap}
                  type="button"
                  onClick={() => setCapitalUsd(cap)}
                  className={`py-1.5 rounded text-center transition-colors ${
                    capitalUsd === cap
                      ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/50'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  ${(cap / 1000).toFixed(1)}k
                </button>
              ))}
            </div>
          </div>

          {/* Adverse Selection Note */}
          <div className="p-2.5 rounded bg-amber-950/20 border border-amber-500/30 text-amber-300/90 text-[11px] flex gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold">Adverse Selection Active (8%)</div>
              <div className="text-[10px] text-amber-400/80">
                Simulates real-world book shifting against the order during queue latency, resulting in slippage degradation.
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 mt-5 pt-3 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 font-mono text-xs"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="btn-cyber btn-cyber-sm btn-cyber-green"
          >
            Apply Parameters
          </button>
        </div>
      </div>
    </div>
  );
};
