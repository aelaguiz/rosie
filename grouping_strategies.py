#!/usr/bin/env python3
"""
Grouping strategies for speech transcription.
Provides abstraction for different approaches to grouping text.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
from datetime import datetime


class GroupingStrategy(ABC):
    """Abstract base class for text grouping strategies."""
    
    def __init__(self, 
                 on_group_complete: Optional[Callable[[str, Any], None]] = None,
                 debug: bool = False):
        """
        Initialize the grouping strategy.
        
        Args:
            on_group_complete: Callback when a group is complete.
                              Called with (text, metadata)
            debug: Enable debug output
        """
        self.on_group_complete = on_group_complete
        self.debug = debug
    
    @abstractmethod
    def process_text(self, text: str, timestamp: Optional[datetime] = None) -> None:
        """
        Process new transcribed text.
        
        Args:
            text: The transcribed text to process
            timestamp: When the text was captured
        """
        pass
    
    @abstractmethod
    def get_status(self) -> str:
        """
        Get current status of the grouping buffer.
        
        Returns:
            Status string (e.g., "OPEN", "PAUSED", "WAITING")
        """
        pass
    
    @abstractmethod
    def flush(self, action: str = "store") -> Optional[str]:
        """
        Flush the current buffer.
        
        Args:
            action: What to do with the buffer ("store" or "discard")
            
        Returns:
            The flushed text if action="store", None otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop any background threads or cleanup resources."""
        pass


def create_strategy(strategy_type: str, **kwargs) -> GroupingStrategy:
    """
    Factory function to create grouping strategies.
    
    Args:
        strategy_type: Type of strategy ("thought" or "topic")
        **kwargs: Arguments to pass to the strategy constructor
        
    Returns:
        Instance of the requested strategy
        
    Raises:
        ValueError: If strategy_type is unknown
    """
    if strategy_type == "thought":
        from thought_grouping_strategy import ThoughtGroupingStrategy
        return ThoughtGroupingStrategy(**kwargs)
    elif strategy_type == "topic":
        from topic_grouping_strategy import TopicGroupingStrategy
        return TopicGroupingStrategy(**kwargs)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")