"""Terminal UI helpers: colors, spinner, banner, tables."""

import sys
import time
import threading
import shutil
from typing import List


# ── ANSI colors ───────────────────────────────────────────────────────────────

def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = _supports_color()

def _c(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def red(t):    return _c("31", t)
def cyan(t):   return _c("36", t)
def bold(t):   return _c("1", t)
def dim(t):    return _c("2", t)


# ── Print helpers ─────────────────────────────────────────────────────────────

def print_banner():
    width = min(shutil.get_terminal_size().columns, 60)
    lines = [
        "╔══════════════════════════════════════════╗",
        "║        slurm-local  ·  SLURM on Docker  ║",
        "║  Local HPC cluster testing in minutes    ║",
        "╚══════════════════════════════════════════╝",
    ]
    for line in lines:
        print(cyan(line))
    print()


def print_success(msg: str):
    print(green(f"  ✔  {msg}"))

def print_error(msg: str):
    print(red(f"  ✘  {msg}"), file=sys.stderr)

def print_warning(msg: str):
    print(yellow(f"  ⚠  {msg}"))

def print_info(msg: str):
    print(f"     {msg}")

def print_step(msg: str):
    print(bold(f"\n  ▸  {msg}"))


# ── Table ─────────────────────────────────────────────────────────────────────

def print_table(headers: List[str], rows: List[List[str]]):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  " + "  ".join("─" * w for w in col_widths)

    print(bold(fmt.format(*headers)))
    print(dim(sep))
    for row in rows:
        cells = [str(c) for c in row]
        # Color the status column
        colored = []
        for i, cell in enumerate(cells):
            if headers[i].lower() == "status":
                if cell == "running":
                    cell = green(cell)
                elif cell in ("exited", "not found"):
                    cell = red(cell)
                else:
                    cell = yellow(cell)
            colored.append(cell)
        # Print without width enforcement for colored cells (ANSI codes add chars)
        raw_fmt = "  " + "  ".join(f"{{:<{w}}}" for w in col_widths)
        # Rebuild with raw values for width calc, then swap in colored
        raw_row = raw_fmt.format(*[str(c) for c in row])
        # Replace each raw cell with colored cell in order
        line = raw_row
        for raw, col in zip([str(c) for c in row], colored):
            line = line.replace(raw, col, 1)
        print(line)


# ── Spinner ───────────────────────────────────────────────────────────────────

class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r  {cyan(frame)}  {self.message} ")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def start(self):
        if USE_COLOR:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            print(f"     {self.message}")
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if USE_COLOR:
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.stop()
