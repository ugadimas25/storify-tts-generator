#!/bin/bash
# =============================================================================
# deploy.sh — Setup Storify AI Audiobook Agent on Ubuntu server (/var/www/)
# Run as root: bash deploy.sh
# =============================================================================
set -e

REPO_URL="https://github.com/ugadimas25/storify-tts-generator.git"
APP_DIR="/var/www/storify-tts-generator"
PYTHON="/usr/bin/python3"
VENV="$APP_DIR/venv"

echo "=== [1/6] Updating system packages ==="
apt-get update -qq
apt-get install -y ffmpeg python3-pip python3-venv git wget unzip

echo "=== [2/6] Installing Playwright system deps ==="
apt-get install -y libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2t64

echo "=== [3/6] Clone or pull repo ==="
if [ -d "$APP_DIR/.git" ]; then
    echo "Repo exists, pulling latest..."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "=== [4/6] Setup Python venv + install requirements ==="
cd "$APP_DIR"
$PYTHON -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip -q
"$VENV/bin/pip" install -r requirements.txt -q

echo "=== [5/6] Install Playwright browser ==="
"$VENV/bin/playwright" install chromium
"$VENV/bin/playwright" install-deps chromium

echo "=== [6/6] Create required directories ==="
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/src/content/audio"
mkdir -p "$APP_DIR/src/content/image"
mkdir -p "$APP_DIR/src/content/text"
mkdir -p "$APP_DIR/src/content/video"
mkdir -p "$APP_DIR/.ig_session"
mkdir -p "$APP_DIR/.tiktok_session"

# Create .env if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" << 'EOF'
OPENAI_API_KEY=
GOOGLE_APPLICATION_CREDENTIALS=src/json/storify-489603-112704b362c8.json
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_IDS=kSzQ9oZF2iytkgNNztpH,eESTQeTcGUli0jYysKtx
ELEVENLABS_VOICE_NAMES=Kanna,Senandika
ELEVENLABS_VOICE_ID=kSzQ9oZF2iytkgNNztpH
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
TTS_LANGUAGE_CODE=id-ID
TTS_VOICE_NAME=id-ID-Chirp3-HD-Kore
TTS_RANDOM_VOICE=true
COS_SECRET_ID=
COS_SECRET_KEY=
COS_REGION=ap-jakarta
COS_BUCKET=pewacaold-1379748683
IG_USERNAME=storifyasia
IG_PASSWORD=
TIKTOK_SESSION_ID=
EOF
    echo ""
    echo ">>> .env created — FILL IN the secret values before running!"
    echo "    nano $APP_DIR/.env"
fi

echo ""
echo "=== Setup cron jobs (WIB 07:00 = UTC 00:00, WIB 20:00 = UTC 13:00) ==="
CRON_CMD_MORNING="0 0 * * * cd $APP_DIR && $VENV/bin/python -m src.social.daily_poster >> $APP_DIR/logs/poster.log 2>&1"
CRON_CMD_EVENING="0 13 * * * cd $APP_DIR && $VENV/bin/python -m src.social.daily_poster >> $APP_DIR/logs/poster.log 2>&1"

# Add to crontab if not already present
(crontab -l 2>/dev/null | grep -v "daily_poster"; echo "$CRON_CMD_MORNING"; echo "$CRON_CMD_EVENING") | crontab -

echo ""
echo "=== DONE ==="
echo "Cron jobs registered:"
crontab -l | grep daily_poster
echo ""
echo "Next steps:"
echo "  1. Fill in .env secrets:  nano $APP_DIR/.env"
echo "  2. Copy content files to: $APP_DIR/src/content/{audio,image,text}/"
echo "  3. Test run:  cd $APP_DIR && $VENV/bin/python -m src.social.daily_poster --dry-run"
echo "  4. View logs: tail -f $APP_DIR/logs/poster.log"
