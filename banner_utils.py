"""
Banner utilities for consistent output formatting
"""

from datetime import datetime
from typing import Optional, Dict, Any


def print_banner(
    title: str,
    content: str,
    emoji: str = "📝",
    metadata: Optional[Dict[str, Any]] = None,
    color: Optional[str] = None
) -> None:
    """
    Print a consistent banner for important events.
    
    Args:
        title: Banner title (e.g., "Complete Thought", "Saved to Knowledge Base")
        content: Main content to display
        emoji: Emoji to use in the banner
        metadata: Optional metadata to display
        color: Optional ANSI color code (not implemented yet)
    """
    # Clear any status line
    print("\r" + " " * 80 + "\r", end='', flush=True)
    
    # Print banner
    print(f"\n{emoji} {title}: {content}")
    
    # Print metadata if provided
    if metadata:
        print("  ├─ " + " | ".join([f"{k}: {v}" for k, v in metadata.items()]))
    
    print()  # Empty line after banner


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


def format_facts_count(count: int) -> str:
    """Format facts count with proper pluralization."""
    if count == 0:
        return "no facts"
    elif count == 1:
        return "1 fact"
    else:
        return f"{count} facts"