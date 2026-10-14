"""
Base Feed Handler Interface for Level-2 Crypto Exchange WebSockets.
Tracks connection state, heartbeat, packet ingress latency, and sequence gaps.
"""

import abc
import asyncio
import time
from typing import Callable, Optional, Dict, List


class BaseFeedHandler(abc.ABC):
    def __init__(self, exchange_name: str, symbols: List[str]):
        self.exchange_name: str = exchange_name
        self.symbols: List[str] = symbols
        self.is_connected: bool = False
        self.is_running: bool = False
        self.on_snapshot_callback: Optional[Callable] = None
        self.on_delta_callback: Optional[Callable] = None
        
        # Telemetry metrics
        self.total_messages_received: int = 0
        self.last_message_time: float = 0.0
        self.avg_latency_ms: float = 0.0
        self.reconnect_count: int = 0
        self._task: Optional[asyncio.Task] = None

    def set_callbacks(self, on_snapshot: Callable, on_delta: Callable):
        self.on_snapshot_callback = on_snapshot
        self.on_delta_callback = on_delta

    @abc.abstractmethod
    async def start(self):
        """Starts websocket connection loop."""
        pass

    @abc.abstractmethod
    async def stop(self):
        """Stops websocket connection gracefully."""
        pass

    def get_status(self) -> Dict:
        now = time.time()
        silence_sec = (now - self.last_message_time) if self.last_message_time > 0 else 999.0
        return {
            "exchange": self.exchange_name,
            "connected": self.is_connected and silence_sec < 5.0,
            "messages_received": self.total_messages_received,
            "reconnect_count": self.reconnect_count,
            "latency_ms": round(self.avg_latency_ms, 2),
            "last_seen_sec_ago": round(silence_sec, 2)
        }
