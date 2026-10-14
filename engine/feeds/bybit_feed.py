"""
Bybit v5 L2 Depth WebSocket Feed Handler.
Subscribes to orderbook.50.<symbol> for spot and linear pairs.
"""

import asyncio
import json
import time
import websockets
from typing import List
from .base_feed import BaseFeedHandler


class BybitFeedHandler(BaseFeedHandler):
    def __init__(self, symbols: List[str] = None):
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ETHBTC", "SOLBTC", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
        super().__init__("Bybit", symbols)
        self.ws_url = "wss://stream.bybit.com/v5/public/spot"

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
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10, open_timeout=5) as ws:
                    self.is_connected = True
                    self.reconnect_count += 1

                    # Subscribe to symbols
                    sub_args = [f"orderbook.50.{s}" for s in self.symbols]
                    sub_msg = {"op": "subscribe", "args": sub_args}
                    await ws.send(json.dumps(sub_msg))

                    while self.is_running:
                        msg = await ws.recv()
                        t_ingress = time.time()
                        self.total_messages_received += 1
                        self.last_message_time = t_ingress

                        try:
                            data = json.loads(msg)
                            topic = data.get("topic", "")
                            msg_type = data.get("type", "")
                            payload = data.get("data", {})

                            if not topic.startswith("orderbook."):
                                continue

                            symbol = payload.get("s", "")
                            bids = payload.get("b", [])
                            asks = payload.get("a", [])
                            update_id = payload.get("u", 0)

                            if msg_type == "snapshot" and self.on_snapshot_callback:
                                self.on_snapshot_callback(self.exchange_name, symbol, bids, asks, update_id)
                            elif msg_type == "delta" and self.on_delta_callback:
                                self.on_delta_callback(self.exchange_name, symbol, bids, asks, update_id)
                        except Exception:
                            pass

            except Exception:
                self.is_connected = False
                await asyncio.sleep(2.0)
