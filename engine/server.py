"""
High-Frequency Crypto Arbitrage Engine Server.
FastAPI + WebSockets distributing sub-millisecond market surveillance,
Bellman-Ford negative cycles, L2 order books, and execution simulation events.
"""

import asyncio
import json
import time
from typing import Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .feeds.market_feed_manager import MarketFeedManager
from .math_engine import ArbitrageMathEngine, ArbitrageRoute
from .state_store import StateStore
from .execution_simulator import ExecutionSimulator

app = FastAPI(title="Delta Trade HFT Arbitrage Engine", version="1.0.0")

# Enable CORS for local dev and frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
state_store = StateStore()
feed_manager = MarketFeedManager()
math_engine = ArbitrageMathEngine(feed_manager)
simulator = ExecutionSimulator(state_store, feed_manager)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Tuple[str, str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = ("Binance", "BTCUSDT")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, exchange: str, symbol: str):
        self.subscriptions[websocket] = (exchange, symbol)

    async def broadcast(self, message: Dict):
        if not self.active_connections:
            return
        payload = json.dumps(message)
        dead_sockets = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_sockets.add(connection)
        for dead in dead_sockets:
            self.active_connections.discard(dead)
            self.subscriptions.pop(dead, None)

ws_manager = ConnectionManager()

# Background broadcast task
background_task: asyncio.Task = None


@app.on_event("startup")
async def startup_event():
    global background_task
    await feed_manager.start()
    background_task = asyncio.create_task(run_hft_engine_loop())


@app.on_event("shutdown")
async def shutdown_event():
    global background_task
    if background_task:
        background_task.cancel()
    await feed_manager.stop()


