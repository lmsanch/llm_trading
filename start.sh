#!/bin/bash

# LLM Trading - Start script

set -e  # Exit on error

echo "Starting LLM Trading..."
echo ""

# Source environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Loaded environment variables from .env"
fi

# Set default ports if not in environment
PORT_BACKEND=${PORT_BACKEND:-8200}
PORT_FRONTEND=${PORT_FRONTEND:-4173}

# Check and clean up ports if in use
echo "Checking port availability..."

# Function to check and kill process on port
cleanup_port() {
    local port=$1
    local name=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port $port is in use by an existing process"
        local pid=$(lsof -ti :$port)
        echo "   Stopping old $name process (PID: $pid)..."

        # Try graceful kill first
        kill $pid 2>/dev/null
        sleep 1

        # Check if still running, force kill if needed
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo "   Process still running, force killing..."
            kill -9 $pid 2>/dev/null
            sleep 2
        fi

        # Final verification
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo "❌ Error: Failed to stop process on port $port"
            echo "   Run: sudo lsof -i :$port to see what's using it"
            echo "   Or: sudo kill -9 $pid"
            exit 1
        fi
        echo "   ✓ Port $port freed"
    fi
}

# Clean up both ports
cleanup_port $PORT_BACKEND "backend"
cleanup_port $PORT_FRONTEND "frontend"

echo "✓ Ports $PORT_BACKEND and $PORT_FRONTEND are available"
echo ""

# Start backend
echo "Starting backend on http://localhost:$PORT_BACKEND..."
uv run python -m backend.main &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start frontend
echo "Starting frontend on http://localhost:$PORT_FRONTEND..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ LLM Trading is running!"
echo "  Backend:  http://localhost:$PORT_BACKEND"
echo "  Frontend: http://localhost:$PORT_FRONTEND"
echo "  Tailscale: http://100.100.238.72:$PORT_FRONTEND"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
