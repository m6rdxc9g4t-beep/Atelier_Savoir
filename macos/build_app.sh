#!/bin/bash
# Construit « Atelier Savoir.app » et l'installe dans ~/Applications.
#
#   ./macos/build_app.sh               installe dans ~/Applications
#   ./macos/build_app.sh /Applications  installe ailleurs
#
# L'app pointe vers CE dossier de projet : si vous le déplacez, relancez ce script.
set -euo pipefail

APP_NAME="Atelier Savoir"
BUNDLE_ID="fr.ateliersavoir.app"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${1:-$HOME/Applications}"
APP_PATH="$DEST_DIR/$APP_NAME.app"
VENV="$PROJECT_DIR/.venv"

say() { printf '\n\033[1;33m▸ %s\033[0m\n' "$1"; }
fail() { printf '\n\033[1;31m✗ %s\033[0m\n' "$1"; exit 1; }

[[ "$(uname)" == "Darwin" ]] || fail "Ce script est destiné à macOS."
[[ -f "$PROJECT_DIR/desktop.py" ]] || fail "desktop.py introuvable dans $PROJECT_DIR."

# --------------------------------------------------------------- Python
PYTHON="${PYTHON:-$(command -v python3 || true)}"
[[ -n "$PYTHON" ]] || fail "python3 introuvable. Installez Python 3.10 ou plus récent."
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || fail "Python 3.10 ou plus récent est requis ($("$PYTHON" --version))."

if [[ ! -x "$VENV/bin/python" ]]; then
  say "Création de l'environnement Python (.venv)"
  "$PYTHON" -m venv "$VENV"
fi
say "Installation des dépendances"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r "$PROJECT_DIR/requirements.txt"
"$VENV/bin/python" -c "import flask, pypdf, webview" || fail "Les dépendances ne se sont pas installées correctement."

# ------------------------------------------------------------ bundle .app
say "Construction de « $APP_NAME.app »"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
BUNDLE="$WORK/$APP_NAME.app"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"

# Icône .icns à partir de macos/icon.png
ICONSET="$WORK/AppIcon.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$PROJECT_DIR/macos/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$PROJECT_DIR/macos/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$BUNDLE/Contents/Resources/AppIcon.icns"

VERSION="$(git -C "$PROJECT_DIR" describe --tags --always 2>/dev/null || echo 1.0)"
cat > "$BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleExecutable</key><string>AtelierSavoir</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundleDevelopmentRegion</key><string>fr</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.education</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSAppTransportSecurity</key>
  <dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict>
</plist>
PLIST

# Exécutable du bundle : lance desktop.py avec le Python du projet
{
  echo '#!/bin/bash'
  printf 'PROJECT_DIR=%q\n' "$PROJECT_DIR"
  cat <<'LAUNCHER'
PY="$PROJECT_DIR/.venv/bin/python"
LOG_DIR="$HOME/Library/Logs/AtelierSavoir"
mkdir -p "$LOG_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [[ ! -x "$PY" || ! -f "$PROJECT_DIR/desktop.py" ]]; then
  osascript -e 'display dialog "Le dossier du projet Atelier Savoir est introuvable ou incomplet :\n\n'"$PROJECT_DIR"'\n\nRelancez « Installer Atelier Savoir.command » depuis le dossier du projet." buttons {"OK"} default button 1 with icon stop with title "Atelier Savoir"'
  exit 1
fi

cd "$PROJECT_DIR"
exec "$PY" desktop.py >>"$LOG_DIR/atelier-savoir.log" 2>&1
LAUNCHER
} > "$BUNDLE/Contents/MacOS/AtelierSavoir"
chmod +x "$BUNDLE/Contents/MacOS/AtelierSavoir"

# ------------------------------------------------------------ installation
say "Installation dans $DEST_DIR"
mkdir -p "$DEST_DIR"
rm -rf "$APP_PATH"
mv "$BUNDLE" "$APP_PATH"
xattr -cr "$APP_PATH" 2>/dev/null || true
touch "$APP_PATH"
# Enregistre l'app auprès de Launchpad / Spotlight
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP_PATH" >/dev/null 2>&1 || true

if [[ ! -d /Applications/Ollama.app ]] && ! command -v ollama >/dev/null 2>&1; then
  printf '\n\033[1;33mOllama n'"'"'est pas installé : la génération de fiches sera indisponible.\033[0m\n'
  printf 'Téléchargez-le sur https://ollama.com puis : ollama pull llama3.1\n'
fi

printf '\n\033[1;32m✓ « %s » est installée : %s\033[0m\n' "$APP_NAME" "$APP_PATH"
printf 'Ouvrez-la depuis le Launchpad ou Spotlight, et glissez-la dans le Dock pour la garder sous la main.\n'
printf 'Journal : ~/Library/Logs/AtelierSavoir/atelier-savoir.log\n'
