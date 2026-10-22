"""Tiny control channel so another process can pause / quit / raise the running app:

    aircursor ctl toggle      (bind this to a keyboard shortcut = global panic key)
    aircursor ctl quit
    aircursor                 (launching again just raises the existing window)
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
from typing import Callable, Optional

TCP_PORT = 47650  # Windows fallback


def _address():
    if sys.platform.startswith("win"):
        return ("127.0.0.1", TCP_PORT), socket.AF_INET
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return os.path.join(base, f"aircursor-{os.getuid()}.sock"), socket.AF_UNIX


def send_command(cmd: str, timeout: float = 1.0) -> Optional[str]:
    """Send a command to the running instance. Returns its reply, or None if none is running."""
    addr, fam = _address()
    try:
        with socket.socket(fam, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(addr)
            s.sendall(cmd.encode() + b"\n")
            return s.recv(4096).decode().strip()
    except OSError:
        return None


class ControlServer:
    def __init__(self, handler: Callable[[str], str]):
        self.handler = handler
        self._sock: Optional[socket.socket] = None

    def start(self) -> bool:
        addr, fam = _address()
        if fam == socket.AF_UNIX and os.path.exists(addr):
            if send_command("ping", 0.5) is not None:
                return False  # another instance is alive
            os.unlink(addr)   # stale socket from a crash
        s = socket.socket(fam, socket.SOCK_STREAM)
        try:
            s.bind(addr)
        except OSError:
            return False
        if fam == socket.AF_UNIX:
            os.chmod(addr, 0o600)
        s.listen(4)
        self._sock = s
        threading.Thread(target=self._serve, daemon=True).start()
        return True

    def _serve(self):
        while self._sock:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            with conn:
                try:
                    cmd = conn.recv(256).decode().strip()
                    reply = "pong" if cmd == "ping" else self.handler(cmd)
                    conn.sendall((reply + "\n").encode())
                except Exception as e:  # never let a bad client kill the server
                    try:
                        conn.sendall(f"error: {e}\n".encode())
                    except OSError:
                        pass

    def stop(self):
        s, self._sock = self._sock, None
        if s:
            s.close()
            addr, fam = _address()
            if fam == socket.AF_UNIX and os.path.exists(addr):
                os.unlink(addr)
