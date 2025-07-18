#!/usr/bin/env python3
"""
Complete thought detection module using LiteLLM and Pydantic
"""

import os
import threading
import queue
import time
from typing import Optional, List, Tuple
from datetime import datetime
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
    """Detects complete thoughts in streaming text using GPT-4o mini"""
    
    def __init__(self, model: str = "gpt-4o-mini", debug: bool = False):
        self.model = model
        self.debug = debug
        self.text_buffer = ""
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.last_complete_thought = ""
        self.accumulated_partial = ""
        self.last_analyzed_text = ""  # Track what we last sent for analysis
        
        # For testing: store results by text
        self.results = {}
        self.results_lock = threading.Lock()
        
        # Start the worker thread
        self._start_worker()
        
    def _start_worker(self):
        """Start the background worker thread for API calls"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        
    def _worker(self):
        """Background worker that processes API calls"""
        while self.running:
            try:
                # Get text to analyze with a timeout
                text = self.processing_queue.get(timeout=0.1)
                
                # Skip if text is too short or same as last analysis
                if len(text.strip()) < 3:
                    continue
                    
                # Analyze the text
                result = self._analyze_text(text)
                
                # Store result
                if result:
                    with self.results_lock:
                        self.results[text] = result
                
                # Put result in the result queue
                self.result_queue.put((text, result))
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.debug:
                    print(f"Worker error: {e}")
                    
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
                max_tokens=150
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
            
            # Add to processing queue (non-blocking)
            try:
                self.processing_queue.put(new_text, block=False)
            except queue.Full:
                pass
        
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
        self.processing_queue.put(text)
        
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
        """Stop the worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)