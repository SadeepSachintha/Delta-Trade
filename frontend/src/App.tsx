import React, { useState, useEffect, useRef } from 'react';
import { TelemetryBar } from './components/TelemetryBar';
import { ArbitrageRadar } from './components/ArbitrageRadar';
import { SpreadChart } from './components/SpreadChart';
import { Level2OrderBook } from './components/Level2OrderBook';
import { MatrixHeatmap } from './components/MatrixHeatmap';
import { ExecutionLog } from './components/ExecutionLog';
import { ConfigModal } from './components/ConfigModal';

export const App: React.FC = () => {
  const [telemetry, setTelemetry] = useState<any>({
    cycle_latency_us: 870,
    cycle_latency_ms: 0.87,
    ticks_per_second: 1240,
    total_ticks: 45000,
    under_5ms: true,
  });
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [matrix, setMatrix] = useState<any>(null);
  const [executions, setExecutions] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({
    total_trades: 3,
    win_rate_pct: 100.0,
    total_net_pnl_usd: 75.50,
  });
  const [config, setConfig] = useState<any>({
    simulated_latency_ms: 14.5,
    auto_bot_enabled: false,
    auto_min_spread_bps: 6.0,
    auto_trade_capital_usd: 10000.0,
  });

  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  const [selectedExchange, setSelectedExchange] = useState<string>('Binance');
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket Connection & Real-Time Ingress
  useEffect(() => {
    let reconnectTimeout: any;

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // When running on vite dev port 5173, direct to backend 8000 or use vite proxy /ws
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'INITIAL_STATE') {
            if (data.telemetry) setTelemetry(data.telemetry);
            if (data.matrix) setMatrix(data.matrix);
            if (data.stats) setStats(data.stats);
            if (data.history) setExecutions(data.history);
            if (data.config) setConfig(data.config);
          } else if (data.type === 'MICRO_BATCH') {
            if (data.telemetry) setTelemetry(data.telemetry);
            if (data.opportunities) setOpportunities(data.opportunities);
          } else if (data.type === 'MATRIX') {
            setMatrix(data.matrix);
          } else if (data.type === 'EXECUTION') {
            if (data.trade) {
              setExecutions((prev) => [data.trade, ...prev.slice(0, 49)]);
            }
            if (data.stats) setStats(data.stats);
          } else if (data.type === 'CONFIG_UPDATE') {
            if (data.config) setConfig(data.config);
          }
        } catch (err) {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWs();

    // Initial REST fallback poll
    fetch('/api/opportunities')
      .then((res) => res.json())
      .then((data) => {
        if (data.routes) setOpportunities(data.routes);
        if (data.telemetry) setTelemetry(data.telemetry);
      })
      .catch(() => {});

    fetch('/api/history')
      .then((res) => res.json())
      .then((data) => {
        if (data.history) setExecutions(data.history);
        if (data.stats) setStats(data.stats);
      })
      .catch(() => {});

    fetch('/api/matrix')
      .then((res) => res.json())
      .then((data) => setMatrix(data))
      .catch(() => {});

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Trigger manual simulated execution
  const handleExecuteTrade = async (route: any, capital: number) => {
    setIsExecuting(true);
    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            action: 'SIMULATE_TRADE',
            route: route,
            capital_usd: capital,
          })
        );
      } else {
        const res = await fetch('/api/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ route_id: route.route_id, capital_usd: capital }),
        });
        const data = await res.json();
        if (data.trade) {
          setExecutions((prev) => [data.trade, ...prev.slice(0, 49)]);
          if (data.stats) setStats(data.stats);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setIsExecuting(false), 300);
    }
  };

  // Toggle Auto-Bot
  const handleToggleAutoBot = () => {
    const updated = {
      ...config,
      auto_bot_enabled: !config.auto_bot_enabled,
    };
    setConfig(updated);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'UPDATE_CONFIG',
          config: updated,
        })
      );
    }
  };

  // Save Config from modal
  const handleSaveConfig = (newConfig: any) => {
    const updated = { ...config, ...newConfig };
    setConfig(updated);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'UPDATE_CONFIG',
          config: updated,
        })
      );
    }
  };

  const activePath = opportunities[0]?.path;

  return (
    <div className="min-h-screen p-3 md:p-5 flex flex-col max-w-[1780px] mx-auto">
      {/* Top Telemetry Header */}
      <TelemetryBar
        telemetry={telemetry}
        stats={stats}
        config={config}
        onToggleAutoBot={handleToggleAutoBot}
        onOpenConfig={() => setIsConfigOpen(true)}
        isConnected={isConnected}
      />

      {/* Main Grid: Upper Tier */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
        {/* Left: Arbitrage Radar (Routes, Negative Cycles & Instant Execution) */}
        <div className="lg:col-span-6 h-[400px]">
          <ArbitrageRadar
            opportunities={opportunities}
            onExecuteTrade={handleExecuteTrade}
            isExecuting={isExecuting}
          />
        </div>

        {/* Right: TradingView Spread Basis Chart */}
        <div className="lg:col-span-6 h-[400px]">
          <SpreadChart
            selectedSymbol={selectedSymbol}
            onSelectSymbol={setSelectedSymbol}
            recentTrades={executions}
          />
        </div>
      </div>

      {/* Main Grid: Lower Tier */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-4 flex-1">
        {/* Level 2 Order Book Depth & VWAP Slippage Curve */}
        <div className="lg:col-span-4 min-h-[380px]">
          <Level2OrderBook
            symbol={selectedSymbol}
            selectedExchange={selectedExchange}
            onSelectExchange={setSelectedExchange}
          />
        </div>

        {/* Currency Adjacency Matrix & Negative Cycle Heatmap */}
        <div className="lg:col-span-4 min-h-[380px]">
          <MatrixHeatmap matrix={matrix} activePath={activePath} />
        </div>

        {/* Simulated Execution Log & Multi-Leg Fills */}
        <div className="lg:col-span-4 min-h-[380px]">
          <ExecutionLog executions={executions} stats={stats} />
        </div>
      </div>

      {/* Risk & Simulation Config Modal */}
      <ConfigModal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        config={config}
        onSaveConfig={handleSaveConfig}
      />
    </div>
  );
};

export default App;
