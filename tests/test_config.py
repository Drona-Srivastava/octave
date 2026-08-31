from pathlib import Path

from apple_music_tui.config import Config, load_config, save_config


def test_config_expands_paths(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[library]\npath = "~/Music/Test"\n[gamdl]\ncookies = "~/cookies.txt"\n')
    config = load_config(path)
    assert config.library_path == Path.home() / "Music" / "Test"
    assert config.cookies_path == Path.home() / "cookies.txt"


def test_missing_config_uses_defaults(tmp_path):
    config = load_config(tmp_path / "missing.toml")
    assert config.gamdl_binary == "gamdl"
    assert config.player == "mpv"


def test_theme_round_trips(tmp_path):
    path = tmp_path / "config.toml"
    save_config(Config(tmp_path / "library", theme="monokai"), path)
    assert load_config(path).theme == "monokai"
