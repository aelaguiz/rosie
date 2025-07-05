#!/usr/bin/env python3
"""
Thought-based grouping strategy using the existing ThoughtCompletionDetector.
"""

from typing import Optional, Callable, Any, Tuple
from datetime import datetime
from grouping_strategies import GroupingStrategy
from thought_detector import ThoughtCompletionDetector, ThoughtAnalysis


class ThoughtGroupingStrategy(GroupingStrategy):
    """Groups text by detecting complete thoughts."""
    
    def __init__(self, 
                 on_group_complete: Optional[Callable[[str, Any], None]] = None,
                 debug: bool = False,
                 model: str = "gpt-4o-mini",
                 max_workers: int = 3,
                 min_pause_before_analysis: float = 0.5,
                 auto_complete_timeout: float = 5.0):
        """
        Initialize thought grouping strategy.
        
        Args:
            on_group_complete: Callback when a thought is complete
            debug: Enable debug output
            model: LLM model to use
            max_workers: Number of parallel workers
            min_pause_before_analysis: Minimum pause before analyzing
            auto_complete_timeout: Timeout for auto-completion
        """
        super().__init__(on_group_complete, debug)
        
        # Create wrapped detector with our callback
        self.detector = ThoughtCompletionDetector(
            model=model,
            debug=debug,
            max_workers=max_workers,
            min_pause_before_analysis=min_pause_before_analysis,
            auto_complete_timeout=auto_complete_timeout,
            on_thought_complete=self._on_thought_complete
        )
        
        self.status = "WAITING"
        self.last_thought = None
        self.last_analysis = None
    
    def _on_thought_complete(self, thought: str, analysis: ThoughtAnalysis) -> None:
        """Internal callback from detector."""
        self.last_thought = thought
        self.last_analysis = analysis
        self.status = "COMPLETE"
        
        # Call external callback with our metadata format
        if self.on_group_complete:
            metadata = {
                "type": "thought",
                "confidence": analysis.confidence,
                "reasoning": analysis.reasoning,
                "is_complete": analysis.is_complete
            }
            self.on_group_complete(thought, metadata)
        
        # Reset status after callback
        self.status = "WAITING"
    
    def process_text(self, text: str, timestamp: Optional[datetime] = None) -> None:
        """Process new transcribed text."""
        if text and text.strip():
            self.status = "PROCESSING"
            # Detector handles all the timing and analysis logic
            result = self.detector.process_text(text)
            
            # If detector returned a result directly (for testing/sync mode)
            if result:
                thought, analysis = result
                self._on_thought_complete(thought, analysis)
            else:
                # Normal async mode - callback will fire when ready
                self.status = "WAITING"
    
    def get_status(self) -> str:
        """Get current status."""
        return self.status
    
    def flush(self, action: str = "store") -> Optional[str]:
        """
        Flush current buffer.
        
        For thought detection, this forces analysis of accumulated text.
        """
        if action == "store" and self.detector.accumulated_partial:
            # Force completion of current text
            text = self.detector.accumulated_partial
            self.detector._on_auto_complete_timeout()
            return text
        elif action == "discard":
            # Clear accumulated text
            self.detector.accumulated_partial = ""
            self.detector.last_analyzed_text = ""
            self.detector._cancel_timers()
            return None
        
        return None
    
    def stop(self) -> None:
        """Stop the detector and cleanup."""
        self.detector.stop()
    
    def format_complete_thought(self, thought: str, timestamp: Optional[datetime] = None) -> str:
        """Format a complete thought for display."""
        return self.detector.format_complete_thought(thought, timestamp)