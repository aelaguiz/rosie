#!/usr/bin/env python3
"""
Topic-based grouping strategy that accumulates text into topics
based on timing, voice cues, and LLM analysis.
"""

import os
import re
import json
import threading
import time
from typing import Optional, Callable, Any, List, Dict
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from colorama import init, Fore, Style, Back
from grouping_strategies import GroupingStrategy
from voice_command_prompts import SYSTEM_PROMPT_TOOLS, TOOLS
from logging_config import get_logger

# Load environment variables
load_dotenv()

# Initialize colorama for cross-platform color support
init()

# Set up logging
logger = get_logger(__name__)


class TopicGroupingStrategy(GroupingStrategy):
    """Groups text by topic with time-based and voice-cue boundaries."""
    
    def __init__(self, 
                 on_group_complete: Optional[Callable[[str, Any], None]] = None,
                 debug: bool = False,
                 # Timing parameters (will be used in Phase 5)
                 short_gap: float = 0.5,
                 max_gap: float = 3.0,
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
        
        # Timing parameters
        self.short_gap = short_gap
        self.max_gap = max_gap
        self.max_lifetime = max_lifetime
        
        # Threading infrastructure
        self._lock = threading.RLock()  # Use RLock to allow reentrant locking
        self._timer_thread = None
        self._stop_timer = threading.Event()
        
        # Command checking infrastructure
        self._accumulated_text = ""
        self._last_command_check = datetime.now()
        self._command_check_interval = 5.0  # Check every 5 seconds
        self._pause_threshold = 2.0  # Consider it a pause after 2 seconds
        
        # Initialize OpenAI client
        self._openai_client = None
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                self._openai_client = OpenAI(api_key=api_key)
                logger.debug("[TopicGroupingStrategy] OpenAI client initialized")
            except Exception as e:
                logger.warning(f"[TopicGroupingStrategy] Warning: Failed to initialize OpenAI client: {e}")
                logger.info("[TopicGroupingStrategy] Falling back to string matching for voice commands")
        else:
            logger.warning("[TopicGroupingStrategy] No OpenAI API key found, using string matching only")
        
        logger.debug(f"[TopicGroupingStrategy] Initialized with timing: short_gap={short_gap}s, max_gap={max_gap}s, max_lifetime={max_lifetime}s")
        
        # Start the timer thread
        self._start_timer_thread()
    
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
        
        # Add text to accumulator for command checking
        with self._lock:
            self._accumulated_text += " " + text.strip()
            
            # Check if we should look for commands
            should_check_commands = False
            time_since_check = (current_time - self._last_command_check).total_seconds()
            
            # Check every 5 seconds
            if time_since_check >= self._command_check_interval:
                should_check_commands = True
            
            # Or check on pause (2+ seconds since last text)
            elif self.last_ts:
                gap = (current_time - self.last_ts).total_seconds()
                if gap >= self._pause_threshold:
                    should_check_commands = True
        
        # Check for commands if needed (outside lock to avoid blocking)
        detected_commands = []
        if should_check_commands:
            detected_commands = self._check_for_commands()
            with self._lock:
                self._last_command_check = current_time
                # Clear accumulated text after checking
                self._accumulated_text = ""
        
        # Process any detected commands
        voice_cue = None
        if detected_commands:
            # Use the first high-confidence command
            for cmd in detected_commands:
                if cmd["confidence"] >= 0.7:  # 70% confidence threshold
                    voice_cue = cmd["command"]
                    # Remove trigger phrase from text if possible
                    if cmd["trigger_phrase"] in text:
                        text = text.replace(cmd["trigger_phrase"], "").strip()
                    break
        
        with self._lock:
            if voice_cue:
                logger.debug(f"[TopicGroupingStrategy] Detected voice cue: {voice_cue}")
                
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
                    logger.debug("[TopicGroupingStrategy] Topic paused")
                    return
                
                elif voice_cue == "resume":
                    self.status = "OPEN"
                    logger.debug("[TopicGroupingStrategy] Topic resumed")
                    return
                
                elif voice_cue == "flush":
                    # Flush current buffer immediately
                    if self.sentences:
                        self.voice_cue_flags.append("manual_flush")
                        self.flush("store")
                    return
            
            # Don't process text if paused
            if self.status == "PAUSED":
                logger.debug("[TopicGroupingStrategy] Ignoring text - topic is paused")
                return
            
            # Initialize timestamps on first text
            if self.start_ts is None:
                self.start_ts = current_time
                logger.debug(f"[TopicGroupingStrategy] Starting new topic at {self.start_ts.strftime('%H:%M:%S')}")
            
            self.last_ts = current_time
            
            # Split text into sentences and add to buffer
            new_sentences = self._split_into_sentences(text)
            if new_sentences:
                self.sentences.extend(new_sentences)
                logger.debug(f"[TopicGroupingStrategy] Added {len(new_sentences)} sentences, total: {len(self.sentences)}")
                for s in new_sentences:
                    logger.debug(f"  - {s}")
    
    def get_status(self) -> str:
        """
        Get current status of the grouping buffer.
        
        Returns:
            Status string: "OPEN", "PAUSED", or "DISCARD_CANDIDATE"
        """
        with self._lock:
            return self.status
    
    def flush(self, action: str = "store") -> Optional[str]:
        """
        Flush the current buffer.
        
        Args:
            action: What to do with the buffer ("store" or "discard")
            
        Returns:
            The flushed text if action="store", None otherwise
        """
        with self._lock:
            if not self.sentences:
                if self.debug:
                    logger.debug("[TopicGroupingStrategy] Flush called but no sentences to flush")
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
                    logger.debug(f"[TopicGroupingStrategy] Flushing topic with {len(self.sentences)} sentences")
                    logger.debug(f"  Duration: {(self.last_ts - self.start_ts).total_seconds():.1f}s")
                
                # Call the callback
                self.on_group_complete(full_text, metadata)
                
                # Reset buffer
                self._reset_buffer()
                return full_text
            
            elif action == "discard":
                logger.debug(f"[TopicGroupingStrategy] Discarding {len(self.sentences)} sentences")
                
                # Reset buffer
                self._reset_buffer()
                return None
            
            return None
    
    def _detect_voice_cue_legacy(self, text: str) -> Optional[str]:
        """
        Legacy string matching for voice cues (fallback when API unavailable).
        
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
    
    def _print_command_banner(self, command: str, confidence: float, trigger_phrase: str) -> None:
        """Print a colorful banner when a voice command is detected."""
        # Create the banner
        banner_width = 50
        command_display = command.upper().replace('_', ' ')
        
        print(f"\n{Fore.YELLOW + Style.BRIGHT}{'╔' + '═' * banner_width + '╗'}")
        print(f"║{' ' * ((banner_width - 28) // 2)}🎤 VOICE COMMAND DETECTED 🎤{' ' * ((banner_width - 28) // 2)}║")
        print(f"║{' ' * banner_width}║")
        print(f"║   Command: {Fore.CYAN}{command_display:<36}  {Fore.YELLOW}║")
        print(f"║   Confidence: {Fore.GREEN}{f'{confidence:.0%}':<33}  {Fore.YELLOW}║")
        print(f"║   Trigger: {Fore.WHITE}'{trigger_phrase[:35]}'{'...' if len(trigger_phrase) > 35 else '':<34}  {Fore.YELLOW}║")
        print(f"{'╚' + '═' * banner_width + '╝'}{Style.RESET_ALL}\n")
    
    def _check_for_commands(self) -> List[Dict[str, Any]]:
        """
        Check accumulated text for voice commands using GPT-4o tool calling.
        
        Returns:
            List of detected commands with their details
        """
        if not self._openai_client or not self._accumulated_text.strip():
            return []
        
        try:
            # Call GPT-4o with tool calling
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_TOOLS},
                {"role": "user", "content": self._accumulated_text}
            ]
            
            response = self._openai_client.chat.completions.create(
                model=os.getenv('VOICE_COMMAND_MODEL', 'gpt-4o'),
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
                timeout=5.0  # 5 second timeout
            )
            
            # Extract tool calls
            commands = []
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    command_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    # Map tool names to our internal command names
                    command_map = {
                        "new_note": "new_note",
                        "discard_previous": "discard", 
                        "flush_current": "flush"
                    }
                    
                    if command_name in command_map:
                        commands.append({
                            "command": command_map[command_name],
                            "confidence": args.get("confidence", 0.8),
                            "trigger_phrase": args.get("trigger_phrase", "")
                        })
                        
                        # Print the colorful banner
                        self._print_command_banner(
                            command_map[command_name],
                            args.get("confidence", 0.8),
                            args.get("trigger_phrase", "")
                        )
            
            return commands
            
        except Exception as e:
            logger.warning(f"[TopicGroupingStrategy] Error calling GPT-4o: {e}")
            logger.debug("[TopicGroupingStrategy] Falling back to legacy string matching")
            
            # Fallback to legacy detection
            legacy_cue = self._detect_voice_cue_legacy(self._accumulated_text)
            if legacy_cue:
                return [{
                    "command": legacy_cue,
                    "confidence": 0.6,  # Lower confidence for string matching
                    "trigger_phrase": self._accumulated_text.strip()
                }]
            
            return []
    
    def _reset_buffer(self):
        """Reset the buffer to start a new topic."""
        self.sentences = []
        self.start_ts = None
        self.last_ts = None
        self.status = "OPEN"
        self.voice_cue_flags = []
    
    def _process_detected_commands(self, commands: List[Dict[str, Any]]) -> None:
        """Process a list of detected commands."""
        for cmd in commands:
            if cmd["confidence"] >= 0.7:  # 70% confidence threshold
                voice_cue = cmd["command"]
                
                if voice_cue == "new_note":
                    # Flush current buffer (if any) and start new
                    if self.sentences:
                        self.voice_cue_flags.append("manual_split")
                        self.flush("store")
                
                elif voice_cue == "discard":
                    # Discard current buffer
                    self.flush("discard")
                
                elif voice_cue == "flush":
                    # Flush current buffer immediately
                    if self.sentences:
                        self.voice_cue_flags.append("manual_flush")
                        self.flush("store")
                
                # Only process first high-confidence command
                break
    
    def _start_timer_thread(self):
        """Start the background timer thread."""
        if self._timer_thread is None or not self._timer_thread.is_alive():
            self._timer_thread = threading.Thread(target=self._timer_worker, daemon=False)
            self._timer_thread.start()
            logger.debug("[TopicGroupingStrategy] Timer thread started")
    
    def _stop_timer_thread(self):
        """Stop the background timer thread."""
        if self._timer_thread and self._timer_thread.is_alive():
            self._stop_timer.set()
            self._timer_thread.join(timeout=2.0)
            logger.debug("[TopicGroupingStrategy] Timer thread stopped")
    
    def _timer_worker(self):
        """Background thread that checks for timeouts."""
        logger.debug("[TopicGroupingStrategy] Timer worker started")
        
        while not self._stop_timer.is_set():
            # Wait for 1 second or until stop is signaled
            if self._stop_timer.wait(1.0):
                break
            
            current_time = datetime.now()
            
            # First check for commands if enough time has passed
            with self._lock:
                time_since_check = (current_time - self._last_command_check).total_seconds()
                should_check = (time_since_check >= self._command_check_interval and 
                               self._accumulated_text.strip() and
                               self.status != "PAUSED")
            
            if should_check:
                # Check for commands (outside lock)
                commands = self._check_for_commands()
                with self._lock:
                    self._last_command_check = current_time
                    self._accumulated_text = ""
                    # Process any detected commands
                    if commands:
                        self._process_detected_commands(commands)
            
            # Check timeout conditions
            with self._lock:
                # Skip if buffer is empty or paused
                if not self.sentences or self.status == "PAUSED":
                    continue
                
                # Check max gap timeout
                if self.last_ts:
                    gap = (current_time - self.last_ts).total_seconds()
                    if gap > self.max_gap:
                        logger.debug(f"[TopicGroupingStrategy] Max gap exceeded: {gap:.1f}s > {self.max_gap}s")
                        self.voice_cue_flags.append("max_gap_exceeded")
                        self.flush("store")
                        continue
                
                # Check max lifetime timeout
                if self.start_ts:
                    lifetime = (current_time - self.start_ts).total_seconds()
                    if lifetime > self.max_lifetime:
                        logger.debug(f"[TopicGroupingStrategy] Max lifetime exceeded: {lifetime:.1f}s > {self.max_lifetime}s")
                        self.voice_cue_flags.append("max_lifetime_exceeded")
                        self.flush("store")
                        continue
        
        logger.debug("[TopicGroupingStrategy] Timer worker stopped")
    
    def stop(self) -> None:
        """Stop any background threads or cleanup resources."""
        logger.debug("[TopicGroupingStrategy] Stopping strategy")
        
        # Stop the timer thread
        self._stop_timer_thread()
        
        # Flush any remaining content
        with self._lock:
            if self.sentences:
                self.flush("store")