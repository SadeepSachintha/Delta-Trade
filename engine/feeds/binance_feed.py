"""
Binance L2 Depth WebSocket Feed Handler.
Subscribes to multi-stream <symbol>@depth20@100ms for ultra-low latency updates.
"""

import asyncio
import json
import time
import websockets
from typing import List
from .base_feed import BaseFeedHandler


class BinanceFeedHandler(BaseFeedHandler):
    def __init__(self, symbols: List[str] = None):
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ETHBTC", "SOLBTC", "BNBUSDT", "BNBBTC", "XRPUSDT", "DOGEUSDT"]
        super().__init__("Binance", symbols)
        # Format for Binance combined stream: e.g. btcusdt@depth20@100ms
        self.stream_names = [f"{s.lower()}@depth20@100ms" for s in self.symbols]
        self.ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(self.stream_names)}"

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self):
        while self.is_running:
            try:
                # Set reasonable connection timeout
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10, open_timeout=5) as ws:
                    self.is_connected = True
                    self.reconnect_count += 1
                    
                    while self.is_running:
                        msg = await ws.recv()
                        t_ingress = time.time()
                        self.total_messages_received += 1
                        self.last_message_time = t_ingress

                        try:
                            data = json.loads(msg)
                            stream = data.get("stream", "")
                            payload = data.get("data", {})
                            
                            # Stream name: e.g. btcusdt@depth20@100ms
                            raw_sym = stream.split("@")[0].upper()
                            
                            # Binance payload fields: "bids": [[price, qty], ...], "asks": [[price, qty], ...]
                            bids = payload.get("bids", [])
                            asks = payload.get("asks", [])
                            last_update_id = payload.get("lastUpdateId", 0)

                            if self.on_snapshot_callback and bids and asks:
                                self.on_snapshot_callback(self.exchange_name, raw_sym, bids, asks, last_update_id)

                        except Exception:
                            pass

            except Exception:
                self.is_connected = False
                await asyncio.sleep(2.0)
