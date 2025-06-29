#!/bin/bash

# Activate virtualenv if present
if [ -d "$(dirname "$0")/.venv" ]; then
  source "$(dirname "$0")/.venv/bin/activate"
fi

# Load environment variables from .env.development
if [ -f "$(dirname "$0")/.env.development" ]; then
  export $(grep -v '^#' "$(dirname "$0")/.env.development" | xargs)
fi

# Set default port if not specified in environment
BACKEND_PORT=${PORT:-8001}

echo "🚀 Starting FlipHero Development Environment"
echo "============================================"

# Start backend server in the background
echo "📡 Starting FastAPI backend (port $BACKEND_PORT)..."
python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend server
echo "⚛️  Starting Next.js frontend (port 3000)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Servers started successfully!"
echo "📡 Backend API: http://localhost:$BACKEND_PORT"
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