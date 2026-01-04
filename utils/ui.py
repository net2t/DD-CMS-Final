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
def get_progress_text(processed, total):
    """Returns clear progress text with percentage."""
    if total > 0:
        percentage = (processed / total) * 100
        return f"[{processed}/{total}] {percentage:.0f}%"
    else:
        return f"[{processed}/?]"


def get_spinning_emoji():
    """Returns a random spinning emoji for loading states."""
    spinners = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "⭐", "✨", "💫", "🌟", "⚡", "🔥", "💎", "🚀", "🌈", "🎆", "🎇", "🎊", "🎉", "🎈", "🎀", "🎁", "🎯", "🎪", "🎭", "🎨", "🎬", "🎤", "🎧", "🎮", "🎰", "🎲", "🎳", "🎯", "🎪", "🎭", "🎨", "🎬", "🎤", "🎧", "🎮", "🎰", "🎲", "🎳"]
    return random.choice(spinners)


def get_progress_bar(progress, total, width=20):
    """Returns a clean formatted progress bar."""
    filled = int(width * progress / total) if total > 0 else 0
    empty = width - filled
    
    # Clean progress bar with standard characters
    if progress == total:
        return "█" * width
    else:
        return "█" * filled + "░" * empty

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
    
    # Format progress counter with clear text and percentage
    progress_counter = get_progress_text(processed, total)
    
    # Progress bar with emojis
    progress_bar = get_progress_bar(processed, total)
    
    # Enhanced status indicator with rich emojis
    status_icon = {
        "new": "🆕",
        "updated": "🔄",
        "skipped": "⏩",
        "error": "❌",
        "scraping": "🔍",
        "processing": "⚙️",
        "loading": "🔄",
        "complete": "🎉",
        "success": "✨",
        "failed": "💥"
    }.get(status.lower(), "➡️")
    
    # For CI, keep it simple
    if is_ci:
        message = f"{progress_counter} {processed}/{total} - {nickname} ({status})"
        console.print(message)
        return
    
    # Build enhanced progress line with clear numbering
    parts = [
        f"[dim]{ts.ljust(8)}[/] ",  # Clean timestamp with space
        f"[bold yellow]{progress_counter.ljust(12)}[/] ",  # Progress counter with percentage
        f"[cyan]{progress_bar}[/] ",  # Clean progress bar
        f"[bold]{nickname.ljust(25)}[/]" if nickname else ""  # Nickname
    ]
    
    # Add simple status indicator
    if status:
        status_text = status.lower()
        if status_text == "scraping":
            parts.append(f" [dim]({status}...)[/]")
        elif status_text == "new":
            parts.append(f" [green]({status})[/]")
        elif status_text == "updated":
            parts.append(f" [yellow]({status})[/]")
        elif status_text == "error":
            parts.append(f" [red]({status})[/]")
        else:
            parts.append(f" [dim]({status})[/]")
    
    # Print with clean formatting
    console.print("".join(parts), end="\r", overflow="ignore", highlight=False)

