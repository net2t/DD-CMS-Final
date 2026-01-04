"""
Terminal UI + Logging (Phase 1)

This module provides:
- Pretty terminal output (header, summary, progress)
- A simple log function (log_msg) used by all modules
- Optional run log file writing (logs/*.log)
- A small "important events" list shown at the end
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, ProgressColumn
from rich.live import Live
from rich import box
from itertools import cycle
import random

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# Initialize a global Rich Console instance
console = Console()

_RUN_LOG_PATH = None
_RUN_LOG_FH = None
_IMPORTANT_EVENTS = []


def get_pkt_time():
    """Get current Pakistan time (UTC+5)"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)


def init_run_logger(mode=None):
    global _RUN_LOG_PATH, _RUN_LOG_FH
    try:
        os.makedirs("logs", exist_ok=True)
        ts = get_pkt_time().strftime("%Y%m%d_%H%M%S")
        suffix = (mode or "run").lower()
        _RUN_LOG_PATH = os.path.join("logs", f"{suffix}_{ts}.log")
        _RUN_LOG_FH = open(_RUN_LOG_PATH, "a", encoding="utf-8")
    except Exception:
        _RUN_LOG_PATH = None
        _RUN_LOG_FH = None


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
    if level in {"WARNING", "ERROR", "TIMEOUT"}:
        _IMPORTANT_EVENTS.append((ts, level, msg))
        return
    if level in {"SUCCESS"}:
        _IMPORTANT_EVENTS.append((ts, level, msg))


def print_important_events(max_items=12):
    if not _IMPORTANT_EVENTS:
        return

    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("Time", style="dim", width=10)
    table.add_column("Level", style="cyan", width=10)
    table.add_column("Message", style="white")

    for ts, level, msg in _IMPORTANT_EVENTS[-max_items:]:
        table.add_row(ts, level, str(msg))

    console.print(
        Panel(
            table,
            title="IMPORTANT EVENTS",
            border_style="yellow",
            expand=False,
        )
    )
def get_numeric_emoji(number, total=None):
    """Converts a number into a string of number emojis with optional total."""
    s = str(number)
    emojis = {
        '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
        '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣',
        '/': '➗', '.': '🔘', ',': '🔸'
    }
    
    result = "".join(emojis.get(char, char) for char in s)
    if total is not None:
        total_str = str(total)
        total_emoji = "".join(emojis.get(char, char) for char in total_str)
        result = f"{result} / {total_emoji}"
    return result


def get_spinning_emoji():
    """Returns a random spinning emoji for loading states."""
    spinners = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    return random.choice(spinners)


def get_progress_bar(progress, total, width=20):
    """Returns a formatted progress bar with emojis."""
    filled = int(width * progress / total) if total > 0 else 0
    empty = width - filled
    
    # Use different emojis based on completion percentage
    if progress == total:
        return "✅" + "★" * (width - 1)
    elif progress / total > 0.9:
        return "★" * (filled - 1) + "✨" + "☆" * empty
    elif progress / total > 0.5:
        return "★" * filled + "☆" * empty
    else:
        return "⬜" * filled + "⬛" * empty

def log_progress(processed, total, nickname="", status=""):
    """
    Displays a rich progress indicator with emojis and a progress bar.
    """
    ts = get_pkt_time().strftime('%H:%M:%S')
    is_ci = os.getenv('GITHUB_ACTIONS') == 'true'
    
    # Status styling
    status_style = {
        "new": "bold green",
        "updated": "bold yellow",
        "skipped": "dim",
        "error": "bold red"
    }.get(status.lower(), "dim")
    
    # Progress emoji based on percentage
    progress_emoji = get_spinning_emoji() if processed < total else "✅"
    
    # Format progress counter with emojis
    progress_counter = f"{get_numeric_emoji(processed, total)}"
    
    # Progress bar with emojis
    progress_bar = get_progress_bar(processed, total)
    
    # Status indicator with emoji
    status_icon = {
        "new": "🆕",
        "updated": "🔄",
        "skipped": "⏩",
        "error": "❌"
    }.get(status.lower(), "➡️")
    
    # For CI, keep it simple
    if is_ci:
        message = f"{progress_counter} {processed}/{total} - {nickname} ({status})"
        console.print(message)
        return
    
    # Build the progress line
    parts = [
        f"[dim]{ts.ljust(9)}[/] ",  # Fixed width timestamp
        f"{progress_emoji} ",
        f"[bold cyan][{progress_counter}][/] ",
        f"{progress_bar} ",
        f"[bold magenta]{nickname.ljust(20)}[/]" if nickname else ""
    ]
    
    # Add status if provided
    if status:
        parts.append(f" ({status_icon} [{status_style}]{status}[/])")
    
    # Print with carriage return to update the line
    console.print("".join(parts), end="\r", overflow="ignore", highlight=False)

