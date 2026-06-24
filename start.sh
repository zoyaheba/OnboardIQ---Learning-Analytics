#!/bin/bash
# OnboardIQ — Start all servers
# Usage: ./start.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOG_DIR="$ROOT/.logs"
PID_FILE="$ROOT/.onboardiq.pids"

mkdir -p "$LOG_DIR"

# ── Kill anything already on 8000/3000 ─────────────────────────────────────
echo "→ Clearing ports 8000 and 3000..."
lsof -ti:8000,3000 | xargs kill -9 2>/dev/null
sleep 1

# ── Backend ─────────────────────────────────────────────────────────────────
echo "→ Starting FastAPI backend on http://localhost:8000 ..."
cd "$BACKEND"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_FILE"

# Wait for backend to be ready (up to 10s)
for i in {1..10}; do
  sleep 1
  if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "   ✅ Backend ready (PID $BACKEND_PID)"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "   ⚠️  Backend slow to start — check $LOG_DIR/backend.log"
  fi
done

# ── Frontend ────────────────────────────────────────────────────────────────
echo "→ Starting Next.js frontend on http://localhost:3000 ..."
cd "$FRONTEND"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID >> "$PID_FILE"

# Wait for frontend to be ready (up to 20s)
for i in {1..20}; do
  sleep 1
  if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ Frontend ready (PID $FRONTEND_PID)"
    break
  fi
  if [ $i -eq 20 ]; then
    echo "   ⚠️  Frontend slow to start — check $LOG_DIR/frontend.log"
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OnboardIQ is running"
echo "  Frontend  →  http://localhost:3000"
echo "  Backend   →  http://localhost:8000/docs"
echo "  Logs      →  $LOG_DIR/"
echo ""
echo "  To stop:  ./stop.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
