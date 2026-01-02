# LLM Trading System - Startup Guide

**Last Updated:** 2025-12-31

This guide covers starting, stopping, and troubleshooting the LLM Trading System.

---

## Quick Start

```bash
# 1. Start Backend (Terminal 1)
cd /research/llm_trading
python -m backend.main

# 2. Start Frontend (Terminal 2)
cd /research/llm_trading/frontend
npm run dev

# 3. Open Dashboard
# Navigate to: http://100.100.238.72:4173/
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER ACCESS                                      │
│                    http://100.100.238.72:4173/                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite + Tailwind)                                        │
│  Port: 4173  |  Host: 0.0.0.0  |  File: frontend/vite.config.js            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ API Calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKEND API (FastAPI)                                                     │
│  Port: 8200  |  Host: 0.0.0.0  |  File: backend/main.py                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │  Requesty API         │       │  Alpaca Paper Trading │
        │  (LLM Models)         │       │  (6 Accounts)          │
        └───────────────────────┘       └───────────────────────┘
```

---

## Port Configuration

| Service | Port | Config File | Host Binding | Configurable Via |
|---------|------|-------------|--------------|------------------|
| Frontend | 4173 | `frontend/vite.config.js` | 0.0.0.0 (all interfaces) | `PORT_FRONTEND` in .env |
| Backend | 8200 | `backend/config/ports.py` | 0.0.0.0 (all interfaces) | `PORT_BACKEND` in .env |
| Test Utils | 8201 | `backend/config/ports.py` | 127.0.0.1 (localhost) | `PORT_TEST` in .env |

**Port Configuration System:**
- All ports are now configurable via environment variables in `.env`
- Default ports: Backend=8200, Frontend=4173, Test=8201
- Port 8200 chosen to avoid conflict with other services often running on 8000
- To change ports: Update `.env` file and restart services

**Why 0.0.0.0?**
- Binds to all network interfaces
- Required for Tailscale VPN access
- Allows access via `localhost`, `127.0.0.1`, AND `100.100.238.72`

**Troubleshooting Port Conflicts:**
```bash
# Check what's using a port
lsof -i :8200
lsof -i :4173

# Change port if needed
# Edit .env file:
PORT_BACKEND=8300  # Use different port
PORT_FRONTEND=4174 # Use different port
```

---

## Startup Procedures

### Option 1: Manual Start (Recommended for Development)

**Terminal 1 - Backend:**
```bash
cd /research/llm_trading
python -m backend.main
```

Expected output:
```
Startup: Listing all registered routes:
 - / [GET]
 - /api/research/current [GET]
 - /api/research/generate [POST]
 ...
🚀 Starting LLM Trading backend on http://0.0.0.0:8200
INFO:     Uvicorn running on http://0.0.0.0:8200
```

**Terminal 2 - Frontend:**
```bash
cd /research/llm_trading/frontend
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:4173/
  ➜  Network: http://100.100.238.72:4173/
```

### Option 2: Background Start (For Production)

```bash
# Start backend in background
cd /research/llm_trading
nohup python -m backend.main > /tmp/backend.log 2>&1 &
echo $! > /tmp/backend.pid

# Start frontend in background
cd /research/llm_trading/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
echo $! > /tmp/frontend.pid
```

### Option 3: Using start.sh Script

Create `start.sh` in project root:

```bash
#!/bin/bash
# start.sh - Start both frontend and backend

# Kill existing processes
echo "Stopping existing servers..."
killall node python 2>/dev/null

# Start backend
echo "Starting backend on port 8000..."
cd /research/llm_trading
python -m backend.main &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/backend.pid

# Start frontend
echo "Starting frontend on port 4173..."
cd /research/llm_trading/frontend
npm run dev &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/frontend.pid

echo ""
echo "✅ Servers started!"
echo "   Backend:  PID $BACKEND_PID  (port 8000)"
echo "   Frontend: PID $FRONTEND_PID (port 4173)"
echo ""
echo "   Dashboard: http://100.100.238.72:4173/"
echo ""

# Wait for user input
read -p "Press Ctrl+C to stop..."
```

Make executable and run:
```bash
chmod +x start.sh
./start.sh
```

---

## Stopping the Servers

### Stop All (Quick)
```bash
killall node python
```

### Stop Individual Servers
```bash
# Stop frontend
kill $(cat /tmp/frontend.pid) 2>/dev/null
# OR
pkill -f "vite"

# Stop backend
kill $(cat /tmp/backend.pid) 2>/dev/null
# OR
pkill -f "backend.main"
```

