from pathlib import Path

import pytest

from apple_music_tui.playback import MpvPlayer, PlaybackError


def test_missing_mpv_is_clear(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(PlaybackError, match="mpv not found"):
        MpvPlayer().play(Path("track.m4a"))


def test_pause_sends_ipc_command(tmp_path, monkeypatch):
    player = MpvPlayer()
    player.process = type("Process", (), {"poll": lambda self: None})()
    player.socket_path = str(tmp_path / "missing.sock")
    # A missing IPC socket is safely ignored.
    player.pause_toggle()


def test_seek_sends_relative_ipc_command(monkeypatch):
    player = MpvPlayer()
    player.process = type("Process", (), {"poll": lambda self: None})()
    player.socket_path = "/tmp/mpv.sock"
    commands = []
    monkeypatch.setattr(player, "_command", lambda command: commands.append(command) or {})
    player.seek(5)
    player.seek(-5)
    assert commands == [["seek", 5, "relative"], ["seek", -5, "relative"]]
