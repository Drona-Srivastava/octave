#!/usr/bin/env bash
set -euo pipefail

uv tool uninstall octave 2>/dev/null || true
desktop_file="${XDG_DATA_HOME:-$HOME/.local/share}/applications/octave.desktop"
if [ -f "$desktop_file" ]; then
  rm -f "$desktop_file"
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$(dirname "$desktop_file")" >/dev/null 2>&1 || true
  fi
fi
for size in 16 24 32 48 64 128 256 512; do
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/${size}x${size}/apps/octave.png"
done
icons_root="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
if command -v gtk-update-icon-cache >/dev/null 2>&1 && [ -d "$icons_root" ]; then
  gtk-update-icon-cache -f -t "$icons_root" >/dev/null 2>&1 || true
fi
printf 'Octave program removed. Your music library and configuration were kept.\n'
printf 'To remove configuration too, delete: %s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/octave"
