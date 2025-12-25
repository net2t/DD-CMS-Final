"""
UI Module for the DamaDam Scraper.

This module centralizes all terminal output for the application, using the 'rich'
library to create a modern, readable, and visually appealing command-line
interface. It provides standardized functions for logging, displaying headers,
and printing summary tables.
"""

import sys
from datetime import datetime, timedelta, timezone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Initialize a global Rich Console instance for consistent output.
console = Console()

def get_pkt_time():
    """Get current Pakistan time"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log_msg(msg, level="INFO"):
    """
    A styled logger that replaces the standard print function.

    It adds a timestamp and a color-coded level (e.g., INFO, OK, ERROR) to each
    message, making the log output easier to scan and debug.

    Args:
        msg (str): The message to log.
        level (str): The log level, which determines the color and label.
    """
    ts = get_pkt_time().strftime('%H:%M:%S')
    is_windows = sys.platform.startswith('win')

    style_map = {
        "INFO": "cyan",
        "OK": "green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "SCRAPING": "magenta",
        "LOGIN": "blue",
        "TIMEOUT": "dim yellow"
    }
    
    icon_map = {
        "INFO": "ℹ️", "OK": "✅", "WARNING": "⚠️", "ERROR": "❌",
        "SCRAPING": "🔍", "LOGIN": "🔑", "TIMEOUT": "⏳"
    }
    
    ascii_map = {
        "INFO": "[INFO]", "OK": "[OK]", "WARNING": "[WARN]", "ERROR": "[ERR]",
        "SCRAPING": "[SCRAPE]", "LOGIN": "[LOGIN]", "TIMEOUT": "[TIMEOUT]"
    }

    style = style_map.get(level, "white")
    
    if is_windows:
        # On Windows, use ASCII text instead of icons to avoid UnicodeEncodeError
        icon_text = ascii_map.get(level, "[----]")
        console.print(f"[{ts}]", Text(icon_text, style=style), f" {msg}")
    else:
        icon = icon_map.get(level, "➡️")
        console.print(f"[{ts}] {icon} ", Text(f"[{level}]", style=style), f" {msg}")

def print_header(title, version):
    """
    Displays a prominent, styled header at the start of the script.

    It uses a Rich Panel to draw a box around the title and version, clearly
    announcing the start of the application.

    Args:
        title (str): The main title to display in the header.
        version (str): The script version to display.
    """
    header_text = f"[bold cyan]{title}[/bold cyan]\n[dim]{version}[/dim]"
    console.print(Panel(Text(header_text, justify="center"), expand=False, border_style="blue"))

def print_summary(stats, mode, duration):
    """
    Displays a summary of the completed scraping run in a clean, formatted table.

    It uses a Rich Table to present the final statistics, such as the number of
    successful, failed, and new profiles, along with the total duration.

    Args:
        stats (dict): A dictionary of statistics from the run.
        mode (str): The scraping mode that was run ('online' or 'target').
        duration (float): The total duration of the run in seconds.
    """
    table = Table(title="Scraping Completed", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim", width=20)
    table.add_column("Value", justify="right")

    table.add_row("Mode", mode.upper())
    table.add_row("Success", str(stats.get('success', 0)))
    table.add_row("Failed", str(stats.get('failed', 0)))
    table.add_row("New", str(stats.get('new', 0)))
    table.add_row("Updated", str(stats.get('updated', 0)))
    table.add_row("Unchanged", str(stats.get('unchanged', 0)))
    if mode == 'online':
        table.add_row("Logged", str(stats.get('logged', 0)))
    table.add_row("Duration", f"{duration:.0f}s")

    console.print(table)
