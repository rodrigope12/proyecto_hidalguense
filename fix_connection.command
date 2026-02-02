#!/bin/bash
cd "$(dirname "$0")"

# 1. Kill old tunnels
echo "🔪 Killing old tunnels..."
pkill -9 cloudflared

# 2. Start new tunnel
echo "🚀 Starting new tunnel..."
LOG_FILE="tunnel_fix.log"
# Ensure we use the full path to avoid PATH issues if possible, or rely on PATH
# Assuming cloudflared is in PATH as verified before
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2 > "$LOG_FILE" 2>&1 &
PID=$!

echo "⏳ Waiting for URL..."
sleep 8

# 3. Extract URL
NEW_URL=$(grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare\.com' "$LOG_FILE" | grep -v "api.trycloudflare.com" | head -n 1)

if [ -z "$NEW_URL" ]; then
    echo "❌ Failed to get URL. Check $LOG_FILE"
    cat "$LOG_FILE"
    exit 1
fi

echo "✅ New URL: $NEW_URL"

# 4. Update Google Sheet (DNS)
echo "🌍 Updating Google Sheet..."
# Check for venv
if [ -d "venv" ]; then
    ./venv/bin/python3 update_url.py "$NEW_URL"
else
    python3 update_url.py "$NEW_URL"
fi

echo "🎉 DONE. The App should now auto-heal."
