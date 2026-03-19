#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/stock-research-assistant}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Updating apt packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git

if [ ! -d "$APP_DIR" ]; then
  echo "App directory $APP_DIR does not exist yet."
  echo "Clone your repository first, then rerun this script."
  exit 1
fi

cd "$APP_DIR"

echo "Creating virtual environment..."
$PYTHON_BIN -m venv .venv

echo "Installing dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f ".env" ]; then
  echo "No .env found. Copying .env.example to .env"
  cp .env.example .env
  echo "Edit $APP_DIR/.env before enabling automation."
fi

echo "Setup complete."
echo "Next steps:"
echo "1. Edit $APP_DIR/.env with rotated OpenAI and Alpaca paper credentials."
echo "2. Copy deploy/systemd/*.service and *.timer into /etc/systemd/system/."
echo "3. Run: sudo systemctl daemon-reload"
echo "4. Run: sudo systemctl enable --now stock-research.timer"

