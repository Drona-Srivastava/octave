import re
import random
from pathlib import Path
from urllib.parse import unquote, urlparse

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, ProgressBar, Static
from textual_image.widget import Image
from textual.worker import Worker
from rich.text import Text

from .config import Config, save_config
from .downloader import DownloadError, Gamdl
from .library import Library
from .playback import MpvPlayer, PlaybackError


class TextPrompt(ModalScreen[str | None]):
    def __init__(self, title: str, action: str, value: str = ""):
        super().__init__()
        self.title_text, self.action_text, self.value = title, action, value

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.title_text)
            yield Input(value=self.value, id="value")
            with Horizontal(id="dialog-buttons"):
                yield Button(self.action_text, variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#ok")
    def submit(self) -> None:
        self.dismiss(self.query_one("#value", Input).value.strip())


class AddPlaylistPrompt(ModalScreen[tuple[str, str, str] | None]):
    def __init__(self, cookies: str):
        super().__init__()
        self.cookies = cookies

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Add Apple Music playlist")
            yield Label("cookies.txt path")
            yield Input(value=self.cookies, placeholder="/path/to/cookies.txt", id="cookies")
            yield Label("Playlist name")
            yield Input(placeholder="My playlist", id="name")
            yield Label("Playlist URL")
            yield Input(placeholder="https://music.apple.com/...", id="url")
            with Horizontal(id="dialog-buttons"):
                yield Button("Import", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#ok")
    def submit(self) -> None:
        cookies = self.query_one("#cookies", Input).value.strip()
        name = self.query_one("#name", Input).value.strip()
        url = self.query_one("#url", Input).value.strip()
        self.dismiss((cookies, url, name) if url else None)


class MusicApp(App):
    TITLE = "Octave — Apple Music TUI"
    BINDINGS = [("q", "quit", "Quit"), ("a", "add_playlist", "Add"), ("r", "rename_playlist", "Rename"),
                ("p", "pause", "Pause/play"), ("n", "next", "Next"), ("b", "previous", "Previous"),
                ("s", "shuffle", "Shuffle"), ("t", "repeat", "Repeat"), ("l", "toggle_album", "Album"), ("/", "search", "Search"),
                ("o", "sort", "Sort"), ("u", "rescan", "Rescan"), ("f", "refresh_playlist", "Refresh"),
                ("ctrl+t", "change_theme", "Theme"),
                ("d", "delete_playlist", "Delete playlist"), ("x", "remove_song", "Remove song")]
    CSS = """
    Screen { background: $background; }
    #now-playing { height: 16; border: round $accent; padding: 1 2; background: $surface; }
    #art-frame { width: 28; height: 13; padding: 0; overflow: hidden; }
    #art { width: 26; height: 13; }
    #track-info { width: 1fr; padding: 0 2; border-left: solid $panel; }
    #track-title { text-style: bold; color: $accent; }
    #lyrics { height: 1fr; color: $text-muted; overflow: hidden; }
    #playback-progress { width: 1fr; height: 1; margin-top: 1; }
    #library-title { height: 2; padding: 1 1 0 1; text-style: bold; color: $accent; }
    #library { height: 1fr; }
    #playlists { width: 28; margin-right: 1; border: round $panel; background: $surface; }
    #tracks { width: 1fr; border: round $accent; background: $surface; }
    #import-progress { height: 1; margin: 0 1; display: none; }
    #status { height: 2; padding: 0 1; color: $text-muted; background: $surface; }
    #dialog { width: 70; height: auto; margin: 4 8; padding: 1 2; background: $surface; border: round $accent; }
    #dialog Input { margin: 1 0; }
    #dialog-buttons { height: 3; }
    #dialog Button { width: 1fr; margin: 0 1; }
    """

    def __init__(self, library: Library, player: MpvPlayer, config: Config, config_path: Path | None = None):
        super().__init__()
        self.library, self.player, self.config = library, player, config
        self.config_path = config_path
        if config.theme in self.available_themes:
            self.theme = config.theme
        self.all_tracks = library.tracks()
        self.tracks, self.playlist_names = self.all_tracks, ["All Songs", *library.playlists()]
        self.active_playlist = "All Songs"
        self.current_index: int | None = None
        self.current_path: str | None = None
        self.lyrics: list[tuple[float, str]] = []
        self.import_worker: Worker[None] | None = None
        self.shuffle_enabled = False
        self.repeat_enabled = False
        self.queue: list[int] = []
        self.search_term = ""
        self.sort_mode = 0
        self.show_album = False

    def watch_theme(self, theme: str) -> None:
        self.config.theme = theme
        save_config(self.config, self.config_path)

    def on_mount(self) -> None:
        self.set_interval(0.5, self.update_lyrics)
        self.set_interval(0.5, self.check_playback)

    def on_unmount(self) -> None:
        if self.import_worker and not self.import_worker.is_finished:
            self.import_worker.cancel()
        self.player.stop()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal(id="now-playing"):
                with Vertical(id="art-frame"):
                    yield Image(id="art")
                with Vertical(id="track-info"):
                    yield Label("Nothing playing", id="track-title")
                    yield Label("Select a song and press Enter", id="track-meta")
                    yield Static("Lyrics will appear here when available.", id="lyrics")
                    yield ProgressBar(total=100, show_eta=False, id="playback-progress")
            yield Label(f"YOUR LIBRARY  •  {len(self.all_tracks)} songs  •  A add  R rename", id="library-title")
            with Horizontal(id="library"):
                yield ListView(*(ListItem(Label(name)) for name in self.playlist_names), id="playlists")
                yield ListView(*(ListItem(Label(self._track_label(t))) for t in self.tracks), id="tracks")
            yield ProgressBar(total=100, show_eta=False, id="import-progress")
            yield Label("Enter play   P pause   N/B next/prev   S shuffle   T repeat   / search   O sort   U rescan", id="status")
        yield Footer()

    @on(ListView.Selected, "#tracks")
    def play_selected(self, event: ListView.Selected) -> None:
        try:
            self.play_index(self.query_one("#tracks", ListView).children.index(event.item))
        except (ValueError, PlaybackError) as exc:
            self.query_one("#status", Label).update(f"Playback error: {exc}")

    @on(ListView.Selected, "#playlists")
    def select_playlist(self, event: ListView.Selected) -> None:
        view = self.query_one("#playlists", ListView)
        try:
            name = self.playlist_names[view.children.index(event.item)]
        except (ValueError, IndexError):
            return
        self.active_playlist = name
        self._load_playlist(name)
        self.query_one("#status", Label).update(f"{name}: {len(self.tracks)} songs")

    def _load_playlist(self, name: str) -> None:
        self.tracks = self.all_tracks if name == "All Songs" else self.library.tracks_for_playlist(name)
        if self.current_path is not None:
            self.current_index = next((i for i, track in enumerate(self.tracks) if track.path == self.current_path), None)
        self._apply_filters()

    def _apply_filters(self) -> None:
        if self.search_term:
            term = self.search_term.casefold()
            self.tracks = [track for track in self.tracks if term in f"{track.title} {track.artist} {track.album}".casefold()]
        self._render_tracks()

    def play_index(self, index: int) -> None:
        track = self.tracks[index]
        self.player.play(self.library.root / track.path)
        self.current_index = index
        self.current_path = track.path
        self.queue = list(range(len(self.tracks)))
        if self.shuffle_enabled:
            random.shuffle(self.queue)
        if index in self.queue:
            self.queue.remove(index)
        self.queue.insert(0, index)
        self.query_one("#track-title", Label).update(track.title)
        self.query_one("#track-meta", Label).update(f"{track.artist}  •  {track.album}")
        self._highlight_current_track()
        self.show_media_details(track.path)
        self.query_one("#status", Label).update(f"Playing: {track.artist} — {track.title}")

    def check_playback(self) -> None:
        if self.current_index is None or not self.player.finished():
            self.update_playback_progress()
            return
        self.action_next()

    def update_playback_progress(self) -> None:
        if self.current_index is None:
            return
        duration = self.player.duration() or self.tracks[self.current_index].duration or 0
        position = self.player.time_position()
        progress = min(100, position / duration * 100) if duration else 0
        self.query_one("#playback-progress", ProgressBar).update(progress=progress)

    def show_media_details(self, relative_path: str) -> None:
        path = self.library.root / relative_path
        cover = next((candidate for candidate in path.parent.iterdir() if candidate.is_file() and candidate.name.lower() in {"cover.jpg", "cover.jpeg", "cover.png"}), None)
        art = self.query_one("#art", Image)
        if cover:
            art.image = cover
        lyrics = path.with_suffix(".lrc")
        self.lyrics = []
        if lyrics.exists():
            for line in lyrics.read_text(errors="replace").splitlines():
                stamps = re.findall(r"\[(\d+):(\d+(?:\.\d+)?)\]", line)
                text = re.sub(r"\[[^\]]+\]", "", line).strip()
                self.lyrics.extend((int(minutes) * 60 + float(seconds), text) for minutes, seconds in stamps)
            self.lyrics.sort()
        self.update_lyrics()

    def update_lyrics(self) -> None:
        widget = self.query_one("#lyrics", Static)
        if not self.lyrics:
            widget.update("No synced lyrics available for this track.")
            return
        position = self.player.time_position()
        current = max((i for i, (timestamp, _) in enumerate(self.lyrics) if timestamp <= position), default=0)
        rendered = Text()
        for index in range(max(0, current - 2), min(len(self.lyrics), current + 3)):
            if rendered.plain:
                rendered.append("\n")
            if index == current:
                rendered.append("> ", style="bold yellow")
                rendered.append(self.lyrics[index][1] or "♪", style="bold yellow")
            else:
                rendered.append("  " + (self.lyrics[index][1] or "♪"), style="dim")
        widget.update(rendered)

    def action_pause(self) -> None:
        self.player.pause_toggle()
        self.query_one("#status", Label).update("Playback toggled")

    def action_next(self) -> None:
        if self.tracks:
            if self.repeat_enabled and self.current_index is not None:
                self.play_index(self.current_index)
                return
            if not self.shuffle_enabled:
                next_index = 0 if self.current_index is None else (self.current_index + 1) % len(self.tracks)
                self.play_index(next_index)
                return
            if not self.queue:
                self.queue = list(range(len(self.tracks)))
                if self.shuffle_enabled:
                    random.shuffle(self.queue)
            if self.current_index in self.queue:
                position = self.queue.index(self.current_index) + 1
            else:
                position = 0
            self.play_index(self.queue[position % len(self.queue)])

    def action_previous(self) -> None:
        if self.tracks:
            if self.current_index is None:
                self.play_index(0)
                return
            if not self.shuffle_enabled:
                self.play_index((self.current_index - 1) % len(self.tracks))
                return
            if self.queue and self.current_index in self.queue:
                position = (self.queue.index(self.current_index) - 1) % len(self.queue)
                self.play_index(self.queue[position])
            else:
                self.play_index((self.current_index - 1) % len(self.tracks))

    def action_shuffle(self) -> None:
        self.shuffle_enabled = not self.shuffle_enabled
        self.queue = []
        self._set_status(f"Shuffle {'on' if self.shuffle_enabled else 'off'}")

    def action_repeat(self) -> None:
        self.repeat_enabled = not self.repeat_enabled
        self._set_status(f"Repeat {'on' if self.repeat_enabled else 'off'}")

    def action_toggle_album(self) -> None:
        self.show_album = not self.show_album
        self._render_tracks()
        self._set_status(f"Album names {'shown' if self.show_album else 'hidden'}")

    def action_search(self) -> None:
        self.push_screen(TextPrompt("Search current playlist", "Search", self.search_term), self.search_tracks)

    def search_tracks(self, term: str | None) -> None:
        self.search_term = term or ""
        self._load_playlist(self.active_playlist)
        self._set_status(f"Search: {self.search_term or 'cleared'} ({len(self.tracks)} songs)")

    def action_sort(self) -> None:
        self.sort_mode = (self.sort_mode + 1) % 3
        labels = ["artist", "title", "album"]
        key = labels[self.sort_mode]
        self.tracks.sort(key=lambda track: (getattr(track, key).casefold(), track.title.casefold()))
        self.current_index = next((i for i, track in enumerate(self.tracks) if track.path == self.current_path), None)
        self.queue = []
        self._render_tracks()
        self._set_status(f"Sorted by {key}")

    def action_rescan(self) -> None:
        count = self.library.scan()
        self.all_tracks = self.library.tracks()
        self._load_playlist(self.active_playlist)
        self._set_status(f"Library rescanned: {count} tracks indexed")

    def action_delete_playlist(self) -> None:
        if self.active_playlist == "All Songs":
            self._set_status("All Songs cannot be deleted")
            return
        name = self.active_playlist
        self.library.delete_playlist(name)
        self.active_playlist = "All Songs"
        self.playlist_names = ["All Songs", *self.library.playlists()]
        self._load_playlist(self.active_playlist)
        playlists = self.query_one("#playlists", ListView)
        playlists.clear(); playlists.extend(ListItem(Label(item)) for item in self.playlist_names)
        self._set_status(f"Deleted playlist: {name}")

    def action_remove_song(self) -> None:
        selected = self.query_one("#tracks", ListView).index
        if self.active_playlist == "All Songs" or selected is None or selected >= len(self.tracks):
            self._set_status("Select a playlist and song first")
            return
        track = self.tracks[selected]
        self.library.remove_from_playlist(self.active_playlist, track.path)
        self._load_playlist(self.active_playlist)
        self._set_status(f"Removed {track.title} from {self.active_playlist}")

    def action_refresh_playlist(self) -> None:
        if self.active_playlist == "All Songs":
            self._set_status("Select a playlist to refresh it")
            return
        url = self.library.playlist_url(self.active_playlist)
        if url:
            self.push_screen(
                TextPrompt("Latest cookies.txt path", "Refresh", str(self.config.cookies_path or "")),
                lambda cookies: self._refresh_playlist(cookies, url),
            )

    def _refresh_playlist(self, cookies: str | None, url: str) -> None:
        if cookies:
            self.config.cookies_path = Path(cookies).expanduser()
        self.import_playlist((str(self.config.cookies_path or ""), url, self.active_playlist))

    def action_add_playlist(self) -> None:
        if self.import_worker and not self.import_worker.is_finished:
            self.query_one("#status", Label).update("An import is already in progress…")
            return
        self.push_screen(AddPlaylistPrompt(str(self.config.cookies_path or "")), self.import_playlist)

    def action_rename_playlist(self) -> None:
        view = self.query_one("#playlists", ListView)
        if view.index is not None and view.index < len(self.playlist_names):
            self.push_screen(TextPrompt("Rename playlist", "Save", self.playlist_names[view.index]), self.rename_playlist)

    def rename_playlist(self, name: str | None) -> None:
        view = self.query_one("#playlists", ListView)
        if name and view.index is not None and view.index < len(self.playlist_names):
            self.library.rename_playlist(self.playlist_names[view.index], name)
            self.playlist_names = self.library.playlists()
            view.clear(); view.extend(ListItem(Label(item)) for item in self.playlist_names)

    def import_playlist(self, values: tuple[str, str, str] | None) -> None:
        if not values:
            return
        cookies, url, name = values
        if cookies:
            self.config.cookies_path = Path(cookies).expanduser()
        self.query_one("#status", Label).update("Preparing playlist import…")
        self.query_one("#import-progress", ProgressBar).styles.display = "block"
        self.query_one("#import-progress", ProgressBar).update(progress=0)
        self.import_worker = self.run_worker(
            lambda: self._import_playlist_worker(url, name),
            name="playlist-import",
            thread=True,
            exclusive=True,
        )

    def _import_playlist_worker(self, url: str, name: str) -> None:
        try:
            Gamdl(self.config).run(url, on_output=self._import_progress)
            self.library.scan()
            self.all_tracks = self.library.tracks()
            self.library.register_playlist(name, url)
            self.call_from_thread(self._refresh_library, f"Playlist imported: {len(self.all_tracks)} songs indexed")
        except DownloadError as exc:
            self.call_from_thread(self._import_failed, f"Import error: {exc}")

    def _import_progress(self, line: str) -> None:
        match = re.search(r"\[Track\s+(\d+)/-\s*\]\s+Downloading\s+['\"](.+?)['\"]", line)
        if match:
            self.call_from_thread(self._set_status, f"Downloading track {match.group(1)}: {match.group(2)}")
            return
        match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
        if match:
            progress = float(match.group(1))
            self.call_from_thread(self._set_progress, progress)
            self.call_from_thread(self._set_status, "Downloading playlist…")

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Label).update(message)

    def _set_progress(self, progress: float) -> None:
        self.query_one("#import-progress", ProgressBar).update(progress=progress)

    def _import_failed(self, message: str) -> None:
        self.query_one("#import-progress", ProgressBar).styles.display = "none"
        self._set_status(message)

    def _refresh_library(self, message: str) -> None:
        self.all_tracks = self.library.tracks()
        self.playlist_names = ["All Songs", *self.library.playlists()]
        if self.active_playlist not in self.playlist_names:
            self.active_playlist = "All Songs"
        self._load_playlist(self.active_playlist)
        playlists = self.query_one("#playlists", ListView)
        playlists.clear()
        playlists.extend(ListItem(Label(item)) for item in self.playlist_names)
        self.query_one("#import-progress", ProgressBar).styles.display = "none"
        self._set_status(message)

    def _render_tracks(self) -> None:
        tracks = self.query_one("#tracks", ListView)
        tracks.clear()
        tracks.extend(ListItem(Label(self._track_label(t))) for t in self.tracks)
        self._highlight_current_track()

    def _highlight_current_track(self) -> None:
        if not self.is_mounted:
            return
        tracks = self.query_one("#tracks", ListView)
        if self.current_path is None:
            tracks.index = None
            return
        index = next((i for i, track in enumerate(self.tracks) if track.path == self.current_path), None)
        tracks.index = index

    def _track_label(self, track) -> str:
        return f"{track.title}  —  {track.album}" if self.show_album else track.title
