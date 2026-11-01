#!/usr/bin/env bash
# Rebuild the debug APK from the current mockup.
#   bash app/build.sh [belem|vigia]
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
CITY=${1:-belem}
[ -f "${CITY}_app.html" ] || { echo "missing ${CITY}_app.html — run mockups/build_muni.py first"; exit 1; }
cp "${CITY}_app.html" app/www/index.html
cd app/android
./gradlew assembleDebug --console=plain -q
APK=app/build/outputs/apk/debug/app-debug.apk
echo "built: $(du -h $APK | cut -f1)  ->  $(pwd)/$APK"
