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
  const [killSwitch, setKillSwitch] = useState<boolean>(config?.kill_switch || false);

  if (!isOpen) return null;

  const handleApplyPreset = (latency: number, minSpread: number, capital: number) => {
    setLatencyMs(latency);
    setMinSpreadBps(minSpread);
    setCapitalUsd(capital);
  };

  const handleSave = () => {
    onSaveConfig({
      simulated_latency_ms: latencyMs,
      auto_min_spread_bps: minSpreadBps,
      auto_trade_capital_usd: capitalUsd,
      kill_switch: killSwitch,
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

        {/* Quick Presets */}
        <div className="mb-4">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1.5">
            Institutional Strategy Presets
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleApplyPreset(3.0, 3.0, 5000)}
              className="px-2 py-1.5 rounded bg-slate-900 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/40 text-[10px] font-mono text-slate-300 transition-colors"
            >
              ⚡ Scalper (3ms)
            </button>
            <button
              type="button"
              onClick={() => handleApplyPreset(14.5, 6.0, 10000)}
              className="px-2 py-1.5 rounded bg-slate-900 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/40 text-[10px] font-mono text-slate-300 transition-colors"
            >
              ⚖️ Standard (14ms)
            </button>
            <button
              type="button"
              onClick={() => handleApplyPreset(25.0, 12.0, 25000)}
              className="px-2 py-1.5 rounded bg-slate-900 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/40 text-[10px] font-mono text-slate-300 transition-colors"
            >
              🛡️ Safe (25ms)
            </button>
          </div>
        </div>

        {/* Form Fields */}
        <div className="space-y-4 font-mono text-xs">
          {/* Emergency Kill Switch */}
          <div className={`p-3 rounded-lg border transition-all ${
            killSwitch
              ? 'bg-rose-950/40 border-rose-500/80 shadow-lg shadow-rose-950/30'
              : 'bg-slate-900/60 border-slate-800'
          }`}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${killSwitch ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'}`} />
                <span className="font-bold text-slate-200">Emergency Kill Switch</span>
              </div>
              <button
                type="button"
                onClick={() => setKillSwitch(!killSwitch)}
                className={`px-3 py-1 rounded text-[11px] font-bold transition-all ${
                  killSwitch
                    ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-600/40'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                }`}
              >
                {killSwitch ? 'HALTED (ENGAGED)' : 'DISENGAGED'}
              </button>
            </div>
            <div className="text-[10px] text-slate-400">
              Immediately halts all automated bots and rejects execution orders across Python engine and PHP Risk console.
            </div>
          </div>

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

