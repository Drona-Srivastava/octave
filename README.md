# Octave

A lightweight Linux music client that imports Apple Music playlists through
[gamdl](https://github.com/glomatico/gamdl), indexes local files, and plays them
with mpv. Apple Music is only needed during import/update.

## Arch Linux installation

Octave requires Python 3.11+, `uv`, `gamdl`, `mpv`, `ffmpeg`, and `chafa`.
Install the system dependencies with:

```bash
sudo pacman -Syu --needed git python uv mpv ffmpeg chafa curl
```

Clone and install Octave:

```bash
git clone https://github.com/Drona-Srivastava/octave.git
cd octave
./install.sh
```

The installer creates an `octave` command and adds Octave to the Linux
application menu. It also installs `gamdl` with `uv`.

## First-time setup

Export your Apple Music browser cookies in Netscape format, then run:

```bash
octave setup --cookies /path/to/cookies.txt \
  --playlist 'https://music.apple.com/.../playlist/...'
```

You can import more playlists by repeating `--playlist`, or add one later
from inside the TUI with `a`.

## Manual import and launch

```bash
octave import 'https://music.apple.com/.../playlist/...'
octave
```

To install directly from the hosted GitHub repository:

```bash
curl -fsSL https://github.com/Drona-Srivastava/octave/archive/refs/heads/main.tar.gz \
  | tar -xz && cd octave-main && ./install.sh
```

## TUI controls

Press `a` to add another playlist. Press Enter to play, `n`
for next, `b` for previous, `s` for shuffle, `t` for repeat, `l` to toggle
album names, `/` to search, `o` to sort, `u` to rescan, and `q` to quit.

The application creates `~/.config/octave/config.toml` on first run. Media and
the SQLite index live below the configured library path. Uninstalling Octave
does not remove your music library.

Commands: `octave import URL`, `octave playlists`, `octave songs`,
`octave update`, `octave status`, `octave config`, and `octave` to launch
the TUI. `amt` remains available as a compatibility alias.

Cookies are sensitive Netscape-format browser cookies. They are never logged,
stored in the library, or included in this repository.
