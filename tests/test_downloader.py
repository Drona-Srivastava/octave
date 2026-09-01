from pathlib import Path

import pytest

from apple_music_tui.config import Config
from apple_music_tui.downloader import DownloadError, Gamdl


def test_command_contains_safe_options(tmp_path):
    cfg = Config(tmp_path, cookies_path=tmp_path / "cookies.txt")
    command = Gamdl(cfg).command("https://music.apple.com/us/playlist/example/pl.1")
    assert command[-1].startswith("https://music.apple.com/")
    assert "--no-config-file" in command
    assert "--no-synced-lyrics" not in command
    assert command[command.index("--synced-lyrics-format") + 1] == "lrc"
    assert command[command.index("--download-mode") + 1] == "ytdlp"
    assert str(tmp_path / ".gamdl-temp") in command
    assert "--cookies-path" in command
    assert "--save-playlist" in command


def test_missing_cookies_is_clear(tmp_path, monkeypatch):
    cfg = Config(tmp_path, cookies_path=tmp_path / "cookies.txt")
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/gamdl")
    with pytest.raises(DownloadError, match="cookies.txt not found"):
        Gamdl(cfg).run("https://music.apple.com/us/playlist/example/pl.1")
