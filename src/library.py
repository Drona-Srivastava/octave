from __future__ import annotations

import sqlite3
import re
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from mutagen import File


@dataclass
class Track:
    path: str
    title: str
    artist: str
    album: str
    track_number: int | None = None
    duration: float | None = None


class Library:
    def __init__(self, root: Path):
        self.root = root.expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "library.db"
        with self.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS tracks (path TEXT PRIMARY KEY, title TEXT NOT NULL, artist TEXT NOT NULL, album TEXT NOT NULL, track_number INTEGER, duration REAL); CREATE TABLE IF NOT EXISTS playlists (name TEXT PRIMARY KEY, source_url TEXT, updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS playlist_tracks (playlist TEXT, path TEXT, position INTEGER, PRIMARY KEY(playlist,path));""")

    def connect(self):
        db = sqlite3.connect(self.db)
        db.row_factory = sqlite3.Row
        return db

    def scan(self) -> int:
        count = 0
        with self.connect() as db:
            for path in self.root.rglob("*"):
                if path.suffix.lower() not in {".m4a", ".mp3", ".flac", ".ogg", ".opus", ".wav"}:
                    continue
                try:
                    audio = File(path, easy=True)
                except Exception:
                    audio = None
                tags = audio.tags if audio else {}
                get = lambda key, default="Unknown": (tags.get(key, [default])[0] if tags else default)
                track = get("tracknumber", "").split("/")[0]
                db.execute("INSERT OR REPLACE INTO tracks VALUES (?,?,?,?,?,?)", (str(path.relative_to(self.root)), get("title", path.stem), get("artist"), get("album"), int(track) if track.isdigit() else None, audio.info.length if audio and audio.info else None))
                count += 1
        return count

    def tracks(self) -> list[Track]:
        with self.connect() as db:
            return [Track(r["path"], r["title"], r["artist"], r["album"], r["track_number"], r["duration"]) for r in db.execute("SELECT * FROM tracks ORDER BY artist, album, track_number, title")]

    def tracks_for_playlist(self, name: str) -> list[Track]:
        self.sync_playlist(name)
        with self.connect() as db:
            rows = db.execute("""SELECT t.* FROM tracks t
                JOIN playlist_tracks pt ON pt.path = t.path
                WHERE pt.playlist = ? ORDER BY pt.position""", (name,))
            return [Track(r["path"], r["title"], r["artist"], r["album"], r["track_number"], r["duration"]) for r in rows]

    def playlists(self) -> list[str]:
        with self.connect() as db:
            return [r[0] for r in db.execute("SELECT name FROM playlists ORDER BY name")]

    def register_playlist(self, name: str, url: str) -> None:
        from datetime import datetime, timezone
        safe = re.sub(r"[^A-Za-z0-9._ -]+", "", name).strip() or "Imported playlist"
        playlist_dir = self.root / "Playlists" / safe
        playlist_dir.mkdir(parents=True, exist_ok=True)
        updated = datetime.now(timezone.utc).isoformat()
        # Leave tracks absent on first creation so an imported m3u can seed it.
        # Once written, the TOML tracks list becomes the editable source of truth.
        (playlist_dir / "playlist.toml").write_text(f'name = {json.dumps(name)}\nsource_url = {json.dumps(url)}\nupdated_at = {json.dumps(updated)}\n')
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO playlists VALUES (?,?,?)", (name, url, updated))
        self.sync_playlist(name)

    def sync_playlist(self, name: str) -> int:
        """Sync editable TOML playlist membership into the SQLite index."""
        playlist_root = self.root / "Playlists"
        safe = re.sub(r"[^A-Za-z0-9._ -]+", "", name).strip()
        playlist_file = playlist_root / safe / "playlist.toml"
        paths: list[str] | None = None
        raw: dict = {}
        if playlist_file.exists():
            with playlist_file.open("rb") as stream:
                raw = tomllib.load(stream)
            tracks = raw.get("tracks")
            if isinstance(tracks, list):
                paths = [path for path in tracks if isinstance(path, str)]

        if paths is None:
            candidates = list(playlist_root.rglob("*.m3u")) if playlist_root.exists() else []
            matching = [path for path in candidates if path.stem == name or path.stem == safe]
            source = max(matching or candidates, key=lambda path: path.stat().st_mtime, default=None)
            paths = []
            if source is not None:
                for line in source.read_text(errors="replace").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        relative = (source.parent / line).resolve().relative_to(self.root.resolve())
                    except ValueError:
                        continue
                    paths.append(str(relative))
                if playlist_file.exists():
                    playlist_file.write_text(
                        f'name = {json.dumps(raw.get("name", name))}\n'
                        f'source_url = {json.dumps(raw.get("source_url", ""))}\n'
                        f'updated_at = {json.dumps(raw.get("updated_at", ""))}\n'
                        f'tracks = {json.dumps(paths, ensure_ascii=False, indent=2)}\n'
                    )
        with self.connect() as db:
            db.execute("DELETE FROM playlist_tracks WHERE playlist = ?", (name,))
            for position, path in enumerate(paths):
                if db.execute("SELECT 1 FROM tracks WHERE path = ?", (path,)).fetchone():
                    db.execute("INSERT OR REPLACE INTO playlist_tracks VALUES (?,?,?)", (name, path, position))
        return len(paths)

    def rename_playlist(self, old_name: str, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            return
        with self.connect() as db:
            db.execute("UPDATE playlists SET name = ? WHERE name = ?", (new_name, old_name))
            db.execute("UPDATE playlist_tracks SET playlist = ? WHERE playlist = ?", (new_name, old_name))

    def playlist_url(self, name: str) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT source_url FROM playlists WHERE name = ?", (name,)).fetchone()
            return row[0] if row else None

    def delete_playlist(self, name: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM playlist_tracks WHERE playlist = ?", (name,))
            db.execute("DELETE FROM playlists WHERE name = ?", (name,))

    def remove_from_playlist(self, name: str, path: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM playlist_tracks WHERE playlist = ? AND path = ?", (name, path))
