#!/usr/bin/env python3
"""View a rendered PLAN.html: serve it on localhost (default) or open it directly,
then launch Chrome to view it.

Companion to render_plan.py — render_plan *builds* the HTML, view_plan *displays* it.

Modes:
  server (default)  Start a localhost http.server rooted at the plan dir and open Chrome
                    at the URL. localhost is a secure context, so the "copy <verify>"
                    clipboard buttons use navigator.clipboard instead of the execCommand
                    fallback. Blocks until Ctrl+C (run in the background from an agent).
  --file            Open PLAN.html directly via file:// — no server, returns immediately.

If PLAN.html is missing or older than PLAN.md, it is (re)rendered first via render_plan.render().

Usage:
    python3 view_plan.py <PLAN.md|slug|file.html> [--view] [--file] [--port N] [--no-open] [--render]

A `.html` argument is viewed as-is (already rendered); a slug / PLAN.md is rendered first if stale.
Run from apps/api (slug resolution searches ./specs first, then the skill's own specs).
"""

from __future__ import annotations

import functools
import shutil
import subprocess
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from render_plan import render, resolve_input

# Chrome binaries to try, in order, before falling back to the default browser.
_CHROME_LINUX = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]
_CHROME_WIN = ["chrome"]


def ensure_html(plan_path: Path, force: bool) -> Path:
    """Return the PLAN.html path, (re)rendering it when missing, stale, or forced."""
    html_path = plan_path.parent / "PLAN.html"
    stale = not html_path.exists() or html_path.stat().st_mtime < plan_path.stat().st_mtime
    if force or stale:
        html_text, warnings, _ = render(plan_path)
        html_path.write_text(html_text, encoding="utf-8")
        for w in warnings:
            print(f"WARNING: {w}")
        print(f"Rendered {html_path}")
    return html_path


def resolve_html(arg: str, force_render: bool) -> Path:
    """Map a CLI argument to a PLAN.html path.

    An ``.html`` argument is an already-rendered file → viewed as-is (no render).
    Anything else is a slug or PLAN.md path → resolved, then rendered if missing/stale.
    """
    if arg.endswith(".html"):
        html_path = Path(arg)
        if not html_path.exists():
            raise SystemExit(f"HTML file not found: {arg}")
        return html_path
    return ensure_html(resolve_input(arg), force_render)


def open_in_chrome(url: str) -> None:
    """Best-effort browser launch: Chrome first, default browser fallback, never raises."""
    plat = sys.platform
    try:
        if plat == "darwin":
            subprocess.Popen(
                ["open", "-a", "Google Chrome", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Opened Chrome at {url}", flush=True)
            return
        candidates = _CHROME_WIN if plat.startswith("win") else _CHROME_LINUX
        for name in candidates:
            binary = shutil.which(name)
            if binary:
                subprocess.Popen(
                    [binary, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"Opened {name} at {url}", flush=True)
                return
    except Exception as e:  # browser launch is best-effort — never fail the view
        print(f"WARNING: Chrome launch failed ({e}); trying default browser.")
    if webbrowser.open(url):
        print(f"Opened default browser at {url}", flush=True)
    else:
        print(f"Could not launch a browser. Open manually: {url}", flush=True)


class _QuietHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler without the per-request stderr access log."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - match base signature, silence log
        pass


def serve(html_path: Path, port: int, do_open: bool) -> None:
    """Serve the plan dir over http://127.0.0.1 and (optionally) open Chrome. Blocks."""
    plan_dir = html_path.parent
    handler = functools.partial(_QuietHandler, directory=str(plan_dir))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    actual_port = httpd.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/{html_path.name}"
    # flush: serve_forever() blocks below, so buffered stdout would hide the URL
    print(f"Serving {plan_dir} at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if do_open:
        open_in_chrome(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


USAGE = "Usage: view_plan.py <PLAN.md|slug|file.html> [--view] [--file] [--port N] [--no-open] [--render]"


def main(argv: list[str]) -> None:
    args = argv[1:]
    use_file = False
    no_open = False
    force_render = False
    port = 0
    positionals: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--file":
            use_file = True
        elif a == "--no-open":
            no_open = True
        elif a == "--render":
            force_render = True
        elif a == "--view":
            pass  # no-op: viewing is implied; accepted for `visual-planner <arg> --view` passthrough
        elif a == "--port":
            i += 1
            if i >= len(args):
                raise SystemExit("--port requires a number")
            port = int(args[i])
        elif a.startswith("--"):
            raise SystemExit(f"Unknown flag: {a}\n{USAGE}")
        else:
            positionals.append(a)
        i += 1

    if not positionals:
        raise SystemExit(USAGE)

    html_path = resolve_html(positionals[0], force_render)

    if use_file:
        url = html_path.resolve().as_uri()
        print(f"File: {url}")
        if not no_open:
            open_in_chrome(url)
        return

    serve(html_path, port, do_open=not no_open)


if __name__ == "__main__":
    main(sys.argv)
