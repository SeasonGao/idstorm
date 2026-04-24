@echo off
echo Starting IDStorm...

echo Starting backend (FastAPI)...
start "IDStorm Backend" cmd /c "cd backend && pip install -q -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting frontend (Vite)...
start "IDStorm Frontend" cmd /c "cd frontend && npm install --silent && npm run dev"

echo.
echo IDStorm is running:
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo Close the terminal windows to stop.
