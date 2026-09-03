#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🎵 Installing OmaAmp (Winamp 2.91 Classic for Linux)..."

# Ensure target directories exist
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/128x128/apps"
mkdir -p "$HOME/.config/omaamp/themes"

# Copy Icon
cp "$REPO_DIR/icon.png" "$HOME/.local/share/icons/hicolor/128x128/apps/omaamp.png"

# Create/Update launcher in ~/.local/bin/omaamp
cat << 'EOF' > "$HOME/.local/bin/omaamp"
#!/usr/bin/env bash
INSTALL_DIR="REPLACE_ME_REPO_DIR"

if command -v uv >/dev/null 2>&1; then
    exec uv run --directory "$INSTALL_DIR" python "$INSTALL_DIR/main.py" "$@"
else
    exec python3 "$INSTALL_DIR/main.py" "$@"
fi
EOF

sed -i "s|REPLACE_ME_REPO_DIR|$REPO_DIR|g" "$HOME/.local/bin/omaamp"
chmod +x "$HOME/.local/bin/omaamp"

# Create Desktop Entry
cat << EOF > "$HOME/.local/share/applications/omaamp.desktop"
[Desktop Entry]
Name=OmaAmp (Winamp)
GenericName=Audio Player
Comment=Classic Winamp 2.91 audio player with themes, real-time FFT visualizer, 10-band DSP EQ, and playlist
Exec=$HOME/.local/bin/omaamp %F
Icon=omaamp
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;Qt;
MimeType=audio/mpeg;audio/x-mpegurl;audio/ogg;audio/x-wav;audio/flac;audio/mp4;audio/aac;
StartupNotify=true
EOF

# Update desktop database
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "✅ Installation complete!"
echo "🚀 You can now start OmaAmp by typing 'omaamp' or finding it in your application launcher (Super + Space)."
