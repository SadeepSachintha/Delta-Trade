"""
OKX v5 L2 Depth WebSocket Feed Handler.
Subscribes to books5 / books channel for sub-100ms updates.
"""

import asyncio
import json
import time
import websockets
from typing import List
from .base_feed import BaseFeedHandler


class OKXFeedHandler(BaseFeedHandler):
    def __init__(self, symbols: List[str] = None):
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ETHBTC", "SOLBTC", "XRPUSDT", "DOGEUSDT"]
        super().__init__("OKX", symbols)
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"

    def _to_okx_inst(self, sym: str) -> str:
        # Convert BTCUSDT -> BTC-USDT
        for quote in ["USDT", "BTC", "ETH"]:
            if sym.endswith(quote):
                base = sym[:-len(quote)]
                return f"{base}-{quote}"
        return sym

    def _from_okx_inst(self, inst_id: str) -> str:
        return inst_id.replace("-", "")

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

                    # OKX subscription
                    args = [{"channel": "books5", "instId": self._to_okx_inst(s)} for s in self.symbols]
                    sub_msg = {"op": "subscribe", "args": args}
                    await ws.send(json.dumps(sub_msg))

                    while self.is_running:
                        msg = await ws.recv()
                        t_ingress = time.time()
                        self.total_messages_received += 1
                        self.last_message_time = t_ingress

                        try:
                            data = json.loads(msg)
                            arg = data.get("arg", {})
                            channel = arg.get("channel", "")
                            inst_id = arg.get("instId", "")
                            symbol = self._from_okx_inst(inst_id)
                            books = data.get("data", [])

                            if channel == "books5" and books:
                                book = books[0]
                                bids = [[item[0], item[1]] for item in book.get("bids", [])]
                                asks = [[item[0], item[1]] for item in book.get("asks", [])]
                                seq_id = int(book.get("seqId", 0))

                                if self.on_snapshot_callback:
                                    self.on_snapshot_callback(self.exchange_name, symbol, bids, asks, seq_id)
                        except Exception:
                            pass

            except Exception:
                self.is_connected = False
                await asyncio.sleep(2.0)
