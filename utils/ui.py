"""
UI Module for DamaDam Scraper

Handles all terminal output using the 'rich' library for a modern look.
"""

from datetime import datetime, timedelta, timezone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

def get_pkt_time():
    """Get current Pakistan time"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log_msg(msg, level="INFO"):
    """Logger using rich for styled output."""
    ts = get_pkt_time().strftime('%H:%M:%S')
    style_map = {
        "INFO": "cyan",
        "OK": "green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "SCRAPING": "magenta",
        "LOGIN": "blue",
        "TIMEOUT": "dim yellow"
    }
    style = style_map.get(level, "white")
    console.print(f"[{ts}] ", Text(f"[{level}]", style=style), f" {msg}")

def print_header(title, version):
    """Prints a styled header panel."""
    header_text = f"[bold cyan]{title}[/bold cyan]\n[dim]{version}[/dim]"
    console.print(Panel(Text(header_text, justify="center"), expand=False, border_style="blue"))

def print_summary(stats, mode, duration):
    """Prints a summary of the scraping operation in a table."""
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