def log_msg(msg, level="INFO", progress=None, total=None):
    """
    Enhanced styled logger with emojis, colors, and progress tracking.
    """
    ts = get_pkt_time().strftime('%H:%M:%S')
    is_ci = os.getenv('GITHUB_ACTIONS') == 'true'
    
    # Enhanced style and icon mappings with rich colors
    style_map = {
        "INFO": "bold cyan", 
        "OK": "bold green", 
        "SUCCESS": "bold green on black",
        "WARNING": "bold yellow on black", 
        "ERROR": "bold red on black", 
        "SCRAPING": "bold magenta",
        "LOGIN": "bold blue", 
        "TIMEOUT": "dim yellow", 
        "SKIP": "dim",
        "PROGRESS": "bold cyan",
        "COMPLETE": "bold green on black",
        "START": "bold yellow on blue",
        "STOP": "bold red on white",
        "PAUSE": "bold yellow on black",
        "RESUME": "bold green on black"
    }
    
    icon_map = {
        "INFO": "💠", 
        "OK": "✨", 
        "SUCCESS": "🎉", 
        "WARNING": "⚠️",
        "ERROR": "❌", 
        "SCRAPING": "🔍", 
        "LOGIN": "🔐", 
        "TIMEOUT": "⏳",
        "SKIP": "⏭️",
        "PROGRESS": "🔄",
        "COMPLETE": "🎊",
        "START": "🚀",
        "STOP": "🛑",
        "PAUSE": "⏸️",
        "RESUME": "▶️"
    }
    
    # Get style and icon, with fallbacks
    style = style_map.get(level, "white")
    icon = icon_map.get(level, "➡️")
    
    # For CI, keep it simple
    if is_ci:
        console.print(f"{icon} {msg}")
        return
    
    # Build clean message parts
    parts = [
        f"[dim]{ts.ljust(8)}[/]",  # Clean timestamp
        f" {icon} ",  # Simple icon
        f"[{style}]{msg}[/]"  # Clean message
    ]
    
    # Add progress bar for progress messages
    if level == "PROGRESS" and total and total > 0:
        progress_percent = min(100, int((progress / total) * 100))
        bar_width = 20
        filled = int(bar_width * progress / total)
        bar = get_progress_bar(progress, total)
        parts.append(f" [cyan]{bar} {progress_percent:3}%[/]")
    
    # Print with clean formatting
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
    Displays a prominent, animated header with rich emojis and colors.

    Args:
        title (str): The main title to display.
        version (str): The script version.
    """
    console.print()
    
    # Animated rainbow border
    border_styles = ["bold red", "bold yellow", "bold green", "bold cyan", "bold blue", "bold magenta"]
    for i in range(3):
        console.print("=" * 80, style=border_styles[i % len(border_styles)])
        time.sleep(0.1)
    
    # Create rich header text with animations
    header_text = Text()
    header_text.append("🚀✨🚀", style="bold yellow")
    header_text.append(f"\n{title}", style="bold cyan on black")
    header_text.append("\n🚀✨🚀", style="bold yellow")
    header_text.append("\n")
    header_text.append(f"Version: {version}", style="bold magenta")
    header_text.append("\n")
    header_text.append("⚡ Powered by Selenium + Google Sheets ⚡", style="bold green")
    header_text.append("\n")
    header_text.append("🌟 Enhanced Terminal UI with Rich Emojis 🌟", style="bold yellow")
    
    # Create animated panel
    console.print(
        Panel(
            header_text,
            expand=False,
            border_style="bold magenta",
            box=box.DOUBLE,
            padding=(2, 6)
        ),
        justify="center"
    )
    
    # Animated closing border
    for i in range(3):
        console.print("=" * 80, style=border_styles[(i + 3) % len(border_styles)])
        time.sleep(0.1)
    
    console.print()
    # Add sparkle effect
    console.print("✨🌟💫⭐🎆🎇🎊🎉✨", justify="center")
    console.print()


def print_summary(stats, mode, duration):
    """
    Displays a comprehensive summary table with rich visual effects.

    Args:
        stats (dict): Run statistics.
        mode (str): The scraping mode ('online' or 'target').
        duration (float): Total duration in seconds.
    """
    console.print()
    
    # Animated celebration border
    celebration_emojis = ["🎉", "🎊", "✨", "🌟", "💫", "⭐", "🎆", "🎇"]
    for _ in range(3):
        console.print("".join(random.choices(celebration_emojis, k=40)), style="bold magenta")
        time.sleep(0.1)
    
    console.print()
    
    # Create enhanced summary table
    table = Table(
        title="🎊 MISSION COMPLETE - SCRAPING SUMMARY 🎊",
        show_header=True,
        header_style="bold magenta on black",
        border_style="bold magenta",
        box=box.DOUBLE_EDGE
    )
    
    table.add_column("📊 Metric", style="bold cyan", width=25)
    table.add_column("💎 Value", justify="right", style="bold yellow on black", width=15)
    table.add_column("⭐ Status", justify="center", width=10)
    
    # Mode with special styling
    table.add_row("🎯 Mode", mode.upper(), "🚀")
    table.add_row("", "", "")  # Spacer
    
    # Results with enhanced icons
    success_count = stats.get('success', 0)
    success_icon = "🎉" if success_count > 0 else "⚠️"
    table.add_row("✅ Successful", str(success_count), success_icon)
    
    failed_count = stats.get('failed', 0)
    failed_icon = "💥" if failed_count > 0 else "✅"
    table.add_row("❌ Failed", str(failed_count), failed_icon)
    
    table.add_row("", "", "")  # Spacer
    
    # Profile breakdown with rich emojis
    new_count = stats.get('new', 0)
    table.add_row("🆕 New Profiles", str(new_count), "✨" if new_count > 0 else "")
    
    updated_count = stats.get('updated', 0)
    table.add_row("🔄 Updated Profiles", str(updated_count), "🔄" if updated_count > 0 else "")
    
    unchanged_count = stats.get('unchanged', 0)
    table.add_row("💤 Unchanged Profiles", str(unchanged_count), "😴" if unchanged_count > 0 else "")

    phase2_ready = stats.get('phase2_ready')
    phase2_not_eligible = stats.get('phase2_not_eligible')
    if phase2_ready is not None or phase2_not_eligible is not None:
        table.add_row("", "", "")  # Spacer
        table.add_row("🚩 Phase 2 READY", str(phase2_ready or 0), "🎯" if (phase2_ready or 0) > 0 else "")
        table.add_row("⛔ Phase 2 NOT ELIGIBLE", str(phase2_not_eligible or 0), "🚫")
    
    # Online mode specific
    if mode == 'online':
        table.add_row("", "", "")  # Spacer
        logged_count = stats.get('logged', 0)
        table.add_row("📝 Logged Online Users", str(logged_count), "📡" if logged_count > 0 else "")
    
    # Duration with performance indicator
    table.add_row("", "", "")  # Spacer
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
    duration_icon = "⚡" if duration < 300 else "🐌" if duration < 600 else "🦕"
    table.add_row("⏱️ Duration", duration_str, duration_icon)
    
    console.print(table, justify="center")
    console.print()
    
    # Add performance rating
    total_profiles = success_count + failed_count
    if total_profiles > 0:
        success_rate = (success_count / total_profiles) * 100
        if success_rate >= 95:
            rating = "🏆 EXCELLENT PERFORMANCE! 🏆"
            rating_style = "bold green on black"
        elif success_rate >= 85:
            rating = "⭐ GREAT JOB! ⭐"
            rating_style = "bold yellow on black"
        elif success_rate >= 70:
            rating = "👍 GOOD WORK! 👍"
            rating_style = "bold cyan on black"
        else:
            rating = "💪 ROOM FOR IMPROVEMENT 💪"
            rating_style = "bold magenta on black"
        
        console.print(rating, style=rating_style, justify="center")
        console.print()
    
    # Animated closing border
    for _ in range(3):
        console.print("".join(random.choices(celebration_emojis, k=40)), style="bold magenta")
        time.sleep(0.1)
    
    console.print()
    console.print("🎊✨🌟💫⭐ MISSION ACCOMPLISHED! ⭐💫🌟✨🎊", style="bold magenta", justify="center")
    console.print()


def print_phase_start(phase_name):
    """
    Announces the start of a scraping phase with dramatic effects.

    Args:
        phase_name (str): Name of the phase (e.g., 'PROFILE', 'POSTS').
    """
    console.print()
    
    # Animated countdown effect
    for i in range(3, 0, -1):
        console.print(f"[bold red on black]GETTING READY... {i}[/]", justify="center")
        time.sleep(0.3)
    
    # Create dramatic phase announcement
    phase_text = Text()
    phase_text.append("🚀 ", style="bold yellow")
    phase_text.append(f"STARTING {phase_name.upper()} PHASE", style="bold cyan on black")
    phase_text.append(" 🚀", style="bold yellow")
    
    # Add decorative elements
    console.print("✨" * 30, style="bold yellow", justify="center")
    console.print()
    console.print(
        Panel(
            phase_text,
            border_style="bold magenta",
            expand=False,
            padding=(1, 4)
        ),
        justify="center"
    )
    console.print()
    console.print("✨" * 30, style="bold yellow", justify="center")
    console.print()
    
    # Add motivational message
    messages = [
        "🔥 Let's get this done! 🔥",
        "⚡ Full speed ahead! ⚡",
        "🌟 Excellence in progress! 🌟",
        "💪 Power mode activated! 💪"
    ]
    console.print(random.choice(messages), style="bold green", justify="center")
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
    Displays the configuration for the current run with enhanced styling.

    Args:
        mode (str): The scraping mode.
        max_profiles (int): Maximum profiles to scrape (0 = unlimited).
        batch_size (int): Batch size for processing.
    """
    config_table = Table(
        title="⚙️ CONFIGURATION SETTINGS ⚙️",
        show_header=False,
        border_style="bold cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    config_table.add_column("🔧 Key", style="bold cyan", width=20)
    config_table.add_column("💎 Value", style="bold yellow", width=25)
    
    config_table.add_row("🎯 Mode", mode.upper())
    config_table.add_row("🔢 Max Profiles", "Unlimited" if max_profiles == 0 else str(max_profiles))
    config_table.add_row("📦 Batch Size", str(batch_size))
    
    console.print(config_table, justify="center")
    console.print()


def create_loading_animation(message="Loading", duration=3):
    """
    Creates an animated loading effect with spinning emojis.
    
    Args:
        message (str): The message to display during loading.
        duration (float): Duration in seconds for the animation.
    """
    spinners = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "⭐", "✨", "💫", "🌟"]
    start_time = time.time()
    
    with console.status(f"[bold cyan]{message}...", spinner="dots") as status:
        while time.time() - start_time < duration:
            current_spinner = random.choice(spinners)
            status.update(f"[bold cyan]{message}... {current_spinner}[/]")
            time.sleep(0.1)


def print_success_banner(message):
    """
    Prints a success banner with celebration effects.
    
    Args:
        message (str): The success message to display.
    """
    console.print()
    console.print("🎉" * 20, style="bold green", justify="center")
    console.print()
    console.print(f"[bold green on black]✨ {message} ✨[/]", justify="center")
    console.print()
    console.print("🎉" * 20, style="bold green", justify="center")
    console.print()


def print_error_banner(message):
    """
    Prints an error banner with warning effects.
    
    Args:
        message (str): The error message to display.
    """
    console.print()
    console.print("⚠️" * 20, style="bold red", justify="center")
    console.print()
    console.print(f"[bold red on white]❌ {message} ❌[/]", justify="center")
    console.print()
    console.print("⚠️" * 20, style="bold red", justify="center")
    console.print()


def create_rainbow_text(text):
    """
    Creates rainbow-colored text effect.
    
    Args:
        text (str): The text to colorize.
    
    Returns:
        str: The rainbow-colored text.
    """
    colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
    rainbow_text = Text()
    
    for i, char in enumerate(text):
        color = colors[i % len(colors)]
        rainbow_text.append(char, style=f"bold {color}")
    
    return rainbow_text
