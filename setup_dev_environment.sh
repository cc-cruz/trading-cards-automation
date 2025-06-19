#!/bin/bash

# 🚀 FlipHero Development Environment Setup Script
# Resolves Python path issues and port conflicts

echo "🃏 FlipHero Development Environment Setup"
echo "========================================"

# Check Python installation
echo "📋 Checking Python installation..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found: $(python3 --version)"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    echo "✅ Python found: $(python --version)"
    PYTHON_CMD="python"
else
    echo "❌ ERROR: Python not found. Please install Python 3.8+"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ ERROR: Please run this script from the trading-cards-automation directory"
    exit 1
fi

# Create backup of database
echo "💾 Creating database backup..."
if [ -f "carddealer.db" ]; then
    cp carddealer.db "carddealer.db.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Database backed up successfully"
else
    echo "⚠️  WARNING: No carddealer.db found - will be created on first run"
fi

# Check for port conflicts and find available ports
echo "🔍 Checking for available ports..."

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Find available backend port (starting from 8000)
BACKEND_PORT=8000
while ! check_port $BACKEND_PORT; do
    ((BACKEND_PORT++))
    if [ $BACKEND_PORT -gt 8010 ]; then
        echo "❌ ERROR: No available ports found in range 8000-8010"
        exit 1
    fi
done

# Find available frontend port (starting from 3000)
FRONTEND_PORT=3000
while ! check_port $FRONTEND_PORT; do
    ((FRONTEND_PORT++))
    if [ $FRONTEND_PORT -gt 3010 ]; then
        echo "❌ ERROR: No available ports found in range 3000-3010"
        exit 1
    fi
done

echo "✅ Available ports found:"
echo "   Backend:  $BACKEND_PORT"
echo "   Frontend: $FRONTEND_PORT"

# Create environment configuration file
echo "📝 Creating environment configuration..."
cat > .env.development << EOF
# FlipHero Development Environment Configuration
# Generated on $(date)

# Server Configuration
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
PYTHON_CMD=$PYTHON_CMD

# Database
DATABASE_URL=sqlite:///./carddealer.db

# Development Settings
DEBUG=true
RELOAD=true
HOST=0.0.0.0
EOF

# Create convenient startup scripts
echo "📝 Creating startup scripts..."

# Backend startup script
cat > start_backend.sh << EOF
#!/bin/bash
echo "🚀 Starting FlipHero Backend on port $BACKEND_PORT..."
source .env.development
$PYTHON_CMD -m uvicorn src.main:app --reload --host \$HOST --port $BACKEND_PORT
EOF
chmod +x start_backend.sh

# Frontend startup script
cat > start_frontend.sh << EOF
#!/bin/bash
echo "🚀 Starting FlipHero Frontend on port $FRONTEND_PORT..."
export PORT=$FRONTEND_PORT
npm run dev
EOF
chmod +x start_frontend.sh

# Combined startup script
cat > start_dev.sh << EOF
#!/bin/bash
echo "🚀 Starting FlipHero Development Environment..."
echo "Backend will be available at: http://localhost:$BACKEND_PORT"
echo "Frontend will be available at: http://localhost:$FRONTEND_PORT"
echo ""

# Start backend in background
echo "Starting backend..."
./start_backend.sh &
BACKEND_PID=\$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "Starting frontend..."
./start_frontend.sh &
FRONTEND_PID=\$!

echo ""
echo "✅ Development environment started!"
echo "📊 Backend API: http://localhost:$BACKEND_PORT"
echo "🎨 Frontend UI: http://localhost:$FRONTEND_PORT"
echo "📚 API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap 'echo ""; echo "🛑 Stopping services..."; kill \$BACKEND_PID \$FRONTEND_PID; exit 0' INT
wait
EOF
chmod +x start_dev.sh

# Check dependencies
echo "📦 Checking dependencies..."
if [ -f "requirements.txt" ]; then
    echo "✅ Python requirements.txt found"
    echo "💡 Run: pip install -r requirements.txt"
else
    echo "⚠️  WARNING: No requirements.txt found"
fi

if [ -f "package.json" ]; then
    echo "✅ package.json found"
    echo "💡 Run: npm install"
else
    echo "⚠️  WARNING: No package.json found"
fi

# Final instructions
echo ""
echo "🎉 Environment setup complete!"
echo "================================"
echo ""
echo "📋 Next Steps:"
echo "1. Install dependencies:"
echo "   pip install -r requirements.txt"
echo "   npm install"
echo ""
echo "2. Start development environment:"
echo "   ./start_dev.sh"
echo ""
echo "3. Or start services individually:"
echo "   Backend:  ./start_backend.sh"
echo "   Frontend: ./start_frontend.sh"
echo ""
echo "📁 Files created:"
echo "   - .env.development (environment configuration)"
echo "   - start_backend.sh (backend startup script)"
echo "   - start_frontend.sh (frontend startup script)"
echo "   - start_dev.sh (combined startup script)"
echo "   - carddealer.db.backup.* (database backup)"
echo ""
echo "🔗 Development URLs:"
echo "   Backend API: http://localhost:$BACKEND_PORT"
echo "   Frontend UI: http://localhost:$FRONTEND_PORT"
echo "   API Documentation: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "✅ Ready to begin Sprint 1 implementation!" 