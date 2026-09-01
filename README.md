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

Octave configures Gamdl for the reliable `aac-web` codec, FFmpeg-backed
downloads, saved playlist manifests, and a private temporary directory under
`~/.config/octave/.gamdl-temp`. Synced lyrics are optional and disabled during
downloads, so a song remains fully playable when Apple Music has no lyrics.

Octave uses the system Python selected by `python3` (or `python`). Python
3.11 or newer is supported; the installer does not require exactly Python
3.11. `uv` is used to create an isolated tool environment and install Python
dependencies, so project packages do not need to be installed globally.

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

The application creates `~/.config/octave/config.toml` on first run. Media,
playlists, cookies, and the SQLite index live below the configured library path.
Uninstalling Octave
does not remove your music library.

Commands: `octave import URL`, `octave playlists`, `octave songs`,
`octave update`, `octave status`, `octave config`, and `octave` to launch
the TUI. `amt` remains available as a compatibility alias.

Cookies are sensitive Netscape-format browser cookies. They are never logged,
stored in the library, or included in this repository.

## Useful commands

```bash
octave status       # Show the number of indexed tracks
octave update       # Rescan the local music library
octave playlists    # List imported playlists
octave songs        # List indexed songs and file paths
octave config       # Print the active configuration path
octave              # Launch the TUI
```

## Configuration and storage

The default configuration is stored at `~/.config/octave/config.toml`. Media
is stored under `~/.config/octave` by default, with the SQLite index in the same
directory. The theme selected with `Ctrl+T` is saved in the `[ui]`
section and restored on the next launch.

### Editable playlists

Playlist membership is stored in editable TOML files under
`~/.config/octave/Playlists/<playlist-name>/playlist.toml`. SQLite remains the
fast local index for song metadata; it is not the file users need to edit.
Each playlist file contains a `tracks` list with paths relative to the library:

```toml
name = "Road Trip"
source_url = ""
updated_at = ""
tracks = [
  "Artist/Album/song-one.m4a",
  "song-two.mp3",
]
```

Add or remove paths in `tracks`, run `octave update` to index new audio files,
then reopen or rescan the playlist in the TUI. Apple Music imports create the
initial `tracks` list from the downloaded playlist; later TOML edits are kept.

To use another library or player, edit the configuration file, for example:

```toml
[library]
path = "~/.config/octave"

[playback]
player = "mpv"

[ui]
theme = "textual-dark"
```

Logs are stored under the platform's user state directory. On most Linux
systems this is `~/.local/state/octave/log/amt.log`.

## Troubleshooting

- Check `python3 --version`; it must be 3.11 or newer.
- Check `command -v octave`, `command -v gamdl`, `command -v mpv`, and
  `command -v ffmpeg` if installation or playback fails.
- Run `octave status` before launching the TUI to confirm that the library is
  configured and readable.
- Imports require a valid Netscape-format Apple Music cookie export. Cookies
  may expire and need to be exported again.
- If the application menu does not refresh immediately, run:

  ```bash
  update-desktop-database ~/.local/share/applications
  ```

## Uninstall

Remove the Octave command and application-menu entry with:

```bash
./uninstall.sh
```

This keeps your music library and configuration. Remove `~/.config/octave`
manually only if you also want to delete your settings and cookies.
