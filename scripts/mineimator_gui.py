#!/usr/bin/env python3
"""Operate the unmodified native Mine-imator GUI through X11.

The program has no verified render CLI. This utility supplies a display and
explicit mouse/keyboard operations; export settings still use the native GUI.
The default :100 avoids the active validation session on :99.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
XROOT = ROOT / ".tools/x11/root"
EXECUTABLE = ROOT / ".tools/mineimator/official/Mine-imator/Mine-imator"


def log_checkpoint(path):
    stat = path.stat()
    return stat.st_ino, stat.st_size


def new_log_segment(path, checkpoint):
    """Read only post-request evidence, including a new log after rotation."""
    try:
        stat = path.stat()
        offset = checkpoint[1] if stat.st_ino == checkpoint[0] and stat.st_size >= checkpoint[1] else 0
        with path.open("rb") as handle:
            handle.seek(offset)
            return handle.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def project_load_confirmed(segment, path):
    """Require the requested opening and its later load completion in new logs."""
    requested = f"Opening project: {path}"
    target_seen = False
    for line in segment.splitlines():
        if "Opening project: " in line:
            # Another opening invalidates an earlier, unfinished target request.
            target_seen = line.endswith(requested)
        elif target_seen and line.endswith("Project loaded"):
            return True
    return False


def process_identity(pid):
    try:
        # starttime is field 22; comm may contain spaces or parentheses.
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        if stat[0] == "Z":
            return None
        return stat[19]
    except (OSError, IndexError):
        return None


def run(command, env, **kwargs):
    return subprocess.run(command, env=env, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display", default=":100")
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("start", help="start an owned Xvfb display and Mine-imator")
    start.add_argument("--size", default="1600x1000")
    sub.add_parser("status")
    sub.add_parser("stop", help="stop only process identities recorded by this utility")
    click = sub.add_parser("click")
    click.add_argument("x", type=int)
    click.add_argument("y", type=int)
    click.add_argument("--button", type=int, default=1)
    click.add_argument("--hold", type=float, default=0.4)
    key = sub.add_parser("key")
    key.add_argument("chord", help="xdotool key chord, e.g. ctrl+o")
    key.add_argument("--hold", type=float, default=0.2)
    text = sub.add_parser("text", help="read text from stdin and paste through the X clipboard")
    text.add_argument("--delay", type=int, default=50)
    text.add_argument("--method", choices=["clipboard", "typed"], default="clipboard")
    text.add_argument("--clipboard-wait", type=float, default=3,
                      help="seconds to serve clipboard selection requests after Ctrl+V")
    shot = sub.add_parser("screenshot")
    shot.add_argument("path", type=Path)
    resize = sub.add_parser("resize")
    resize.add_argument("window")
    resize.add_argument("width", type=int)
    resize.add_argument("height", type=int)
    opening = sub.add_parser("open-project", help="open a native project and verify its new load-completion log")
    opening.add_argument("path", type=Path)
    opening.add_argument("--log", type=Path, default=Path.home() / "Mine-imator/log.txt")
    opening.add_argument("--timeout", type=float, default=30,
                         help="maximum seconds to wait for native load-completion evidence")
    opening.add_argument("--dialog-title", default="Open project",
                         help="expected native file-picker title (change for a translated application)")
    args = parser.parse_args()
    number = args.display.removeprefix(":")
    if not number.isdigit():
        parser.error("--display must be a local display such as :100")
    env = dict(os.environ, DISPLAY=args.display, LIBGL_ALWAYS_SOFTWARE="1")
    lib = str(XROOT / "usr/lib/x86_64-linux-gnu")
    env["LD_LIBRARY_PATH"] = lib + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    env["PATH"] = str(XROOT / "usr/bin") + ":" + env.get("PATH", "")
    state_dir = ROOT / ".tools/mineimator/runtime"
    state_path = state_dir / f"display-{number}.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    def live_records():
        return {name: record for name, record in state.get("processes", {}).items()
                if process_identity(record["pid"]) == record["starttime"]}

    def xdo(*tokens, **kwargs):
        run([str(XROOT / "usr/bin/xdotool"), *map(str, tokens)], env, **kwargs)

    def held_key(chord, hold=0.2):
        # keydown consumes all following command tokens in xdotool. Separate
        # invocations also preserve the held modifier until its matching keyup.
        xdo("keydown", chord)
        try:
            time.sleep(hold)
        finally:
            xdo("keyup", chord)

    def paste(value, wait=3):
        try:
            import tkinter
        except ImportError:
            raise SystemExit("Clipboard input requires tkinter; use text --method typed as a fallback")
        owner = tkinter.Tk(screenName=args.display)
        owner.withdraw()
        try:
            owner.clipboard_clear()
            owner.clipboard_append(value)
            owner.update()
            held_key("ctrl+v")
            # X11 selection data is requested asynchronously by Mine-imator.
            # Keep the owner alive and process Tcl events until transfer occurs.
            deadline = time.monotonic() + wait
            while time.monotonic() < deadline:
                owner.update()
                time.sleep(0.01)
        finally:
            owner.destroy()

    if args.action == "status":
        print(json.dumps({"display": args.display, "state": str(state_path),
                          "owned_processes": live_records()}, indent=2))
        return
    if args.action == "stop":
        for record in reversed(list(live_records().values())):
            try:
                os.killpg(record["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
        if state_path.exists():
            state_path.unlink()
        print("Sent SIGTERM only to matching owned process groups")
        return
    if args.action == "start":
        if live_records():
            raise SystemExit("An owned session is already running; inspect status before continuing")
        if not EXECUTABLE.is_file() or not (XROOT / "usr/bin/Xvfb").is_file():
            raise SystemExit("Run install_mineimator.py and install_mineimator_x11.py first")
        probe = subprocess.run(["xdpyinfo"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            raise SystemExit(f"Display {args.display} is already in use; it will not be replaced")
        if not args.size.replace("x", "").isdigit() or args.size.count("x") != 1:
            parser.error("--size must be WIDTHxHEIGHT")
        state_dir.mkdir(parents=True, exist_ok=True)
        state = {"display": args.display, "processes": {}}

        def launch(name, command, cwd=None):
            log = state_dir / f"display-{number}-{name}.log"
            with log.open("ab") as handle:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                           stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
            state["processes"][name] = {"pid": process.pid, "starttime": process_identity(process.pid),
                                        "log": str(log)}
            state_path.write_text(json.dumps(state, indent=2) + "\n")
            return process

        server = launch("xvfb", [str(XROOT / "usr/bin/Xvfb"), args.display, "-screen", "0",
                                 args.size + "x24", "-nolisten", "tcp", "-ac"])
        for _ in range(50):
            if server.poll() is not None:
                raise SystemExit("Xvfb exited; inspect the recorded log")
            if subprocess.run(["xdpyinfo"], env=env, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise SystemExit("Display did not become ready in five seconds; inspect the log")
        launch("mineimator", [str(EXECUTABLE)], EXECUTABLE.parent)
        print(json.dumps(state, indent=2))
        return
    if args.action == "click":
        xdo("mousemove", args.x, args.y, "mousedown", args.button, "sleep", args.hold,
            "mouseup", args.button)
        time.sleep(0.5)
    elif args.action == "key":
        held_key(args.chord, args.hold)
        time.sleep(0.5)
    elif args.action == "text":
        value = sys.stdin.buffer.read()
        if args.method == "clipboard":
            paste(value.decode("utf-8"), args.clipboard_wait)
        else:
            xdo("type", "--clearmodifiers", "--delay", args.delay, "--file", "-", input=value)
    elif args.action == "screenshot":
        if not shutil.which("import"):
            raise SystemExit("ImageMagick import is required for screenshots")
        args.path.parent.mkdir(parents=True, exist_ok=True)
        if args.path.exists():
            raise SystemExit("Screenshot exists; choose a new path to preserve evidence")
        run(["import", "-window", "root", str(args.path.resolve())], env)
        print(args.path.resolve())
    elif args.action == "resize":
        xdo("windowsize", args.window, args.width, args.height, "windowmove", args.window, 0, 0)
    elif args.action == "open-project":
        path = args.path.resolve(strict=True)
        if path.suffix.lower() != ".miproject":
            raise SystemExit("Expected a native .miproject file")
        try:
            checkpoint = log_checkpoint(args.log)
        except OSError:
            raise SystemExit(f"Cannot read native runtime log {args.log}; no open request sent")
        xdotool = str(XROOT / "usr/bin/xdotool")
        editor_window = subprocess.check_output([xdotool, "getwindowfocus"], env=env).decode().strip()
        editor_title = subprocess.check_output([xdotool, "getwindowname", editor_window], env=env).decode().strip()
        held_key("ctrl+o")
        time.sleep(1)
        focused = subprocess.check_output([str(XROOT / "usr/bin/xdotool"), "getwindowfocus"], env=env).decode().strip()
        title = subprocess.check_output([str(XROOT / "usr/bin/xdotool"), "getwindowname", focused], env=env).decode().strip()
        if title != args.dialog_title:
            raise SystemExit(
                f"Expected native file picker {args.dialog_title!r}, found {title!r}. "
                "No path was pasted. Inspect a screenshot and resolve any unsaved-project "
                "confirmation or other popup before trying again."
            )
        paste(str(path))
        # Qt may close the file picker on keydown. A longer hold leaks Return
        # into the editor and can start timeline playback after the dialog closes.
        held_key("Return", hold=0.03)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if project_load_confirmed(new_log_segment(args.log, checkpoint), path):
                # Xvfb without a window manager can leave focus on the X root
                # after Qt closes its picker. Restore only the verified editor
                # that initiated this request, after native load completion.
                if editor_title == "Mine-imator" or editor_title.endswith(" - Mine-imator"):
                    xdo("windowfocus", "--sync", editor_window)
                print(json.dumps({"project": str(path), "native_load_confirmed": True,
                                  "evidence": str(args.log)}))
                return
            time.sleep(0.25)
        raise SystemExit(
            "Native project load was NOT confirmed: new runtime logs must contain "
            f"'Opening project: {path}' followed by 'Project loaded'. "
            "Inspect a screenshot and the native log; resolve prompts before retrying. "
            "Do not continue with animation/export based only on the open request."
        )


if __name__ == "__main__":
    main()