async def run_hft_engine_loop():
    """
    Sub-second micro-batch arbitrage surveillance loop:
    - Re-evaluates Bellman-Ford negative cycles and spatial spreads (< 3ms).
    - Checks auto-execution bot triggers.
    - Broadcasts high-frequency state updates to all connected browser terminals.
    """
    loop_count = 0
    while True:
        try:
            loop_count += 1
            t0 = time.perf_counter_ns()
            
            # Run Bellman-Ford & Spatial scan
            routes, telemetry = math_engine.scan_all(test_capital_usd=simulator.auto_trade_capital_usd)
            
            # Check auto-execution bot
            auto_trade = simulator.evaluate_auto_arbitrage(routes)
            if auto_trade:
                await ws_manager.broadcast({
                    "type": "EXECUTION",
                    "trade": auto_trade,
                    "stats": state_store.get_aggregate_stats()
                })

            # Format route dictionaries for serialization
            serialized_routes = []
            for r in routes:
                serialized_routes.append({
                    "route_id": r.route_id,
                    "route_type": r.route_type,
                    "path": r.path,
                    "exchanges": r.exchanges,
                    "gross_spread_bps": r.gross_spread_bps,
                    "net_spread_bps": r.net_spread_bps,
                    "optimal_size_usd": r.optimal_size_usd,
                    "expected_profit_usd": r.expected_profit_usd,
                    "total_fee_drag_usd": r.total_fee_drag_usd,
                    "total_slippage_drag_usd": r.total_slippage_drag_usd,
                    "cycle_latency_us": r.cycle_latency_us,
                    "legs": [
                        {
                            "step": l.step,
                            "from_currency": l.from_currency,
                            "to_currency": l.to_currency,
                            "exchange": l.exchange,
                            "action": l.action,
                            "symbol": l.symbol,
                            "rate": l.rate,
                            "vwap": l.vwap,
                            "fee_rate": l.fee_rate,
                            "slippage_bps": l.slippage_bps,
                            "input_amount": l.input_amount,
                            "output_amount": l.output_amount
                        } for l in r.legs
                    ]
                })

            # Compute real-time top-of-book spreads across key pairs
            market_spreads = {}
            for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ETHBTC", "SOLBTC", "BNBUSDT"]:
                bk = feed_manager.get_order_book("Binance", s)
                if bk and bk.best_bid and bk.best_ask:
                    market_spreads[s] = {
                        "spread_bps": round(bk.spread_bps, 2),
                        "mid_price": round(bk.mid_price, 6 if (bk.mid_price or 0) < 10 else 2),
                        "imbalance": round(bk.order_book_imbalance, 4),
                        "best_bid": bk.best_bid[0],
                        "best_ask": bk.best_ask[0]
                    }

            # Broadcast opportunities and engine telemetry every ~100ms
            feed_telemetry = feed_manager.get_telemetry()
            await ws_manager.broadcast({
                "type": "MICRO_BATCH",
                "telemetry": {
                    **telemetry,
                    "ticks_per_second": feed_telemetry["ticks_per_second"],
                    "total_ticks": feed_telemetry["ticks_processed"],
                    "connections": len(ws_manager.active_connections)
                },
                "opportunities": serialized_routes,
                "market_spreads": market_spreads
            })

            # Every 2nd loop (~200ms), stream L2 depth directly to subscribed clients
            if loop_count % 2 == 0 and ws_manager.active_connections:
                sub_cache = {}
                for ws, (ex, sym) in list(ws_manager.subscriptions.items()):
                    if ws not in ws_manager.active_connections:
                        continue
                    if (ex, sym) not in sub_cache:
                        book = feed_manager.get_order_book(ex, sym)
                        if book:
                            quote_curr = "USDT"
                            for q in ["USDT", "BTC", "ETH"]:
                                if sym.endswith(q):
                                    quote_curr = q
                                    break
                            rate = math_engine.get_usd_value(quote_curr, 1.0)
                            sub_cache[(ex, sym)] = {
                                "type": "L2_UPDATE",
                                "exchange": ex,
                                "symbol": sym,
                                "depth": book.get_depth(levels=20),
                                "slippage_curve": book.compute_slippage_curve(quote_usd_rate=rate)
                            }
                        else:
                            sub_cache[(ex, sym)] = None

                    l2_data = sub_cache.get((ex, sym))
                    if l2_data:
                        try:
                            await ws.send_text(json.dumps(l2_data))
                        except Exception:
                            pass

            # Every 5th loop (~500ms), broadcast matrix and sample orderbook depth
            if loop_count % 5 == 0:
                matrix_data = math_engine.get_rate_matrix()
                await ws_manager.broadcast({
                    "type": "MATRIX",
                    "matrix": matrix_data
                })

            # 100ms micro-batch pause (10 cycles per second)
            await asyncio.sleep(0.10)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0.2)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial snapshot upon connection
        routes, telemetry = math_engine.scan_all()
        matrix_data = math_engine.get_rate_matrix()
        stats = state_store.get_aggregate_stats()
        history = state_store.get_recent_executions(limit=20)
        cfg = simulator.get_config()

        init_spreads = {}
        for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ETHBTC", "SOLBTC", "BNBUSDT"]:
            bk = feed_manager.get_order_book("Binance", s)
            if bk and bk.best_bid and bk.best_ask:
                init_spreads[s] = {
                    "spread_bps": round(bk.spread_bps, 2),
                    "mid_price": round(bk.mid_price, 6 if (bk.mid_price or 0) < 10 else 2),
                    "imbalance": round(bk.order_book_imbalance, 4),
                    "best_bid": bk.best_bid[0],
                    "best_ask": bk.best_ask[0]
                }

        await websocket.send_text(json.dumps({
            "type": "INITIAL_STATE",
            "telemetry": telemetry,
            "matrix": matrix_data,
            "stats": stats,
            "history": history,
            "config": cfg,
            "market_spreads": init_spreads
        }))


        while True:
            # Handle incoming commands from client
            msg = await websocket.recv_text()
            data = json.loads(msg)
            action = data.get("action")
            
            if action == "SIMULATE_TRADE":
                route_data = data.get("route")
                capital = float(data.get("capital_usd", 10000.0))
                # Reconstruct dummy route for execution
                matching_routes, _ = math_engine.scan_all(capital)
                target = None
                for r in matching_routes:
                    if r.route_id == route_data.get("route_id"):
                        target = r
                        break
                if not target and matching_routes:
                    target = matching_routes[0]

                if target:
                    try:
                        exec_result = simulator.execute_route(target, capital)
                        await ws_manager.broadcast({
                            "type": "EXECUTION",
                            "trade": exec_result,
                            "stats": state_store.get_aggregate_stats()
                        })
                    except ValueError as err:
                        await websocket.send_text(json.dumps({
                            "type": "ERROR",
                            "message": str(err)
                        }))

            elif action == "SUBSCRIBE_BOOK":
                ex = data.get("exchange", "Binance")
                sym = data.get("symbol", "BTCUSDT").upper()
                ws_manager.subscribe(websocket, ex, sym)
                book = feed_manager.get_order_book(ex, sym)
                if book:
                    quote_curr = "USDT"
                    for q in ["USDT", "BTC", "ETH"]:
                        if sym.endswith(q):
                            quote_curr = q
                            break
                    rate = math_engine.get_usd_value(quote_curr, 1.0)
                    await websocket.send_text(json.dumps({
                        "type": "L2_UPDATE",
                        "exchange": ex,
                        "symbol": sym,
                        "depth": book.get_depth(levels=20),
                        "slippage_curve": book.compute_slippage_curve(quote_usd_rate=rate)
                    }))

            elif action == "UPDATE_CONFIG":
                simulator.update_config(data.get("config", {}))
                await ws_manager.broadcast({
                    "type": "CONFIG_UPDATE",
                    "config": simulator.get_config()
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# REST API Endpoints
@app.get("/api/status")
def get_status():
    _, telemetry = math_engine.scan_all()
    feed_telemetry = feed_manager.get_telemetry()
    return {
        "status": "ONLINE",
        "telemetry": telemetry,
        "feed_telemetry": feed_telemetry,
        "config": simulator.get_config()
    }


@app.get("/api/matrix")
def get_matrix():
    return math_engine.get_rate_matrix()


@app.get("/api/orderbook/{exchange}/{symbol}")
def get_order_book(exchange: str, symbol: str):
    sym_upper = symbol.upper()
    book = feed_manager.get_order_book(exchange, sym_upper)
    if not book:
        raise HTTPException(status_code=404, detail="Symbol or exchange not found")
    depth = book.get_depth(levels=20)
    
    # Determine quote currency and USD conversion rate
    quote_curr = "USDT"
    for q in ["USDT", "BTC", "ETH"]:
        if sym_upper.endswith(q):
            quote_curr = q
            break
    quote_usd_rate = math_engine.get_usd_value(quote_curr, 1.0)
    slippage_curve = book.compute_slippage_curve(quote_usd_rate=quote_usd_rate)
    
    return {
        "depth": depth,
        "slippage_curve": slippage_curve
    }


@app.get("/api/opportunities")
def get_opportunities(capital: float = 10000.0):
    routes, telemetry = math_engine.scan_all(capital)
    return {
        "routes": routes,
        "telemetry": telemetry
    }


@app.get("/api/history")
def get_history(limit: int = 50):
    return {
        "history": state_store.get_recent_executions(limit=limit),
        "stats": state_store.get_aggregate_stats()
    }


from fastapi import Request


@app.post("/api/config")
async def update_config(request: Request):
    data = await request.json()
    simulator.update_config(data)
    cfg = simulator.get_config()
    await ws_manager.broadcast({
        "type": "CONFIG_UPDATE",
        "config": cfg
    })
    return cfg


@app.get("/api/risk")
def get_risk():
    stats = state_store.get_aggregate_stats()
    is_halted = simulator.is_kill_switch_engaged
    return {
        "kill_switch": is_halted,
        "max_capital_per_trade": 50000.0,
        "status": "HALTED" if is_halted else "ACTIVE_MONITORING",
        "total_simulations": stats.get("total_trades", 0),
        "net_pnl_usd": stats.get("total_net_pnl_usd", 0.0),
        "win_rate_pct": stats.get("win_rate_pct", 0.0)
    }


@app.post("/api/risk")
async def update_risk(request: Request):
    data = await request.json()
    if "kill_switch" in data:
        simulator.set_kill_switch(bool(data["kill_switch"]))
        await ws_manager.broadcast({
            "type": "CONFIG_UPDATE",
            "config": simulator.get_config()
        })
    return get_risk()


@app.post("/api/simulate")
async def simulate_trade(request: Request):
    if simulator.is_kill_switch_engaged:
        raise HTTPException(status_code=403, detail="EMERGENCY_KILL_SWITCH_ACTIVE: Execution halted by risk manager.")

    data = await request.json()
    route_id = data.get("route_id")
    capital_usd = float(data.get("capital_usd", 10000.0))


    routes, _ = math_engine.scan_all(capital_usd)
    target = None
    if route_id:
        for r in routes:
            if r.route_id == route_id:
                target = r
                break
    if not target and routes:
        target = routes[0]

    if not target:
        raise HTTPException(status_code=400, detail="No viable arbitrage route currently available for execution")

    try:
        exec_result = simulator.execute_route(target, capital_usd)
    except ValueError as err:
        raise HTTPException(status_code=403, detail=str(err))

    stats = state_store.get_aggregate_stats()
    await ws_manager.broadcast({
        "type": "EXECUTION",
        "trade": exec_result,
        "stats": stats
    })

    return {
        "trade": exec_result,
        "stats": stats
    }

