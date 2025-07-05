#!/usr/bin/env python3
"""
Complete thought detection module using LiteLLM and Pydantic
Phase 2: Parallel Processing Implementation
"""

import os
import threading
import queue
import time
from typing import Optional, List, Tuple, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from pydantic import BaseModel, Field
import litellm
from litellm import completion
from colorama import init, Fore, Style
from dotenv import load_dotenv
import string

# Load environment variables from .env file
load_dotenv()

# Initialize colorama for cross-platform color support
init()

# Configure litellm
litellm.drop_params = True
litellm.set_verbose = False

class ThoughtAnalysis(BaseModel):
    """Response model for thought completion analysis"""
    is_complete: bool = Field(
        description="Whether the text represents a complete thought (sentence, question, or coherent statement)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score from 0.0 to 1.0 indicating certainty of the assessment"
    )
    reasoning: str = Field(
        description="Brief explanation of why the text is or isn't a complete thought"
    )

class ThoughtCompletionDetector:
    """Detects complete thoughts in streaming text using GPT-4o mini with parallel processing"""
    
    def __init__(self, model: str = "gpt-4o-mini", debug: bool = False, max_workers: int = 3,
                 min_pause_before_analysis: float = 0.5, auto_complete_timeout: float = 5.0,
                 on_thought_complete=None):
        self.model = model
        self.debug = debug
        self.max_workers = max_workers
        self.min_pause_before_analysis = min_pause_before_analysis
        self.auto_complete_timeout = auto_complete_timeout
        self.on_thought_complete = on_thought_complete
        self.text_buffer = ""
        self.executor = None
        self.running = False
        self.last_complete_thought = ""
        self.accumulated_partial = ""
        self.last_analyzed_text = ""  # Track what we last sent for analysis
        
        # Timing state
        self.last_text_update_time = None
        self.pause_timer = None
        self.auto_complete_timer = None
        self.pending_analysis_text = None
        
        # Track futures and their submission order
        self.pending_futures: Dict[Future, str] = {}  # Future -> text mapping
        self.futures_lock = threading.Lock()
        
        # Results queue for maintaining FIFO order
        self.result_queue = queue.Queue()
        
        # For testing: store results by text
        self.results = {}
        self.results_lock = threading.Lock()
        
        # Start the executor
        self._start_executor()
        
    def _start_executor(self):
        """Start the ThreadPoolExecutor for parallel API calls"""
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='thought-detector')
        
        if self.debug:
            print(f"Started ThreadPoolExecutor with {self.max_workers} workers")
            
    def _analyze_text(self, text: str) -> Optional[ThoughtAnalysis]:
        """Analyze text for thought completion using LLM"""
        try:
            # Create the prompt
            system_prompt = """You are a linguistic expert analyzing real-time speech transcription.
Your task is to determine if the given text represents a CONVERSATIONALLY COMPLETE THOUGHT.

CRITICAL: You are analyzing SPOKEN conversation, NOT written text. The text comes from real-time speech recognition and DOES NOT include punctuation. Focus on whether the speaker has finished expressing their current thought based on the CONTENT and NATURAL SPEECH PATTERNS.

A thought is COMPLETE when:
- The speaker has expressed a full idea or statement
- It's a complete response or reaction
- The content feels finished and doesn't trail off
- It expresses a complete sentiment or observation

A thought is INCOMPLETE when:
- It ends with discourse markers ("and", "but", "so", "because", "or")
- It's clearly a setup phrase expecting more content
- It trails off without completing the idea
- It ends with filler words (um, uh, like, you know)
- The content suggests more is coming

BE CONSERVATIVE: When in doubt, mark as INCOMPLETE. Natural speech has pauses - we want to detect when someone has finished their thought, not just paused briefly.

Examples of COMPLETE thoughts (remember, NO PUNCTUATION):
- "I went to the store yesterday" (complete story/idea)
- "What time is it" (complete question)
- "That's amazing" (complete reaction)
- "Yes" (complete response)
- "The weather is nice today" (complete observation)

Examples of INCOMPLETE thoughts:
- "I went to the store" (trails off, might continue)
- "I went to the store and" (discourse marker at end)
- "What I mean is" (setup phrase)
- "One of the things about that is" (clearly expects more)
- "So basically" (discourse marker)
- "The thing is" (conversational setup)
- "I was thinking maybe we could" (trails off mid-idea)

REMEMBER: You're analyzing natural speech without punctuation. Focus on whether the thought/idea is complete, not grammar.

You MUST respond with a JSON object containing exactly these fields:
{
  "is_complete": boolean,
  "confidence": number between 0.0 and 1.0,
  "reasoning": "brief explanation string"
}"""

            user_prompt = f"Analyze if this transcribed speech is a complete thought: \"{text}\""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call LiteLLM with JSON mode
            response = completion(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=150,
                timeout=15.0  # Add timeout to prevent hanging on API calls
            )
            
            # Parse the response
            result = ThoughtAnalysis.model_validate_json(response.choices[0].message.content)
            
            if self.debug:
                print(f"\nAnalysis for '{text}': {result.is_complete} (confidence: {result.confidence})")
                
            return result
            
        except Exception as e:
            if self.debug:
                print(f"Analysis error: {e}")
            return None
            
    def _process_future_result(self, future: Future, text: str):
        """Process the result of a completed future"""
        try:
            result = future.result()
            
            # Store result for testing
            if result:
                with self.results_lock:
                    self.results[text] = result
            
            # Add to result queue
            self.result_queue.put((text, result))
            
            # Immediately check and notify
            self._notify_thought_complete()
            
        except Exception as e:
            if self.debug:
                print(f"Future processing error for '{text}': {e}")
            self.result_queue.put((text, None))
        finally:
            # Clean up future tracking
            with self.futures_lock:
                if future in self.pending_futures:
                    del self.pending_futures[future]
                    
    def _cancel_timers(self):
        """Cancel any pending timers"""
        if self.pause_timer:
            self.pause_timer.cancel()
            self.pause_timer = None
        if self.auto_complete_timer:
            self.auto_complete_timer.cancel()
            self.auto_complete_timer = None
            
    def _on_pause_detected(self):
        """Called when pause threshold is reached"""
        if self.debug:
            print(f"[DEBUG] {self.min_pause_before_analysis}s pause detected, submitting for analysis: '{self.pending_analysis_text}'")
        
        # Submit for analysis
        if self.pending_analysis_text and len(self.pending_analysis_text.strip()) >= 3:
            # Check for backpressure
            with self.futures_lock:
                if len(self.pending_futures) >= self.max_workers:
                    if self.debug:
                        print(f"Skipping analysis: worker pool is full ({self.max_workers} pending tasks)")
                    return
            
            # Submit analysis task
            future = self.executor.submit(self._analyze_text, self.pending_analysis_text)
            
            # Track the future
            with self.futures_lock:
                self.pending_futures[future] = self.pending_analysis_text
            
            # Set up callback
            future.add_done_callback(lambda f, t=self.pending_analysis_text: self._process_future_result(f, t))
            
            if self.debug:
                print(f"Submitted analysis for '{self.pending_analysis_text}' (active tasks: {len(self.pending_futures)})")
                
    def _notify_thought_complete(self):
        """Check result queue and notify callback if complete thought found"""
        try:
            while True:
                text, result = self.result_queue.get_nowait()
                
                if result and result.is_complete and result.confidence > 0.8:
                    # Strip trailing punctuation for comparison
                    analyzed_stripped = text.rstrip(string.punctuation)
                    accumulated_stripped = self.accumulated_partial.rstrip(string.punctuation)
                    
                    if analyzed_stripped == accumulated_stripped or accumulated_stripped.startswith(analyzed_stripped):
                        complete_thought = text
                        self.last_complete_thought = complete_thought
                        # Reset for next thought
                        self.accumulated_partial = ""
                        self.last_analyzed_text = ""
                        self.pending_analysis_text = None
                        self._cancel_timers()
                        
                        # Notify via callback
                        if self.on_thought_complete:
                            self.on_thought_complete(complete_thought, result)
                        
        except queue.Empty:
            pass
                
    def _on_auto_complete_timeout(self):
        """Called when auto-complete timeout is reached"""
        if self.debug:
            print(f"[DEBUG] {self.auto_complete_timeout}s timeout reached, auto-completing thought: '{self.accumulated_partial}'")
        
        # Auto-complete the current text without LLM
        if self.accumulated_partial:
            # Create a fake analysis result
            auto_result = ThoughtAnalysis(
                is_complete=True,
                confidence=1.0,
                reasoning="Auto-completed due to long pause"
            )
            
            # Add to result queue
            self.result_queue.put((self.accumulated_partial, auto_result))
            
            # Immediately check and notify
            self._notify_thought_complete()
    
    def process_text(self, new_text: str) -> Optional[Tuple[str, ThoughtAnalysis]]:
        """
        Process new transcribed text and return complete thought if detected
        
        Returns:
            Tuple of (complete_thought_text, analysis) if a complete thought is detected
            None otherwise
        """
        current_time = time.time()
        
        # Cancel any pending timers since we have new text
        self._cancel_timers()
        
        # Update state
        self.accumulated_partial = new_text
        self.last_text_update_time = current_time
        self.pending_analysis_text = new_text
        
        if self.debug:
            print(f"[DEBUG] Text updated, resetting timers: '{new_text}'")
        
        # Only set up timers if we have meaningful text
        if len(new_text.strip()) >= 3:
            # Set up pause detection timer
            self.pause_timer = threading.Timer(self.min_pause_before_analysis, self._on_pause_detected)
            self.pause_timer.daemon = True
            self.pause_timer.start()
            
            # Set up auto-complete timer
            self.auto_complete_timer = threading.Timer(self.auto_complete_timeout, self._on_auto_complete_timeout)
            self.auto_complete_timer.daemon = True
            self.auto_complete_timer.start()
        
        # Check for results (non-blocking)
        try:
            while True:
                text, result = self.result_queue.get_nowait()
                
                # If this analysis detected a complete thought
                if result and result.is_complete and result.confidence > 0.8:
                    # Strip trailing punctuation for comparison to handle RealtimeSTT's dynamic punctuation
                    analyzed_stripped = text.rstrip(string.punctuation)
                    accumulated_stripped = self.accumulated_partial.rstrip(string.punctuation)
                    
                    # Check if this is still relevant
                    if analyzed_stripped == accumulated_stripped or accumulated_stripped.startswith(analyzed_stripped):
                        complete_thought = text  # Use original text with punctuation
                        self.last_complete_thought = complete_thought
                        # Reset for next thought
                        self.accumulated_partial = ""
                        self.last_analyzed_text = ""
                        self.pending_analysis_text = None
                        self._cancel_timers()
                        return (complete_thought, result)
                    
        except queue.Empty:
            pass
            
        return None
        
    def format_complete_thought(self, thought: str, timestamp: Optional[datetime] = None) -> str:
        """Format a complete thought with color and timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
            
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Create a big, obvious display for complete thoughts
        border = "=" * 80
        formatted = f"""
{Fore.GREEN}{Style.BRIGHT}{border}{Style.RESET_ALL}
{Fore.YELLOW}[{time_str}]{Style.RESET_ALL}  {Fore.GREEN}{Style.BRIGHT}💭 COMPLETE THOUGHT DETECTED 💭{Style.RESET_ALL}

