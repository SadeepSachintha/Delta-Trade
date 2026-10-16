import React, { useEffect, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi, AreaSeries, ColorType, LineStyle } from 'lightweight-charts';
import { BarChart2 } from 'lucide-react';

interface LiveSpreadInfo {
  spread_bps: number;
  mid_price: number;
  imbalance?: number;
  best_bid?: number;
  best_ask?: number;
}

interface SpreadChartProps {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  recentTrades?: any[];
  liveSpreadData?: LiveSpreadInfo;
}

export const SpreadChart: React.FC<SpreadChartProps> = ({
  selectedSymbol,
  onSelectSymbol,
  liveSpreadData,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const lastTimeRef = useRef<number>(0);
  const initialSpreadRef = useRef<number>(liveSpreadData?.spread_bps || 7.5);
  const [currentSpreadBps, setCurrentSpreadBps] = useState<number>(liveSpreadData?.spread_bps || 8.4);

  const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ETHBTC', 'SOLBTC', 'BNBUSDT'];

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create TradingView lightweight chart instance
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#090d14' },
        textColor: '#64748b',
        fontSize: 11,
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)', style: LineStyle.Dotted },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)', style: LineStyle.Dotted },
      },
      crosshair: {
        vertLine: { color: 'rgba(0, 240, 255, 0.4)', width: 1, style: LineStyle.Dashed },
        horzLine: { color: 'rgba(0, 240, 255, 0.4)', width: 1, style: LineStyle.Dashed },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.08)',
        timeVisible: true,
        secondsVisible: true,
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.08)',
        scaleMargins: { top: 0.15, bottom: 0.15 },
      },
      handleScroll: true,
      handleScale: true,
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(0, 240, 255, 0.35)',
      bottomColor: 'rgba(0, 240, 255, 0.01)',
      lineColor: '#00f0ff',
      lineWidth: 2,
      priceFormat: {
        type: 'custom',
        formatter: (price: number) => `${price.toFixed(2)} bps`,
      },
    });

    // Seed historical spread baseline points
    const nowSec = Math.floor(Date.now() / 1000);
    const initialData = [];
    const baseVal = initialSpreadRef.current;
    for (let i = 40; i >= 1; i--) {
      const historicalTime = nowSec - i;
      initialData.push({
        time: historicalTime as any,
        value: Number(baseVal.toFixed(2)),
      });
    }

    initialData.push({
      time: nowSec as any,
      value: Number(baseVal.toFixed(2)),
    });
    lastTimeRef.current = nowSec;

    areaSeries.setData(initialData);
    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = areaSeries;

    // Resize observer for responsive layout
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length > 0 && chartContainerRef.current) {
        window.requestAnimationFrame(() => {
          if (chartContainerRef.current && chartRef.current) {
            chartRef.current.applyOptions({
              width: chartContainerRef.current.clientWidth,
              height: chartContainerRef.current.clientHeight,
            });
          }
        });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [selectedSymbol]);

  // Handle incoming live spread updates from WebSocket
  useEffect(() => {
    if (!seriesRef.current || !liveSpreadData) return;
    const nowSec = Math.floor(Date.now() / 1000);

    // Monotonic time check required by TradingView Lightweight Charts
    if (nowSec <= lastTimeRef.current) return;
    lastTimeRef.current = nowSec;

    const liveVal = Number(liveSpreadData.spread_bps.toFixed(2));
    setCurrentSpreadBps(liveVal);
    try {
      seriesRef.current.update({
        time: nowSec as any,
        value: liveVal,
      });
    } catch {
      // Ignore timestamp overlap gracefully
    }
  }, [liveSpreadData]);


  return (
    <div className="glass-panel p-4 flex flex-col h-full min-h-[320px]">
      {/* Header Controls */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Cross-Exchange Basis & Spread Dynamics
          </h2>
          <div className="flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded bg-cyan-950/70 border border-cyan-500/30 text-cyan-300">
            <span>LIVE SPREAD:</span>
            <span className="font-bold text-emerald-400">+{currentSpreadBps.toFixed(2)} bps</span>
          </div>
        </div>

        {/* Symbol Selector Buttons */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {symbols.map((sym) => (
            <button
              key={sym}
              onClick={() => onSelectSymbol(sym)}
              className={`px-2 py-1 rounded text-[10px] font-mono transition-all ${
                selectedSymbol === sym
                  ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/50 shadow-sm shadow-cyan-500/20'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {sym}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="flex-1 w-full h-full relative" ref={chartContainerRef}>
        <div className="absolute top-2 left-2 z-10 pointer-events-none flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500">
            Basis: Binance vs Bybit vs OKX (Aggregated VWAP)
          </span>
        </div>
      </div>
    </div>
  );
};