def log_msg(msg, level="INFO", progress=None, total=None):
    """
    Enhanced styled logger with emojis, colors, and progress tracking.
    """
    ts = get_pkt_time().strftime('%H:%M:%S')
    is_ci = os.getenv('GITHUB_ACTIONS') == 'true'
    
    # Style and icon mappings
    style_map = {
        "INFO": "cyan", 
        "OK": "bold green", 
        "SUCCESS": "bold green",
        "WARNING": "bold yellow", 
        "ERROR": "bold red", 
        "SCRAPING": "magenta",
        "LOGIN": "blue", 
        "TIMEOUT": "dim yellow", 
        "SKIP": "dim",
        "PROGRESS": "cyan",
        "COMPLETE": "bold green"
    }
    
    icon_map = {
        "INFO": "ℹ️", 
        "OK": "✅", 
        "SUCCESS": "✨", 
        "WARNING": "⚠️",
        "ERROR": "❌", 
        "SCRAPING": "🔍", 
        "LOGIN": "🔑", 
        "TIMEOUT": "⏳",
        "SKIP": "⏭️",
        "PROGRESS": "🔄",
        "COMPLETE": "✅"
    }
    
    # Get style and icon, with fallbacks
    style = style_map.get(level, "white")
    icon = icon_map.get(level, "➡️")
    
    # For CI, keep it simple
    if is_ci:
        console.print(f"{icon} {msg}")
        return
    
    # Build the message parts
    parts = [
        f"[dim]{ts.ljust(9)}[/]",  # Fixed width timestamp
        f" {icon} "  # Icon with consistent spacing
    ]
    
    # Add progress prefix if needed
    if progress is not None and total is not None:
        progress_emoji = "🔄" if progress < total else "✅"
        parts.append(f"[{progress}/{total}] {progress_emoji} ")
    
    # Add the main message
    parts.append(f"[{style}]{msg}[/]")
    
    # Add progress bar for progress messages
    if level == "PROGRESS" and total and total > 0:
        progress_percent = min(100, int((progress / total) * 100))
        bar_width = 20
        filled = int(bar_width * progress / total)
        bar = '█' * filled + '░' * (bar_width - filled)
        parts.append(f" [cyan]{bar} {progress_percent:3}%[/]")
    
    # Print with left alignment and no extra newlines
    console.print("".join(parts), end="\n", highlight=False, overflow="ignore")

    try:
        if _RUN_LOG_FH:
            _RUN_LOG_FH.write(f"{ts} {level}: {msg}\n")
            _RUN_LOG_FH.flush()
    except Exception:
        pass

    try:
        _append_important_event(ts, level, msg)
    except Exception:
        pass


def print_header(title, version):
    """
    Displays a prominent, animated header at the start of the script.

    Args:
        title (str): The main title to display.
        version (str): The script version.
    """
    console.print()
    
    # Animated border
    for _ in range(3):
        console.print("=" * 80, style="bold cyan")
        time.sleep(0.1)
    
    header_text = Text()
    header_text.append("🚀 ", style="bold yellow")
    header_text.append(title, style="bold cyan")
    header_text.append(" 🚀", style="bold yellow")
    header_text.append("\n")
    header_text.append(f"Version: {version}", style="dim italic")
    header_text.append("\n")
    header_text.append("Powered by Selenium + Google Sheets", style="dim")
    
    console.print(
        Panel(
            header_text,
            expand=False,
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 4)
        ),
        justify="center"
    )
    
    console.print("=" * 80, style="bold cyan")
    console.print()


