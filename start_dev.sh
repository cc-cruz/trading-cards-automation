#!/bin/bash

# Activate virtualenv if present
if [ -d "$(dirname "$0")/.venv" ]; then
  source "$(dirname "$0")/.venv/bin/activate"
fi

echo "🚀 Starting FlipHero Development Environment"
echo "============================================"

# Start backend server in the background
echo "📡 Starting FastAPI backend (port 8000)..."
python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend server
echo "⚛️  Starting Next.js frontend (port 3000)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Servers started successfully!"
echo "📡 Backend API: http://localhost:8000"
echo "⚛️  Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT

# Wait for servers (keeps script running)
wait
