#!/usr/bin/env bash
set -euo pipefail

uv tool uninstall octave 2>/dev/null || true
desktop_file="${XDG_DATA_HOME:-$HOME/.local/share}/applications/octave.desktop"
icon_file="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps/octave.png"
if [ -f "$desktop_file" ]; then
  rm -f "$desktop_file"
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$(dirname "$desktop_file")" >/dev/null 2>&1 || true
  fi
fi
rm -f "$icon_file"
printf 'Octave program removed. Your music library and configuration were kept.\n'
printf 'To remove configuration too, delete: %s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/octave"
