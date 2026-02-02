#!/bin/bash
cd "$(dirname "$0")"

# === CONFIGURATION ===
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "=========================================================="
echo "   SISTEMA DE LOGÍSTICA - ARRANCADOR UNIVERSAL"
echo "=========================================================="
echo "1. Backend API (Python/FastAPI)"
echo "2. Frontend Web (Servido por Backend)"
echo "3. Túnel Remoto (Cloudflare)"
echo "4. App Móvil (Expo Tunnel)"
echo "=========================================================="

# 1. CHECK AND START BACKEND
echo "🚀 Iniciando Backend (Puerto 8000)..."
# Check if running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  El puerto 8000 ya está en uso. Reiniciando servicio..."
    kill -9 $(lsof -t -i:8000)
fi

# Start Backend in background
# We assume virtualenv is in 'venv'
if [ -d "venv" ]; then
    # Use executables directly from venv to avoid PATH issues
    echo "Using venv Python..."
    
    # Launch Uvicorn in a NEW Terminal window so logs are visible
    # We use osascript (AppleScript) for this.
    echo "🖥️  Abriendo nueva terminal para logs del Backend..."
    
    # Construct command securely
    DIR="$(pwd)"
    # Use single quotes for the directory to avoid nested double-quote issues in AppleScript
    CMD="cd '$DIR' && echo '=== BACKEND LOGS ===' && ./venv/bin/python3 -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    
    osascript -e "tell application \"Terminal\" to do script \"$CMD\""
    
    # We don't have the PID easily here, but lsof can find it.
    echo "✅ Backend iniciado en ventana separada."
else
    echo "❌ Error: No se encontró el entorno virtual 'venv'."
    exit 1
fi

# 2. START TUNNELS & MOBILE
# We reuse the existing logic but improved
# Instead of calling the other script, we include the logic here for unity OR call it.
# Calling it is cleaner if I trust it.
# But I need to make sure it doesn't block immediately or we handle it right.
# The `start_mobile_remote.command` I edited ends with `npx expo start ...` which is blocking.
# So we should run the backend FIRST (done above), then run the mobile script which handles tunnels and Expo.

echo "⏳ Esperando a que el backend arranque..."

MAX_RETRIES=30
COUNT=0

while true; do
    # Try to fetch health endpoint
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health)
    
    if [ "$HTTP_STATUS" == "200" ]; then
        echo ""
        echo "✅ Backend respondiendo correctamente (HTTP 200)."
        break
    fi
    
    sleep 2
    echo -n "."
    COUNT=$((COUNT+1))
    
    if [ $COUNT -ge $MAX_RETRIES ]; then
      echo ""
      echo "⚠️  El backend tardó demasiado en responder (Timeout 60s)."
      echo "    continuando de todos modos..."
      break 
    fi
done

echo "🚀 Iniciando Túneles y App Móvil..."
# Execute the mobile remote script
./mobile/start_mobile_remote.command

# Cleanup on exit (if mobile script finishes)
# Remove kill $PID_BACKEND since it is in another window
echo "👋 Cerrando lanzador maestro."
