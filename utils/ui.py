"""
Terminal UI and Logging — DD-CMS-V3

Provides:
- Styled terminal output using Rich
- Simple log function (log_msg) used by all modules
- Optional run log file writing (logs/*.log)
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

console = Console()

_RUN_LOG_PATH  = None
_RUN_LOG_FH    = None
_IMPORTANT_EVENTS = []


def get_pkt_time():
    """Returns current Pakistan Standard Time (UTC+5)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)


def init_run_logger(mode=None):
    global _RUN_LOG_PATH, _RUN_LOG_FH
    try:
        os.makedirs("logs", exist_ok=True)
        ts     = get_pkt_time().strftime("%Y%m%d_%H%M%S")
        suffix = (mode or "run").lower()
        _RUN_LOG_PATH = os.path.join("logs", f"{suffix}_{ts}.log")
        _RUN_LOG_FH   = open(_RUN_LOG_PATH, "a", encoding="utf-8")
    except Exception:
        _RUN_LOG_PATH = None
        _RUN_LOG_FH   = None


def close_run_logger():
    global _RUN_LOG_FH
    try:
        if _RUN_LOG_FH:
            _RUN_LOG_FH.flush()
            _RUN_LOG_FH.close()
    except Exception:
        pass
    finally:
        _RUN_LOG_FH = None


def _append_important_event(ts, level, msg):
    if level in {"WARNING", "ERROR", "TIMEOUT", "SUCCESS"}:
        _IMPORTANT_EVENTS.append((ts, level, msg))


def print_important_events(max_items=12):
    if not _IMPORTANT_EVENTS:
        return
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("Time",    style="dim",   width=10)
    table.add_column("Level",   style="cyan",  width=10)
    table.add_column("Message", style="white")
    for ts, level, msg in _IMPORTANT_EVENTS[-max_items:]:
        table.add_row(ts, level, str(msg))
    console.print(Panel(table, title="IMPORTANT EVENTS", border_style="yellow", expand=False))


def get_progress_bar(progress, total, width=20):
    filled = int(width * progress / total) if total > 0 else 0
    return "█" * filled + "░" * (width - filled)


def log_progress(processed, total, nickname="", status=""):
    """Shows inline progress line (overwrites current line)."""
    ts       = get_pkt_time().strftime('%H:%M:%S')
    is_ci    = os.getenv('GITHUB_ACTIONS') == 'true'
    pct      = f"{int(processed / total * 100)}%" if total > 0 else "?%"
    progress_text = f"[{processed}/{total}] {pct}"

    if is_ci:
        console.print(f"{progress_text} {nickname} ({status})")
        return

    bar = get_progress_bar(processed, total)
    status_color = {
        "new": "green", "updated": "yellow", "error": "red",
        "scraping": "magenta", "skipped": "dim",
    }.get(status.lower(), "white")

    console.print(
        f"[dim]{ts}[/]  [bold yellow]{progress_text:<12}[/]  [cyan]{bar}[/]  "
        f"[bold]{nickname:<25}[/]  [{status_color}]({status})[/]",
        end="\r", overflow="ignore", highlight=False
    )


def log_msg(msg, level="INFO", progress=None, total=None):
    """Main logger — writes to terminal + optional log file."""
    ts    = get_pkt_time().strftime('%H:%M:%S')
    is_ci = os.getenv('GITHUB_ACTIONS') == 'true'

    style_map = {
        "INFO":     "bold cyan",
        "OK":       "bold green",
        "SUCCESS":  "bold green",
        "WARNING":  "bold yellow",
        "ERROR":    "bold red",
        "SCRAPING": "bold magenta",
        "LOGIN":    "bold blue",
        "TIMEOUT":  "dim yellow",
        "SKIP":     "dim",
    }
    icon_map = {
        "INFO": "💠", "OK": "✅", "SUCCESS": "🎉", "WARNING": "⚠️",
        "ERROR": "❌", "SCRAPING": "🔍", "LOGIN": "🔐", "TIMEOUT": "⏳",
        "SKIP": "⏭️",
    }

    style = style_map.get(level, "white")
    icon  = icon_map.get(level, "➡️")

    if is_ci:
        console.print(f"{icon} {msg}")
    else:
        console.print(f"[dim]{ts}[/] {icon} [{style}]{msg}[/]", highlight=False)

    try:
        if _RUN_LOG_FH:
            _RUN_LOG_FH.write(f"{ts} {level}: {msg}\n")
            _RUN_LOG_FH.flush()
    except Exception:
        pass

    _append_important_event(ts, level, msg)


def print_header(title, version):
    console.print()
    header_text = Text()
    header_text.append(f"\n{title}\n", style="bold cyan")
    header_text.append(f"Version: {version}", style="bold magenta")
    console.print(
        Panel(header_text, expand=False, border_style="bold magenta",
              box=box.DOUBLE, padding=(1, 4)),
        justify="center"
    )
    console.print()


def print_summary(stats, mode, duration):
    console.print()
    table = Table(
        title="SCRAPING SUMMARY",
        show_header=True, header_style="bold magenta",
        border_style="bold magenta", box=box.DOUBLE_EDGE
    )
    table.add_column("Metric",  style="bold cyan",   width=25)
    table.add_column("Value",   justify="right", style="bold yellow", width=15)
    table.add_column("Status",  justify="center", width=8)

    table.add_row("Mode",              mode.upper(),                  "🚀")
    table.add_row("Successful",        str(stats.get('success', 0)),  "✅")
    table.add_row("Failed",            str(stats.get('failed', 0)),   "❌" if stats.get('failed') else "")
    table.add_row("New Profiles",      str(stats.get('new', 0)),      "🆕" if stats.get('new') else "")
    table.add_row("Updated Profiles",  str(stats.get('updated', 0)),  "🔄" if stats.get('updated') else "")
    table.add_row("Unchanged",         str(stats.get('unchanged', 0)),"💤")
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
    table.add_row("Duration",          duration_str,                  "⏱️")

    console.print(table, justify="center")
    console.print()


def print_phase_start(phase_name):
    console.print()
    console.print(
        Panel(f"[bold cyan]STARTING {phase_name.upper()} PHASE[/]",
              border_style="bold magenta", expand=False, padding=(0, 4)),
        justify="center"
    )
    console.print()


def print_online_users_found(count):
    if count == 0:
        console.print("[yellow]⚠️  No online users found[/]")
    else:
        console.print(f"[green]✅  Found {count} online users[/]")


def print_mode_config(mode, max_profiles, batch_size):
    table = Table(title="Configuration", show_header=False,
                  border_style="bold cyan", box=box.ROUNDED, padding=(0, 2))
    table.add_column("Key",   style="bold cyan",   width=20)
    table.add_column("Value", style="bold yellow",  width=25)
    table.add_row("Mode",         mode.upper())
    table.add_row("Max Profiles", "Unlimited" if max_profiles == 0 else str(max_profiles))
    table.add_row("Batch Size",   str(batch_size))
    console.print(table, justify="center")
    console.print()
