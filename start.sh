#!/bin/bash
# ==============================================================================
# DELTA TRADE - High-Frequency Crypto Arbitrage Engine & Terminal Orchestrator
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================================="
echo "  🚀 DELTA TRADE | HFT ARBITRAGE ENGINE & TERMINAL LAUNCHER"
echo "=================================================================="

# 1. Python Environment Check
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment in .venv..."
    python3 -m venv .venv
    echo "📦 Installing Python dependencies from requirements.txt..."
    .venv/bin/pip install -r requirements.txt
else
    echo "✓ Python virtual environment (.venv) detected."
fi

# 2. Frontend Node Dependencies Check
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing Frontend npm dependencies..."
    cd frontend && npm install && cd ..
else
    echo "✓ Frontend node_modules detected."
fi

# Process cleanup handler on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down Delta Trade services..."
    if [ -n "$ENGINE_PID" ] && kill -0 "$ENGINE_PID" 2>/dev/null; then
        kill "$ENGINE_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ -n "$PHP_PID" ] && kill -0 "$PHP_PID" 2>/dev/null; then
        kill "$PHP_PID" 2>/dev/null || true
    fi
    echo "✓ All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 3. Start Python HFT Engine (Port 8000)
echo "⚡ Starting Python HFT Arbitrage Engine (FastAPI + WebSockets on :8000)..."
.venv/bin/python engine/run_engine.py &
ENGINE_PID=$!

# Wait briefly for FastAPI to bind
sleep 1.5

# 4. Start PHP Risk Console (Optional if PHP installed, Port 8080)
if command -v php >/dev/null 2>&1; then
    echo "🛡️  Starting PHP Risk Management Console on http://127.0.0.1:8080..."
    php -S 127.0.0.1:8080 -t management >/dev/null 2>&1 &
    PHP_PID=$!
else
    echo "ℹ️  PHP CLI not installed on host. Native FastAPI Risk Manager active at /api/risk."
fi

# 5. Start Frontend Terminal (Port 5173)
echo "🖥️  Starting Trader Terminal Frontend (Vite on http://127.0.0.1:5173)..."
cd frontend
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!
cd ..

echo "=================================================================="
echo "  ✓ PLATFORM ONLINE:"
echo "    - Terminal UI:        http://127.0.0.1:5173"
echo "    - Engine API & Docs:  http://127.0.0.1:8000/docs"
echo "    - Engine WebSocket:   ws://127.0.0.1:8000/ws"
echo "    - Risk API:           http://127.0.0.1:8000/api/risk"
if [ -n "$PHP_PID" ]; then
    echo "    - PHP Risk Dashboard: http://127.0.0.1:8080"
fi
echo "=================================================================="
echo "Press Ctrl+C to halt all services."

# Wait indefinitely until interrupted
wait