### Clean Stop (Kill by port)
```bash
# Stop what's on port 4173
lsof -ti :4173 | xargs kill -9

# Stop what's on port 8000
lsof -ti :8000 | xargs kill -9
```

---

## Troubleshooting

### Problem: "This site can't be reached" / "ERR_CONNECTION_REFUSED"

**Diagnosis:**
```bash
# Check if servers are running
lsof -i :8000 -i :4173
```

**Solution 1: Servers not running**
```bash
# Restart servers (see Startup Procedures above)
```

**Solution 2: Servers bound to localhost only**
```bash
# Check vite.config.js has:
server: {
  host: '0.0.0.0',  # NOT 'localhost'
  port: 4173,
}

# Check backend/main.py has:
uvicorn.run(app, host="0.0.0.0", port=8000)  # NOT '127.0.0.1'
```

**Solution 3: Firewall blocking**
```bash
# Check firewall status
sudo ufw status

# Allow ports if needed
sudo ufw allow 8000/tcp
sudo ufw allow 4173/tcp
```

**Solution 4: Wrong URL**
- Use `http://100.100.238.72:4173/` (NOT :5173, NOT :3000)
- The port MUST be 4173 (configured in vite.config.js)

---

### Problem: Port Already in Use

**Error:**
```
Error: listen EADDRINUSE: address already in use :::4173
```

**Diagnosis:**
```bash
# Find what's using the port
lsof -i :4173
```

**Solution:**
```bash
# Kill the process using the port
lsof -ti :4173 | xargs kill -9

# Then restart your server
```

---

### Problem: Frontend Can't Connect to Backend

**Error (browser console):**
```
ERR_CONNECTION_REFUSED
CORS policy error
```

**Check 1: Backend is running**
```bash
curl http://localhost:8000/
# Should return: {"status":"ok","service":"LLM Council API"...}
```

**Check 2: CORS configuration**
```bash
# In backend/main.py, verify CORS includes:
allow_origins=[
    "http://localhost:4173",
    "http://100.100.238.72:4173",
    ...
]
```

**Check 3: Frontend API URL**
```bash
# In frontend/src/api/trading.js:
const BASE_URL = 'http://100.100.238.72:8000/api';  # NOT localhost
```

---

### Problem: API Returns Mock Data Instead of Real Data

**Check frontend configuration:**
```bash
# In frontend/src/api/trading.js:
const USE_MOCK = false;  # Should be FALSE for real data
```

---

### Problem: ImportError or Module Not Found

**Backend:**
```bash
# Check Python path
cd /research/llm_trading
pwd  # Should be /research/llm_trading

# Try running with Python module syntax
python -m backend.main  # NOT python backend/main.py
```

**Frontend:**
```bash
# Reinstall dependencies
cd /research/llm_trading/frontend
rm -rf node_modules package-lock.json
npm install
```

---

### Problem: Changes Not Reflecting

**Frontend:**
- Hard refresh: `Ctrl+Shift+R` (browser)
- Clear cache: DevTools → Application → Storage → Clear site data
- Restart dev server: Stop and `npm run dev` again

