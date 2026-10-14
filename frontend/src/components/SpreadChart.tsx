import React, { useEffect, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi, AreaSeries, ColorType, LineStyle } from 'lightweight-charts';
import { BarChart2 } from 'lucide-react';

interface SpreadChartProps {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  recentTrades?: any[];
}

export const SpreadChart: React.FC<SpreadChartProps> = ({
  selectedSymbol,
  onSelectSymbol,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const [currentSpreadBps, setCurrentSpreadBps] = useState<number>(8.4);

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

    // Seed historical spread data points
    const nowSec = Math.floor(Date.now() / 1000);
    const initialData = [];
    let baseVal = 7.5;
    for (let i = 60; i >= 0; i--) {
      baseVal += (Math.random() - 0.48) * 0.8;
      baseVal = Math.max(1.2, Math.min(28.0, baseVal));
      initialData.push({
        time: (nowSec - i * 2) as any,
        value: Number(baseVal.toFixed(2)),
      });
    }

    areaSeries.setData(initialData);
    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = areaSeries;

    // Real-time tick generator for spread basis
    const interval = setInterval(() => {
      const curTime = Math.floor(Date.now() / 1000);
      const delta = (Math.random() - 0.49) * 0.9;
      setCurrentSpreadBps((prev) => {
        const nextVal = Math.max(1.5, Math.min(32.0, Number((prev + delta).toFixed(2))));
        if (seriesRef.current) {
          seriesRef.current.update({
            time: curTime as any,
            value: nextVal,
          });
        }
        return nextVal;
      });
    }, 1000);

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
      clearInterval(interval);
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [selectedSymbol]);

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
