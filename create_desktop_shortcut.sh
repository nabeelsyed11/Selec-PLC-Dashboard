#!/usr/bin/env bash
# Creates an executable desktop shortcut on Raspberry Pi OS
DESKTOP_DIR="$HOME/Desktop"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/start.sh"

if [ -d "$DESKTOP_DIR" ]; then
    cat <<EOF > "$DESKTOP_DIR/Selec-SCADA.desktop"
[Desktop Entry]
Type=Application
Name=Selec SCADA Dashboard
Comment=Launch Selec MiBRX-6M SCADA Edge Dashboard
Exec=lxterminal -e "bash -c '$SCRIPT_PATH; bash'"
Icon=utilities-system-monitor
Terminal=false
Categories=Utility;Application;
EOF
    chmod +x "$DESKTOP_DIR/Selec-SCADA.desktop"
    echo "✓ Desktop shortcut created at $DESKTOP_DIR/Selec-SCADA.desktop!"
    echo "You can now double-click 'Selec SCADA Dashboard' on your desktop!"
else
    echo "Desktop directory not found."
fi