def print_summary(stats, mode, duration):
    """
    Displays a comprehensive summary table at the end of the run.

    Args:
        stats (dict): Run statistics.
        mode (str): The scraping mode ('online' or 'target').
        duration (float): Total duration in seconds.
    """
    console.print()
    console.print("=" * 80, style="bold green")
    console.print()
    
    # Create summary table
    table = Table(
        title="📊 Scraping Run Summary",
        show_header=True,
        header_style="bold magenta",
        border_style="green",
        box=box.DOUBLE_EDGE
    )
    
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Value", justify="right", style="bold yellow", width=15)
    table.add_column("Status", justify="center", width=10)
    
    # Mode
    table.add_row("🎯 Mode", mode.upper(), "")
    table.add_row("", "", "")  # Spacer
    
    # Results
    success_icon = "✅" if stats.get('success', 0) > 0 else "⚠️"
    table.add_row("✅ Successful", str(stats.get('success', 0)), success_icon)
    
    failed_icon = "❌" if stats.get('failed', 0) > 0 else "✅"
    table.add_row("❌ Failed", str(stats.get('failed', 0)), failed_icon)
    
    table.add_row("", "", "")  # Spacer
    
    # Profile breakdown
    table.add_row("🆕 New Profiles", str(stats.get('new', 0)), "")
    table.add_row("🔄 Updated Profiles", str(stats.get('updated', 0)), "")
    table.add_row("💤 Unchanged Profiles", str(stats.get('unchanged', 0)), "")

    phase2_ready = stats.get('phase2_ready')
    phase2_not_eligible = stats.get('phase2_not_eligible')
    if phase2_ready is not None or phase2_not_eligible is not None:
        table.add_row("", "", "")  # Spacer
        table.add_row("🚩 Phase 2 READY", str(phase2_ready or 0), "")
        table.add_row("⛔ Phase 2 NOT ELIGIBLE", str(phase2_not_eligible or 0), "")
    
    # Online mode specific
    if mode == 'online':
        table.add_row("", "", "")  # Spacer
        table.add_row("📝 Logged Online Users", str(stats.get('logged', 0)), "")
    
    # Duration
    table.add_row("", "", "")  # Spacer
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
    duration_icon = "⚡" if duration < 300 else "🐌"
    table.add_row("⏱️ Duration", duration_str, duration_icon)
    
    console.print(table, justify="center")
    console.print()
    console.print("=" * 80, style="bold green")
    console.print()


def print_phase_start(phase_name):
    """
    Announces the start of a scraping phase.

    Args:
        phase_name (str): Name of the phase (e.g., 'PROFILE', 'POSTS').
    """
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Starting {phase_name} Phase[/bold cyan]",
            border_style="yellow",
            expand=False
        )
    )
    console.print()


def print_online_users_found(count):
    """
    Displays a summary of found online users.

    Args:
        count (int): Number of online users found.
    """
    if count == 0:
        console.print("⚠️ [yellow]No online users found[/yellow]")
    else:
        console.print(f"✅ [green]Found {count} online users[/green]")


def create_progress_bar():
    """
    Creates a reusable progress bar for batch operations.

    Returns:
        Progress: A rich Progress instance.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="bold green"),
        TaskProgressColumn(),
        console=console
    )


def print_mode_config(mode, max_profiles, batch_size):
    """
    Displays the configuration for the current run.

    Args:
        mode (str): The scraping mode.
        max_profiles (int): Maximum profiles to scrape (0 = unlimited).
        batch_size (int): Batch size for processing.
    """
    config_table = Table(show_header=False, border_style="dim", box=None)
    config_table.add_column("Key", style="cyan")
    config_table.add_column("Value", style="yellow")
    
    config_table.add_row("🎯 Mode", mode.upper())
    config_table.add_row("🔢 Max Profiles", "Unlimited" if max_profiles == 0 else str(max_profiles))
    config_table.add_row("📦 Batch Size", str(batch_size))
    
    console.print(config_table)
    console.print()
