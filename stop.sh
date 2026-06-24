#!/bin/bash
# OnboardIQ — Stop all servers
# Usage: ./stop.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/.onboardiq.pids"

echo "→ Stopping OnboardIQ servers..."

# Kill by saved PIDs if file exists
if [ -f "$PID_FILE" ]; then
  while read -r pid; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      echo "   Stopped PID $pid"
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

# Also force-clear ports in case of orphaned processes
lsof -ti:8000,3000 | xargs kill -9 2>/dev/null

echo "   ✅ All servers stopped"
