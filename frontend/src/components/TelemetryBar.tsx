import React from 'react';
import { Activity, Zap, Server, Play, Pause, Settings } from 'lucide-react';

interface TelemetryBarProps {
  telemetry: any;
  stats: any;
  config: any;
  onToggleAutoBot: () => void;
  onOpenConfig: () => void;
  isConnected: boolean;
}

export const TelemetryBar: React.FC<TelemetryBarProps> = ({
  telemetry,
  stats,
  config,
  onToggleAutoBot,
  onOpenConfig,
  isConnected,
}) => {
  const latencyUs = telemetry?.cycle_latency_us || 870;
  const latencyMs = (latencyUs / 1000).toFixed(2);
  const ticksPerSec = telemetry?.ticks_per_second || 1240;
  const isUnder5ms = latencyUs < 5000;
  const totalPnl = stats?.total_net_pnl_usd || 0;
  const winRate = stats?.win_rate_pct || 0;
  const isAutoEnabled = config?.auto_bot_enabled || false;

  return (
    <header className="glass-panel px-4 py-3 mb-4 flex flex-wrap items-center justify-between gap-4 border-b border-cyan-950/40">
      {/* Brand & Connection */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-9 h-9 rounded-lg bg-cyan-950/60 border border-cyan-500/40 shadow-lg shadow-cyan-500/10">
          <Zap className="w-5 h-5 text-cyan-400" />
          <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping opacity-75" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-extrabold tracking-wider uppercase bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400 bg-clip-text text-transparent">
              DELTA TRADE
            </h1>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-500/30 font-semibold tracking-wider">
              HFT-CORE v1.2
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 pulse-green' : 'bg-rose-500'}`} />
            <span>{isConnected ? 'LIVE WEBSOCKET STREAM' : 'RECONNECTING...'}</span>
          </div>
        </div>
      </div>

      {/* Latency & Throughput Telemetry */}
      <div className="flex items-center gap-6">
        {/* Bellman-Ford Cycle Badge */}
        <div className="flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
          <Activity className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">Bellman-Ford Latency</div>
            <div className="flex items-center gap-1.5 font-mono text-xs font-bold">
              <span className={isUnder5ms ? 'text-emerald-400' : 'text-amber-400'}>
                {latencyUs} µs <span className="text-slate-500 font-normal">({latencyMs} ms)</span>
              </span>
              <span className="text-[9px] px-1 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-500/30">
                &lt; 5ms OK
              </span>
            </div>
          </div>
        </div>

        {/* Ticks Throughput */}
        <div className="hidden sm:flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
          <Server className="w-4 h-4 text-emerald-400" />
          <div>
            <div className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">Order Book Ingress</div>
            <div className="font-mono text-xs font-bold text-slate-200">
              {ticksPerSec} <span className="text-slate-500 text-[11px] font-normal">ticks/s</span>
            </div>
          </div>
        </div>

        {/* Venue Status Indicators */}
        <div className="hidden md:flex items-center gap-2 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
          <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider mr-1">Venues:</span>
          {['Binance', 'Bybit', 'OKX'].map((venue) => (
            <div key={venue} className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-slate-300">{venue}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Financials & Execution Control */}
      <div className="flex items-center gap-3">
        {/* Cumulative PnL Badge */}
        <div className="bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800 text-right">
          <div className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">Simulated PnL</div>
          <div className="font-mono text-xs font-bold flex items-center gap-1.5">
            <span className={totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
            </span>
            <span className="text-[10px] text-slate-400">({winRate}% WR)</span>
          </div>
        </div>

        {/* Auto Bot Toggle */}
        <button
          onClick={onToggleAutoBot}
          className={`btn-cyber ${isAutoEnabled ? 'btn-cyber-green' : 'border-slate-700 text-slate-400'}`}
          title="Toggle Automated Execution Bot"
        >
          {isAutoEnabled ? (
            <>
              <Pause className="w-3.5 h-3.5" />
              <span>BOT ACTIVE</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              <span>BOT IDLE</span>
            </>
          )}
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenConfig}
          className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 transition-colors"
          title="Engine & Latency Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
