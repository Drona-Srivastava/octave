from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from .config import Config


class DownloadError(RuntimeError):
    pass


@dataclass
class DownloadResult:
    command: list[str]
    returncode: int
    output: str


class Gamdl:
    def __init__(self, config: Config):
        self.config = config

    def command(self, url: str) -> list[str]:
        # Keep Gamdl fully controlled by Octave instead of inheriting a user's
        # unrelated ~/.gamdl/config.ini settings. Missing lyrics must never
        # prevent a playable audio file from being downloaded.
        temp_path = self.config.library_path / ".gamdl-temp"
        cmd = [self.config.gamdl_binary, "--no-config-file",
               "--output-path", str(self.config.library_path),
               "--temp-path", str(temp_path),
               "--download-mode", "ytdlp", "--ffmpeg-path", "ffmpeg",
               "--song-codec-priority", self.config.codec,
               "--no-synced-lyrics"]
        if self.config.cookies_path:
            cmd += ["--cookies-path", str(self.config.cookies_path)]
        if self.config.cover_art:
            cmd.append("--save-cover")
        if self.config.save_playlist:
            cmd.append("--save-playlist")
        cmd.append(url)
        return cmd

    def run(self, url: str, on_output: Callable[[str], None] | None = None) -> DownloadResult:
        if not shutil.which(self.config.gamdl_binary):
            raise DownloadError(f"{self.config.gamdl_binary} not found. Install gamdl and ensure it is available in PATH.")
        if not self.config.cookies_path or not self.config.cookies_path.is_file():
            raise DownloadError(f"cookies.txt not found: {self.config.cookies_path or '(not configured)'}")
        self.config.library_path.mkdir(parents=True, exist_ok=True)
        (self.config.library_path / ".gamdl-temp").mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.Popen(self.command(url), text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, bufsize=1)
            output_lines: list[str] = []
            assert proc.stdout is not None
            for line in proc.stdout:
                output_lines.append(line)
                if on_output:
                    on_output(line.rstrip())
            proc.wait()
        except OSError as exc:
            raise DownloadError(f"Unable to start gamdl: {exc}") from exc
        output = "".join(output_lines)
        result = DownloadResult(self.command(url), proc.returncode, output)
        if proc.returncode:
            raise DownloadError(f"gamdl failed with exit code {proc.returncode}.\n{output[-4000:]}")
        return result
