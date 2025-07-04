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
    
    def __init__(self, model: str = "gpt-4o-mini", debug: bool = False, max_workers: int = 3):
        self.model = model
        self.debug = debug
        self.max_workers = max_workers
        self.text_buffer = ""
        self.executor = None
        self.running = False
        self.last_complete_thought = ""
        self.accumulated_partial = ""
        self.last_analyzed_text = ""  # Track what we last sent for analysis
        
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

CRITICAL: Focus on CONVERSATIONAL completeness, not just grammatical completeness. In natural speech, people often pause mid-thought even when a sentence could technically stand alone.

A thought is COMPLETE only when:
- The speaker has clearly finished expressing their idea
- There's strong punctuation (period, question mark, exclamation)
- It's a clear, standalone response or statement
- There's no expectation of immediate continuation

A thought is INCOMPLETE if:
- It lacks ending punctuation (especially periods)
- It ends with discourse markers ("and", "but", "so", "because", "or")
- It sounds like the speaker paused mid-thought
- It's grammatically complete but conversationally expects more
- It ends with filler words (um, uh, like, you know)
- The tone suggests continuation

BE CONSERVATIVE: When in doubt, mark as INCOMPLETE. It's better to wait for more text than to prematurely cut off a thought.

Examples of COMPLETE thoughts:
- "I went to the store yesterday." (has period, complete idea)
- "What time is it?" (complete question with punctuation)
- "That's amazing!" (complete exclamation)
- "Yes." (complete response)
- "The weather is nice today." (complete statement with period)

Examples of INCOMPLETE thoughts (even if grammatically valid):
- "I went to the store" (no period, likely to continue)
- "I went to the store and" (discourse marker at end)
- "The weather is nice" (no period, may continue)
- "What I mean is" (clearly expects continuation)
- "One of the things about that is" (setup for more)
- "So basically" (discourse marker, expects more)
- "The thing is" (conversational setup)

PUNCTUATION MATTERS: Presence of a period, question mark, or exclamation point is a strong signal of completeness. Absence is a strong signal of incompleteness.

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
            
        except Exception as e:
            if self.debug:
                print(f"Future processing error for '{text}': {e}")
            self.result_queue.put((text, None))
        finally:
            # Clean up future tracking
            with self.futures_lock:
                if future in self.pending_futures:
                    del self.pending_futures[future]
                    
    def process_text(self, new_text: str) -> Optional[Tuple[str, ThoughtAnalysis]]:
        """
        Process new transcribed text and return complete thought if detected
        
        Returns:
            Tuple of (complete_thought_text, analysis) if a complete thought is detected
            None otherwise
        """
        # RealtimeSTT sends the full accumulated text each time
        self.accumulated_partial = new_text
        
        # Only analyze if text has grown (not shortened or same)
        if len(new_text) > len(self.last_analyzed_text):
            self.last_analyzed_text = new_text
            
            # Skip if text is too short
            if len(new_text.strip()) >= 3:
                # Check for backpressure - limit pending tasks to prevent overload
                with self.futures_lock:
                    if len(self.pending_futures) >= self.max_workers:
                        if self.debug:
                            print(f"Skipping analysis for '{new_text}': worker pool is full ({self.max_workers} pending tasks)")
                        return None
                
                # Submit analysis task to executor
                future = self.executor.submit(self._analyze_text, new_text)
                
                # Track the future
                with self.futures_lock:
                    self.pending_futures[future] = new_text
                
                # Set up callback to process result when complete
                # Use default argument to capture new_text value at lambda creation time
                future.add_done_callback(lambda f, t=new_text: self._process_future_result(f, t))
                
                if self.debug:
                    print(f"Submitted analysis for '{new_text}' (active tasks: {len(self.pending_futures)})")
        
        # Check for results (non-blocking)
        try:
            while True:
                text, result = self.result_queue.get_nowait()
                
                # If this analysis is for current text and it's complete
                if result and text == self.accumulated_partial and result.is_complete and result.confidence > 0.8:
                    complete_thought = self.accumulated_partial
                    self.last_complete_thought = complete_thought
                    # Reset for next thought
                    self.accumulated_partial = ""
                    self.last_analyzed_text = ""
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