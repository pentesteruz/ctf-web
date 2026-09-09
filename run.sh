#!/bin/bash
# Linux CTF Web Platform Startup Script

echo "=========================================================="
echo "🚀 Apex Linux CTF Web Platform Ishga Tushirilmoqda..."
echo "=========================================================="

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 topilmadi! Iltimos, Python3 o'rnating."
    exit 1
fi

if ! python3 -c "import flask" &> /dev/null; then
    echo "[+] Flask o'rnatilmoqda..."
    pip3 install flask
fi

echo "🌐 Server `http://localhost:5000` manzilida ishga tushirilmoqda..."
python3 app.py
