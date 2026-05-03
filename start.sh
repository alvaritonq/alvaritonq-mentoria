#!/bin/bash
# MENTORIA — Arranca backend + tunnel
# Corre esto una vez antes de compartir la URL de la landing page

MENTORIA_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$MENTORIA_DIR/logs"
PID_DIR="/tmp"

mkdir -p "$LOG_DIR"

echo "🚀 MENTORIA — Arrancando sistema..."

# ── 1. Matar procesos anteriores ──────────────────────────────────────────────
if [ -f "$PID_DIR/mentoria_api.pid" ]; then
    kill $(cat "$PID_DIR/mentoria_api.pid") 2>/dev/null
fi
if [ -f "$PID_DIR/mentoria_tunnel.pid" ]; then
    kill $(cat "$PID_DIR/mentoria_tunnel.pid") 2>/dev/null
fi
sleep 1

# ── 2. Backend FastAPI ─────────────────────────────────────────────────────────
echo "⚙️  Arrancando backend (puerto 8000)..."
cd "$MENTORIA_DIR/api"
PYTHONPATH="$MENTORIA_DIR" /Library/Frameworks/Python.framework/Versions/3.14/bin/uvicorn \
    main:app --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/api-stdout.log" 2>&1 &
echo $! > "$PID_DIR/mentoria_api.pid"
sleep 3

# Verificar que levantó
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend OK"
else
    echo "❌ Backend no levantó — revisar $LOG_DIR/api-stderr.log"
    exit 1
fi

# ── 3. Tunnel serveo ──────────────────────────────────────────────────────────
echo "🌐 Abriendo tunnel público..."
ssh -i ~/.ssh/mentoria_serveo \
    -R alvaro-mentoria:80:localhost:8000 \
    serveo.net \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    > "$LOG_DIR/tunnel.log" 2>&1 &
echo $! > "$PID_DIR/mentoria_tunnel.pid"
sleep 6

# Extraer URL del tunnel
TUNNEL_URL=$(grep -o 'https://[^ ]*serveousercontent.com' "$LOG_DIR/tunnel.log" | head -1)

if [ -z "$TUNNEL_URL" ]; then
    # Si no hay URL con subdominio fijo, agarrar la URL random
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9._-]*.serveousercontent.com' "$LOG_DIR/tunnel.log" | head -1)
fi

# Guardar URL activa
echo "$TUNNEL_URL" > "$LOG_DIR/url-activa.txt"

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ MENTORIA ONLINE"
echo ""
echo "  🔗 URL pública: $TUNNEL_URL"
echo ""
echo "  Compartí ese link para que apliquen."
echo "  Las respuestas se guardan automáticamente."
echo "════════════════════════════════════════════"
echo ""
echo "Para parar todo: ./stop.sh"
echo "Ver aplicaciones: python3 mentor.py report"
