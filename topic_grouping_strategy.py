#!/usr/bin/env python3
"""
Topic-based grouping strategy that accumulates text into topics
based on timing, voice cues, and LLM analysis.
"""

import re
from typing import Optional, Callable, Any, List
from datetime import datetime
from grouping_strategies import GroupingStrategy


class TopicGroupingStrategy(GroupingStrategy):
    """Groups text by topic with time-based and voice-cue boundaries."""
    
    def __init__(self, 
                 on_group_complete: Optional[Callable[[str, Any], None]] = None,
                 debug: bool = False,
                 # Timing parameters (will be used in Phase 5)
                 short_gap: float = 0.5,
                 max_gap: float = 90.0,
                 max_lifetime: float = 300.0):  # 5 minutes
        """
        Initialize topic grouping strategy.
        
        Args:
            on_group_complete: Callback when a topic is complete
            debug: Enable debug output
            short_gap: Short pause threshold (for future use)
            max_gap: Maximum gap before auto-flush (for future use)
            max_lifetime: Maximum topic lifetime (for future use)
        """
        super().__init__(on_group_complete, debug)
        
        # Buffer state
        self.start_ts: Optional[datetime] = None
        self.last_ts: Optional[datetime] = None
        self.sentences: List[str] = []
        self.status = "OPEN"
        self.voice_cue_flags: List[str] = []
        
        # Timing parameters (stored for Phase 5)
        self.short_gap = short_gap
        self.max_gap = max_gap
        self.max_lifetime = max_lifetime
        
        if self.debug:
            print(f"[TopicGroupingStrategy] Initialized with timing: short_gap={short_gap}s, max_gap={max_gap}s, max_lifetime={max_lifetime}s")
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences based on punctuation."""
        # Simple sentence splitting - splits on . ! ? followed by space or end
        # Keeps the punctuation with the sentence
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        # Filter out empty sentences
        return [s.strip() for s in sentences if s.strip()]
    
    def process_text(self, text: str, timestamp: Optional[datetime] = None) -> None:
        """
        Process new transcribed text.
        
        Args:
            text: The transcribed text to process
            timestamp: When the text was captured
        """
        if not text or not text.strip():
            return
        
        current_time = timestamp or datetime.now()
        
        # Check for voice cues first
        voice_cue = self._detect_voice_cue(text)
        
        if voice_cue:
            if self.debug:
                print(f"[TopicGroupingStrategy] Detected voice cue: {voice_cue}")
            
            if voice_cue == "new_note":
                # Flush current buffer (if any) and start new
                if self.sentences:
                    self.voice_cue_flags.append("manual_split")
                    self.flush("store")
                # Remove the voice cue from the text before processing
                text = text.lower().replace("new note", "").strip()
                if not text:
                    return
            
            elif voice_cue == "discard":
                # Discard current buffer
                self.flush("discard")
                return
            
            elif voice_cue == "pause":
                self.status = "PAUSED"
                if self.debug:
                    print("[TopicGroupingStrategy] Topic paused")
                return
            
            elif voice_cue == "resume":
                self.status = "OPEN"
                if self.debug:
                    print("[TopicGroupingStrategy] Topic resumed")
                return
        
        # Don't process text if paused
        if self.status == "PAUSED":
            if self.debug:
                print("[TopicGroupingStrategy] Ignoring text - topic is paused")
            return
        
        # Initialize timestamps on first text
        if self.start_ts is None:
            self.start_ts = current_time
            if self.debug:
                print(f"[TopicGroupingStrategy] Starting new topic at {self.start_ts.strftime('%H:%M:%S')}")
        
        self.last_ts = current_time
        
        # Split text into sentences and add to buffer
        new_sentences = self._split_into_sentences(text)
        if new_sentences:
            self.sentences.extend(new_sentences)
            if self.debug:
                print(f"[TopicGroupingStrategy] Added {len(new_sentences)} sentences, total: {len(self.sentences)}")
                for s in new_sentences:
                    print(f"  - {s}")
    
    def get_status(self) -> str:
        """
        Get current status of the grouping buffer.
        
        Returns:
            Status string: "OPEN", "PAUSED", or "DISCARD_CANDIDATE"
        """
        return self.status
    
    def flush(self, action: str = "store") -> Optional[str]:
        """
        Flush the current buffer.
        
        Args:
            action: What to do with the buffer ("store" or "discard")
            
        Returns:
            The flushed text if action="store", None otherwise
        """
        if not self.sentences:
            if self.debug:
                print("[TopicGroupingStrategy] Flush called but no sentences to flush")
            return None
        
        # Join sentences into complete text
        full_text = " ".join(self.sentences)
        
        if action == "store" and self.on_group_complete:
            # Create metadata for the completed topic
            metadata = {
                "type": "topic",
                "start_ts": self.start_ts.isoformat() if self.start_ts else None,
                "end_ts": self.last_ts.isoformat() if self.last_ts else None,
                "sentence_count": len(self.sentences),
                "voice_cue_flags": self.voice_cue_flags.copy(),  # Copy current flags
                "tags": []  # For future use
            }
            
            if self.debug:
                print(f"[TopicGroupingStrategy] Flushing topic with {len(self.sentences)} sentences")
                print(f"  Duration: {(self.last_ts - self.start_ts).total_seconds():.1f}s")
            
            # Call the callback
            self.on_group_complete(full_text, metadata)
            
            # Reset buffer
            self._reset_buffer()
            return full_text
        
        elif action == "discard":
            if self.debug:
                print(f"[TopicGroupingStrategy] Discarding {len(self.sentences)} sentences")
            
            # Reset buffer
            self._reset_buffer()
            return None
        
        return None
    
    def _detect_voice_cue(self, text: str) -> Optional[str]:
        """
        Detect voice cues in the text.
        
        Args:
            text: Text to check for voice cues
            
        Returns:
            The detected cue type or None
        """
        text_lower = text.lower().strip()
        
        # Check for exact matches or partial matches
        if "new note" in text_lower:
            return "new_note"
        elif "discard that" in text_lower:
            return "discard"
        elif "pause note" in text_lower:
            return "pause"
        elif "resume note" in text_lower:
            return "resume"
        
        return None
    
    def _reset_buffer(self):
        """Reset the buffer to start a new topic."""
        self.sentences = []
        self.start_ts = None
        self.last_ts = None
        self.status = "OPEN"
        self.voice_cue_flags = []
    
    def stop(self) -> None:
        """Stop any background threads or cleanup resources."""
        # For Phase 3, we don't have any background threads
        # Phase 5 will add timer threads that need cleanup
        if self.debug:
            print("[TopicGroupingStrategy] Stopping strategy")
        
        # Flush any remaining content
        if self.sentences:
            self.flush("store")