**Backend:**
- Restart server (FastAPI doesn't auto-reload by default)
- Check if running in production mode (no auto-reload)

---

## Status Check Commands

```bash
# Quick status check
echo "=== SERVER STATUS ==="
lsof -i :8000 -i :4173 | grep LISTEN

# Test backend health
curl -s http://localhost:8000/ | jq .

# Test frontend
curl -s http://localhost:4173/ | head -5

# View logs
tail -f /tmp/backend.log
tail -f /tmp/frontend.log

# Check for errors
grep -i error /tmp/backend.log | tail -20
grep -i error /tmp/frontend.log | tail -20
```

---

## Environment Variables

Create a `.env` file in the project root:

```bash
# /research/llm_trading/.env

# Requesty API (for LLM models)
REQUESTY_API_KEY=sk-or-v1-xxxxx

# Alpaca Paper Trading (6 accounts)
ALPACA_PAPER_KEY_CHATGPT=xxxxx
ALPACA_PAPER_SECRET_CHATGPT=xxxxx
ALPACA_PAPER_KEY_GEMINI=xxxxx
ALPACA_PAPER_SECRET_GEMINI=xxxxx
ALPACA_PAPER_KEY_CLAUDE=xxxxx
ALPACA_PAPER_SECRET_CLAUDE=xxxxx
ALPACA_PAPER_KEY_GROQ=xxxxx
ALPACA_PAPER_SECRET_GROQ=xxxxx
ALPACA_PAPER_KEY_DEEPSEEK=xxxxx
ALPACA_PAPER_SECRET_DEEPSEEK=xxxxx
ALPACA_PAPER_KEY_COUNCIL=xxxxx
ALPACA_PAPER_SECRET_COUNCIL=xxxxx

# Database (optional, defaults to SQLite)
DATABASE_URL=postgresql://localhost:5432/llm_trading

# Log level
LOG_LEVEL=INFO
```

Load environment before starting:
```bash
cd /research/llm_trading
source .env  # OR
export $(cat .env | xargs)
```

---

## Pipeline Flow

Once servers are running:

1. **Research Tab** (Perplexity + Gemini)
   - Click "Generate Research"
   - Wait for completion
   - Review and verify

2. **PMs Tab** (5 Portfolio Manager Models)
   - Click "Generate Pitches"
   - Wait for all 5 models to respond
   - Review convictions

3. **Council Tab** (Chairman Synthesis)
   - Click "Synthesize Council"
   - Chairman reviews all pitches + peer reviews
   - Final decision displayed

4. **Trades Tab** (Execution)
   - Review pending trades
   - Click "Approve All" or approve individually
   - Click "Execute Approved"

5. **Monitor Tab** (Live Positions)
   - View current positions across 6 accounts
   - Check P/L
   - Run checkpoints (daily conviction updates)

---

## File Locations

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI server (port from config) |
| `backend/config/ports.py` | Port configuration (defaults: 8200, 4173, 8201) |
| `frontend/vite.config.js` | Vite dev server config (port 4173) |
| `frontend/src/api/trading.js` | API client (toggle USE_MOCK) |
| `cli.py` | Command-line interface |
| `.env` | Environment variables (PORT_BACKEND, PORT_FRONTEND, etc.) |
| `start.sh` | Startup script with port checking |

---

## Network Access

### Local Access
- Frontend: `http://localhost:4173/`
- Backend: `http://localhost:8000/`

### Tailscale VPN Access
- Frontend: `http://100.100.238.72:4173/`
- Backend: `http://100.100.238.72:8000/`

### From Other Devices on Same Network
- Frontend: `http://<your-ip>:4173/`
- Backend: `http://<your-ip>:8000/`

Find your IP:
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

---

## Common Commands Reference

```bash
# === START/STOP ===
# Start both servers
cd /research/llm_trading && python -m backend.main &
cd /research/llm_trading/frontend && npm run dev &

# Stop both
killall node python

# === STATUS ===
# Check ports
lsof -i :8000 -i :4173

# Test backend
curl http://localhost:8000/

# === LOGS ===
# View logs
tail -f /tmp/backend.log
tail -f /tmp/frontend.log

# === RESET ===
# Clear node modules and reinstall
cd frontend && rm -rf node_modules package-lock.json && npm install

# Kill everything and restart
killall node python; sleep 2; cd /research/llm_trading && python -m backend.main &
cd /research/llm_trading/frontend && npm run dev &
```

---

## Getting Help

If issues persist:

1. **Check logs:** `tail -f /tmp/backend.log` and `tail -f /tmp/frontend.log`
2. **Verify ports:** `lsof -i :8000 -i :4173`
3. **Test API:** `curl http://localhost:8000/`
4. **Check browser console:** F12 → Console for errors
5. **Check network tab:** F12 → Network for failed requests

---

## Summary

| What | Port | URL | Command |
|------|------|-----|---------|
| Backend | 8200 | http://100.100.238.72:8200/ | `python -m backend.main` |
| Frontend | 4173 | http://100.100.238.72:4173/ | `npm run dev` |
| Stop All | - | - | `killall node python` |
| Status | - | - | `lsof -i :8200 -i :4173` |
| Quick Start | - | - | `./start.sh` (port checking included) |

**Remember:**
- Frontend defaults to port 4173 (configurable via `PORT_FRONTEND` in .env)
- Backend defaults to port 8200 (configurable via `PORT_BACKEND` in .env)
- Both bind to 0.0.0.0 (all interfaces, not localhost)
- start.sh checks port availability before starting
- USE_MOCK must be false in trading.js for real data
