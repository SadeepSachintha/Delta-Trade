"""
Launcher for Delta Trade HFT Engine.
Runs FastAPI + WebSockets on port 8000.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import uvicorn
from engine.server import app

if __name__ == "__main__":
    print("=" * 65)
    print("  DELTA TRADE - HIGH-FREQUENCY CRYPTO ARBITRAGE ENGINE")
    print("  Microsecond L2 Depth Reconstructor & Bellman-Ford Negative Cycle Solver")
    print("  FastAPI & WebSocket Server running at http://127.0.0.1:8000")
    print("=" * 65)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