{Fore.WHITE}{Style.BRIGHT}{thought}{Style.RESET_ALL}

{Fore.GREEN}{Style.BRIGHT}{border}{Style.RESET_ALL}
"""
        
        return formatted
    
    def wait_for_result(self, text: str, timeout: float = 5.0) -> Optional[ThoughtAnalysis]:
        """
        Wait for a specific text's analysis result (for testing)
        
        Args:
            text: The text to analyze
            timeout: Maximum time to wait for result
            
        Returns:
            ThoughtAnalysis result or None if timeout
        """
        # Submit for analysis
        future = self.executor.submit(self._analyze_text, text)
        
        # Track the future
        with self.futures_lock:
            self.pending_futures[future] = text
        
        # Set up callback
        future.add_done_callback(lambda f: self._process_future_result(f, text))
        
        # Wait for result
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if result is available
            with self.results_lock:
                if text in self.results:
                    return self.results[text]
                    
            time.sleep(0.1)
            
        return None
        
    def stop(self):
        """Stop the executor and clean up"""
        self.running = False
        
        # Cancel any pending timers
        self._cancel_timers()
        
        if self.executor:
            # Cancel pending futures
            with self.futures_lock:
                for future in self.pending_futures:
                    future.cancel()
                self.pending_futures.clear()
                
            # Shutdown executor
            self.executor.shutdown(wait=True, cancel_futures=True)
            
            if self.debug:
                print("ThreadPoolExecutor shutdown complete")