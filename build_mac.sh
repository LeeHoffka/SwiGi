#!/bin/bash
# Build SwiGi portable na macOS.
set -e

echo "=== SwiGi — macOS portable build ==="

python3 --version || { echo "Python3 nenalezen!"; exit 1; }

pip3 install pyinstaller --break-system-packages 2>/dev/null || pip3 install pyinstaller

mkdir -p lib
if [ ! -f lib/libhidapi.dylib ]; then
    if [ -f /opt/homebrew/lib/libhidapi.dylib ]; then
        cp /opt/homebrew/lib/libhidapi.dylib lib/
    elif [ -f /usr/local/lib/libhidapi.dylib ]; then
        cp /usr/local/lib/libhidapi.dylib lib/
    else
        echo "libhidapi.dylib nenalezen! Spusť: brew install hidapi"
        exit 1
    fi
fi

echo "Building..."
pyinstaller \
  --name SwiGi \
  --onedir \
  --console \
  --clean \
  --noconfirm \
  --add-binary "lib/libhidapi.dylib:." \
  --exclude-module tkinter \
  --exclude-module unittest \
  swigi.py

if [ -f dist/SwiGi/SwiGi ]; then
    echo ""
    echo "=== Build hotový! ==="
    echo "Složka: dist/SwiGi/"
    echo "Spuštění: ./dist/SwiGi/SwiGi"
else
    echo "Build selhal!"
    exit 1
fi
