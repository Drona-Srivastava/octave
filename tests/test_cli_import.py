from pathlib import Path

from apple_music_tui import cli


def test_import_rejects_successful_gamdl_with_no_audio(tmp_path, monkeypatch, capsys):
    config = tmp_path / "config.toml"
    config.write_text(f'[library]\npath = "{tmp_path / "library"}"\n[gamdl]\ncookies = "{tmp_path / "cookies.txt"}"\n')
    (tmp_path / "cookies.txt").write_text("# Netscape HTTP Cookie File\n")
    monkeypatch.setattr(cli, "log_path", lambda: tmp_path / "amt.log")
    monkeypatch.setattr(cli.Gamdl, "run", lambda self, url: type("Result", (), {"output": "done"})())
    assert cli.main(["--config", str(config), "import", "https://music.apple.com/us/playlist/test/pl.1"]) == 1
    assert "produced no audio files" in capsys.readouterr().err
