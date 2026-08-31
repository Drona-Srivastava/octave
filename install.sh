#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

install_system_packages() {
  if command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed python uv mpv ffmpeg chafa
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv ffmpeg mpv chafa curl
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 ffmpeg mpv chafa curl
  else
    printf '%s\n' 'Unsupported package manager. Install Python 3.11+, uv, mpv, ffmpeg, and chafa manually.' >&2
  fi
}

install_system_packages

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# uv may already be installed while its tool bin directory is not in PATH.
uv_tool_bin="$(uv tool dir --bin 2>/dev/null || true)"
if [ -n "$uv_tool_bin" ]; then
  export PATH="$uv_tool_bin:$PATH"
fi

system_python="$(command -v python3 || command -v python || true)"
if [ -z "$system_python" ]; then
  printf '%s\n' 'Python 3.11+ is required but was not found.' >&2
  exit 1
fi
if ! "$system_python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  printf '%s\n' "Python 3.11+ is required. Found: $($system_python --version 2>&1)" >&2
  exit 1
fi

uv tool install --force --python "$system_python" "$repo_dir"
uv tool install --force --python "$system_python" gamdl

config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/octave"
mkdir -p "$config_dir"

# Register Octave in graphical Linux application menus. The TUI needs a
# terminal, so desktop environments should launch it in one.
applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
desktop_file="$applications_dir/octave.desktop"
mkdir -p "$applications_dir"
octave_bin="$(command -v octave)"
icon_name="multimedia-player"
icon_path=""
logo_source="$repo_dir/logos/octave.png"
if [ ! -f "$logo_source" ]; then
  logo_source="$repo_dir/logos/octave-512.png"
fi
if [ -f "$logo_source" ]; then
  for size in 16 24 32 48 64 128 256 512; do
    icon_source="$repo_dir/logos/octave-${size}.png"
    icons_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/${size}x${size}/apps"
    if [ "$size" = 512 ] && [ ! -f "$icon_source" ]; then
      icon_source="$logo_source"
    fi
    if [ -f "$icon_source" ]; then
      mkdir -p "$icons_dir"
      install -m 644 "$icon_source" "$icons_dir/octave.png"
      if [ "$size" = 512 ]; then
        icon_path="$icons_dir/octave.png"
      fi
    fi
  done
  icon_name="octave"
fi
cat > "$desktop_file" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Octave
Comment=Local Apple Music library and TUI player
Exec=$octave_bin
TryExec=$octave_bin
Icon=${icon_path:-$icon_name}
Terminal=true
Categories=AudioVideo;Audio;Player;
StartupNotify=true
EOF
chmod 644 "$desktop_file"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$applications_dir" >/dev/null 2>&1 || true
fi
icons_root="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
if command -v gtk-update-icon-cache >/dev/null 2>&1 && [ -d "$icons_root" ]; then
  gtk-update-icon-cache -f -t "$icons_root" >/dev/null 2>&1 || true
fi

printf 'Octave installed. Run: octave\n'
printf 'Application menu entry: %s\n' "$desktop_file"
