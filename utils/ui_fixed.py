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
    
    # Build progress line
    parts = [
        f"[bold white on black]{ts.ljust(9)}[/] ",  # Bold timestamp with background
        f"{progress_emoji} ",
        f"[bold cyan][{progress_counter}][/] ",  # Extra space after progress counter
        f"{progress_bar} ",
        f"[bold magenta]{nickname.ljust(25)}[/]" if nickname else ""  # Increased width for better alignment
    ]
    
    # Add enhanced status with animations
    if status:
        if status.lower() == "scraping":
            parts.append(f" ({status_icon} [{status_style}]{status}...[/]) 🔄")
        elif status.lower() == "new":
            parts.append(f" ({status_icon} [{status_style}]{status}[/]) ✨")
        elif status.lower() == "updated":
            parts.append(f" ({status_icon} [{status_style}]{status}[/]) 🔄")
        elif status.lower() == "error":
            parts.append(f" ({status_icon} [{status_style}]{status}[/]) 💥")
        else:
            parts.append(f" ({status_icon} [{status_style}]{status}[/])")
    
    # Add decorative elements for special states
    if processed == total:
        parts.append(" 🎉✨🎉")
    elif processed > total * 0.9:
        parts.append(" 🔥⚡")
    
    # Print with enhanced formatting
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
    
    # Build message parts with enhanced formatting
    parts = [
        f"[bold white on black]{ts.ljust(9)}[/]",  # Bold timestamp with background
        f" {icon} "  # Icon with consistent spacing
    ]
    
    # Add animated progress prefix if needed
    if progress is not None and total is not None:
        progress_emoji = get_spinning_emoji() if progress < total else "🎉"
        parts.append(f"[bold cyan][{progress}/{total}][/] {progress_emoji} ")
    
    # Add the main message with enhanced styling
    if level == "SUCCESS":
        parts.append(f"[{style}] {msg} [/]")
    elif level == "ERROR":
        parts.append(f"[{style}] ⚠️ {msg} ⚠️ [/]")
    elif level == "WARNING":
        parts.append(f"[{style}] 🔸 {msg} 🔸 [/]")
    else:
        parts.append(f"[{style}] {msg}[/]")
    
    # Add animated progress bar for progress messages
    if level == "PROGRESS" and total and total > 0:
        progress_percent = min(100, int((progress / total) * 100))
        bar_width = 20
        filled = int(bar_width * progress / total)
        bar = get_progress_bar(progress, total)
        parts.append(f" [bold cyan]{bar} {progress_percent:3}%[/]")
    
    # Add decorative elements for special messages
    if level in ["SUCCESS", "COMPLETE"]:
        parts.append(" ✨🎉✨")
    elif level == "ERROR":
        parts.append(" ❌💔❌")
    
    # Print with enhanced formatting
    console.print("".join(parts), end="\n", highlight=False, overflow="ignore")
