from __future__ import annotations

import shutil
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path


class PlaybackError(RuntimeError):
    pass


class MpvPlayer:
    def __init__(self, binary: str = "mpv"):
        self.binary = binary
        self.process: subprocess.Popen | None = None
        self.socket_path: str | None = None

    def play(self, path: Path) -> None:
        if not shutil.which(self.binary):
            raise PlaybackError("mpv not found. Install mpv and ensure it is available in PATH.")
        self.stop()
        self.socket_path = os.path.join(tempfile.gettempdir(), f"amt-mpv-{os.getpid()}.sock")
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
        self.process = subprocess.Popen([
            self.binary, "--no-video", "--no-audio-display", "--no-terminal",
            "--really-quiet", f"--input-ipc-server={self.socket_path}", str(path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
           stdin=subprocess.DEVNULL)

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None
        if self.socket_path:
            try:
                os.unlink(self.socket_path)
            except FileNotFoundError:
                pass

    def pause_toggle(self) -> None:
        if not self.process or self.process.poll() is not None or not self.socket_path:
            return
        self._command(["cycle", "pause"])

    def time_position(self) -> float:
        response = self._command(["get_property", "time-pos"])
        try:
            return float(response.get("data") or 0)
        except (TypeError, ValueError):
            return 0.0

    def duration(self) -> float:
        response = self._command(["get_property", "duration"])
        try:
            return float(response.get("data") or 0)
        except (TypeError, ValueError):
            return 0.0

    def finished(self) -> bool:
        if self.process and self.process.poll() is not None:
            return True
        response = self._command(["get_property", "idle-active"])
        return bool(response.get("data"))

    def _command(self, command: list[str]) -> dict:
        if not self.process or self.process.poll() is not None or not self.socket_path:
            return {}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.1)
                client.connect(self.socket_path)
                client.sendall((json.dumps({"command": command, "request_id": 1}) + "\n").encode())
                data = client.recv(4096).decode()
                return json.loads(data.splitlines()[0]) if data else {}
        except (OSError, json.JSONDecodeError):
            return {}
