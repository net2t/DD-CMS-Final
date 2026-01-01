"""
UI Module for the DamaDam Scraper.

Enhanced with emojis, colors, animations, and beautiful terminal output.
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich import box

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
def log_msg(msg, level="INFO"):
    """
    Enhanced styled logger with emojis and colors.

    Args:
        msg (str): The message to log.
        level (str): The log level (INFO, OK, WARNING, ERROR, SCRAPING, LOGIN, TIMEOUT).
    """
    ts = get_pkt_time().strftime('%H:%M:%S')
    
    style_map = {
        "INFO": "cyan",
        "OK": "green",
        "SUCCESS": "bold green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "SCRAPING": "magenta",
        "LOGIN": "blue",
        "TIMEOUT": "dim yellow",
        "SKIP": "dim"
    }
    
    icon_map = {
        "INFO": "ℹ️",
        "OK": "✅",
        "SUCCESS": "🎉",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "SCRAPING": "🔍",
        "LOGIN": "🔑",
        "TIMEOUT": "⏳",
        "SKIP": "⏭️"
    }
    
    style = style_map.get(level, "white")
    icon = icon_map.get(level, "➡️")
    
    console.print(f"[dim]{ts}[/dim] {icon} [{style}]{msg}[/{style}]")

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
