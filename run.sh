#!/bin/bash
echo "Starting IDStorm..."

# Start backend
echo "Starting backend (FastAPI)..."
cd backend
source venv/bin/activate 2>/dev/null || true
pip install -q -r requirements.txt 2>/dev/null
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend (Vite)..."
cd ../frontend
npm install --silent 2>/dev/null
npm run dev &
FRONTEND_PID=$!

echo ""
echo "IDStorm is running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
