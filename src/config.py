from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

import tomllib
from platformdirs import user_config_dir, user_log_dir


@dataclass
class Config:
    library_path: Path
    gamdl_binary: str = "gamdl"
    cookies_path: Path | None = None
    player: str = "mpv"
    theme: str = "textual-dark"
    codec: str = "aac-web"
    cover_art: bool = True
    save_playlist: bool = True

    @property
    def index_path(self) -> Path:
        return self.library_path / "library.db"


def config_path() -> Path:
    return Path(user_config_dir("octave")) / "config.toml"


def default_config() -> Config:
    base = Path(user_config_dir("octave"))
    return Config(base, cookies_path=base / "cookies.txt")


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    config = default_config()
    if path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)
        library = raw.get("library", {})
        gamdl = raw.get("gamdl", {})
        downloads = raw.get("downloads", {})
        playback = raw.get("playback", {})
        ui = raw.get("ui", {})
        config.library_path = Path(os.path.expanduser(library.get("path", str(config.library_path))))
        config.gamdl_binary = str(gamdl.get("binary", config.gamdl_binary))
        cookies = gamdl.get("cookies", str(config.cookies_path))
        config.cookies_path = Path(os.path.expanduser(cookies)) if cookies else None
        config.player = str(playback.get("player", config.player))
        config.theme = str(ui.get("theme", config.theme))
        config.codec = str(downloads.get("codec", downloads.get("format", config.codec)))
        config.cover_art = bool(downloads.get("cover_art", config.cover_art))
        config.save_playlist = bool(downloads.get("save_playlist", config.save_playlist))
    return config


def save_config(config: Config, path: Path | None = None) -> None:
    """Persist Octave settings."""
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cookies = str(config.cookies_path) if config.cookies_path else ""
    path.write_text(
        f'''[library]\npath = "{config.library_path}"\n\n[gamdl]\nbinary = "{config.gamdl_binary}"\ncookies = "{cookies}"\n\n[playback]\nplayer = "{config.player}"\n\n[ui]\ntheme = "{config.theme}"\n\n[downloads]\ncodec = "{config.codec}"\ncover_art = {str(config.cover_art).lower()}\nsave_playlist = {str(config.save_playlist).lower()}\n'''
    )


def ensure_config(path: Path | None = None) -> Path:
    path = path or config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('''[library]\npath = "~/.config/octave"\n\n[gamdl]\nbinary = "gamdl"\ncookies = "~/.config/octave/cookies.txt"\n\n[playback]\nplayer = "mpv"\n\n[ui]\ntheme = "textual-dark"\n\n[downloads]\ncodec = "aac-web"\ncover_art = true\nsave_playlist = true\n''')
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def log_path() -> Path:
    path = Path(user_log_dir("octave"))
    path.mkdir(parents=True, exist_ok=True)
    return path / "amt.log"
