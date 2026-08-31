from apple_music_tui.cli import playlist_name, valid_playlist_url


def test_playlist_url_validation():
    assert valid_playlist_url("https://music.apple.com/us/playlist/chill/pl.abc123")
    assert valid_playlist_url("https://music.apple.com/us/library/playlist/p.7PkeqWdC0gRd2z8")
    assert not valid_playlist_url("https://example.com/playlist/chill")


def test_playlist_name():
    assert playlist_name("https://music.apple.com/us/playlist/my-chill/pl.abc") == "my chill"
