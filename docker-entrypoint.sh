#!/bin/bash
set -e

echo "=== Starting AI B-Roll Autopilot Cloud Container ==="

# Start FastAPI backend in background on port 8000
echo "Starting FastAPI Backend API on port 8000..."
python -m ai_broll_autopilot.cli serve --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for Backend API to become ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null; then
        echo "Backend API is online and healthy!"
        break
    fi
    sleep 1
done

# Start Next.js standalone server on port 3000
echo "Starting Next.js Web Frontend on port 3000..."
if [ -d "/app/web-standalone" ]; then
    PORT=3000 HOSTNAME=0.0.0.0 node /app/web-standalone/server.js &
    FRONTEND_PID=$!
else
    echo "Warning: Standalone Next.js directory not found, running backend only."
fi

# Graceful termination handler
trap "echo 'Stopping services...'; kill -TERM $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# Wait for any process to exit
wait -n $BACKEND_PID $FRONTEND_PID
