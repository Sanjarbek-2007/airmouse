"""Command line entry point.

    aircursor                 open the app (or raise it if it's already running)
    aircursor run             headless mode: no window, prints recognised commands
    aircursor ctl <cmd>       control the running app: pause | resume | toggle | quit | show | status
    aircursor cameras         list detected cameras
    aircursor reset-config    restore default settings
"""
from __future__ import annotations

import argparse
import signal
import sys
import threading

from . import APP_NAME, __version__
from .config import CONFIG_PATH, Config
from .ipc import ControlServer, send_command


def cmd_ctl(args) -> int:
    reply = send_command(args.command)
    if reply is None:
        print(f"{APP_NAME} is not running.", file=sys.stderr)
        return 1
    print(reply)
    return 0


def cmd_cameras(_args) -> int:
    from .camera import list_local_cameras
    cams = list_local_cameras()
    if not cams:
        print("No local cameras found.")
    for c in cams:
        print(f"#{c.index}  {c.name}")
    return 0


def cmd_reset(_args) -> int:
    cfg = Config.load()
    cfg.reset_to_defaults()
    cfg.save()
    print(f"Settings reset ({CONFIG_PATH})")
    return 0


def cmd_run(args) -> int:
    """Headless: same engine as the GUI, output to the terminal. Ctrl+C quits."""
    from .engine import Engine
    cfg = Config.load()
    if args.camera is not None:
        cfg.camera_source = f"local:{args.camera}"
    if args.url:
        cfg.camera_source, cfg.phone_url = "url", args.url
    quit_ev = threading.Event()
    eng = Engine(cfg, live=not args.dry_run, on_event=lambda e: print(f"  {e}", flush=True))

    def handle(cmd: str) -> str:
        if cmd in ("toggle", "pause", "resume"):
            if cmd == "pause" or (cmd == "toggle" and not eng.paused):
                eng.pause("Paused by command")
            else:
                eng.resume()
            return "paused" if eng.paused else "running"
        if cmd == "quit":
            quit_ev.set()
            return "bye"
        if cmd == "status":
            return f"{eng.state.status} {'paused' if eng.paused else 'active'} {eng.state.label}"
        return "unknown command"

    server = ControlServer(handle)
    if not server.start():
        print(f"{APP_NAME} is already running (use `aircursor ctl quit` first).", file=sys.stderr)
        return 1
    signal.signal(signal.SIGINT, lambda *_: quit_ev.set())
    signal.signal(signal.SIGTERM, lambda *_: quit_ev.set())
    print(f"{APP_NAME} running ({'dry run' if args.dry_run else 'LIVE'}). Ctrl+C or `aircursor ctl quit` to stop.")
    eng.start()
    last = None
    while not quit_ev.wait(0.5):
        s = eng.state
        if s.status != last:
            print(f"[{s.status}] {s.source} {s.message}".strip(), flush=True)
            last = s.status
        if s.warning and last == "starting":
            print(s.warning, file=sys.stderr)
    eng.stop()
    server.stop()
    print("bye")
    return 0


def cmd_gui(args) -> int:
    from .gui.app import run_gui
    return run_gui(live=not getattr(args, "dry_run", False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aircursor", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("gui", help="open the app (default)")
    g.add_argument("--dry-run", action="store_true", help="detect only; never touch the cursor")
    g.set_defaults(fn=cmd_gui)
    r = sub.add_parser("run", help="headless mode")
    r.add_argument("--dry-run", action="store_true", help="detect only; never touch the cursor")
    r.add_argument("--camera", type=int, help="local camera index")
    r.add_argument("--url", help="phone MJPEG stream URL")
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("ctl", help="control the running app")
    c.add_argument("command", choices=["pause", "resume", "toggle", "quit", "show", "status"])
    c.set_defaults(fn=cmd_ctl)
    sub.add_parser("cameras", help="list cameras").set_defaults(fn=cmd_cameras)
    sub.add_parser("reset-config", help="restore defaults").set_defaults(fn=cmd_reset)
    args = ap.parse_args(argv)
    return (args.fn or cmd_gui)(args) if getattr(args, "fn", None) else cmd_gui(args)
