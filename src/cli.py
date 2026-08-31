from __future__ import annotations

import argparse
import logging
import re
import shutil
import stat
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from .config import config_path, ensure_config, load_config, log_path
from .downloader import DownloadError, Gamdl
from .library import Library
from .playback import MpvPlayer

PLAYLIST_RE = re.compile(
    r"^https?://music\.apple\.com/[^/?#]+/"
    r"(?:playlist/[^/?#]+(?:/[^/?#]+)?|library/playlist/[^/?#]+)"
    r"(?:[?#].*)?/?$"
)


def valid_playlist_url(url: str) -> bool:
    return bool(PLAYLIST_RE.match(url))


def playlist_name(url: str) -> str:
    parts = [unquote(part) for part in urlparse(url).path.split("/") if part]
    candidate = next((part for part in reversed(parts) if not part.startswith("pl.")), "Imported playlist")
    return candidate.replace("-", " ").strip() or "Imported playlist"


def import_playlist(config, library: Library, url: str) -> int:
    if not valid_playlist_url(url):
        print("[ERROR] Invalid Apple Music playlist URL", file=sys.stderr)
        return 2
    try:
        print(f"Downloading {playlist_name(url)} with gamdl...")
        result = Gamdl(config).run(url)
        if result.output.strip():
            print(result.output.rstrip())
    except DownloadError as exc:
        logging.error(str(exc)); print(f"[ERROR] {exc}", file=sys.stderr); return 1
    count = library.scan()
    if count == 0:
        print("[ERROR] gamdl produced no audio files. Check its output, cookies, and dependencies.", file=sys.stderr)
        return 1
    library.register_playlist(playlist_name(url), url)
    print(f"Imported successfully ({count} tracks indexed) into {config.library_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="octave")
    parser.add_argument("--config", type=Path, default=None)
    sub = parser.add_subparsers(dest="command")
    imp = sub.add_parser("import", help="download and index an Apple Music playlist")
    imp.add_argument("url")
    setup = sub.add_parser("setup", help="configure cookies and import playlists")
    setup.add_argument("--cookies", required=True, type=Path)
    setup.add_argument("--playlist", action="append", required=True, help="playlist URL; repeat for multiple playlists")
    for name in ("playlists", "songs", "update", "status", "config"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    path = ensure_config(args.config)
    config = load_config(path)
    logging.basicConfig(filename=log_path(), level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    library = Library(config.library_path)
    if args.command == "config":
        print(path); return 0
    if args.command == "import":
        return import_playlist(config, library, args.url)
    if args.command == "setup":
        if not args.cookies.is_file():
            print(f"[ERROR] Cookies file not found: {args.cookies}", file=sys.stderr); return 1
        if not config.cookies_path:
            print("[ERROR] No cookies destination configured", file=sys.stderr); return 1
        config.cookies_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.cookies, config.cookies_path)
        config.cookies_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        print(f"Installed cookies at {config.cookies_path}")
        for url in args.playlist:
            result = import_playlist(config, library, url)
            if result:
                return result
        return 0
    if args.command == "playlists":
        print("\n".join(library.playlists())); return 0
    if args.command == "songs":
        print("\n".join(f"{t.artist} — {t.title} [{t.path}]" for t in library.tracks())); return 0
    if args.command == "update":
        count = library.scan()
        print(f"Indexed {count} tracks in {config.library_path}"); return 0
    if args.command == "status":
        print(f"{len(library.tracks())} indexed tracks in {config.library_path}"); return 0
    from .tui import MusicApp
    MusicApp(library, MpvPlayer(config.player), config, path).run(); return 0
