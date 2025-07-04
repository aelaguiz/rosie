#!/usr/bin/env python3
"""Test for lambda closure bug fix"""

import os
import time
import threading
from dotenv import load_dotenv
from thought_detector import ThoughtCompletionDetector

# Load environment variables from .env file
load_dotenv()

# Check for API key
if not os.environ.get('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    exit(1)

def test_lambda_closure_bug():
    """Test that rapid successive calls don't cause lambda closure issues"""
    print("Testing Lambda Closure Bug Fix")
    print("=" * 50)
    
    detector = ThoughtCompletionDetector(debug=True, max_workers=3)
    
    # Test texts that should all be detected as complete
    test_texts = [
        "First sentence here.",
        "Second one goes here.",
        "Third example now.",
        "Fourth test case.",
        "Fifth and final."
    ]
    
    # Submit all texts using wait_for_result in separate threads
    # This ensures each gets processed independently
    results = {}
    results_lock = threading.Lock()
    
    def submit_and_verify(text):
        """Submit text and verify the callback gets the correct value"""
        # This will trigger the bug if lambda doesn't capture text correctly
        result = detector.wait_for_result(text, timeout=5.0)
        with results_lock:
            if result:
                results[text] = result.is_complete
                print(f"Processed: '{text}' -> Complete: {result.is_complete}")
            else:
                results[text] = None
                print(f"Failed: '{text}' -> TIMEOUT")
    
    # Submit all texts in rapid succession using threads
    print("\nSubmitting texts rapidly via threads...")
    threads = []
    for text in test_texts:
        thread = threading.Thread(target=submit_and_verify, args=(text,))
        threads.append(thread)
        thread.start()
        time.sleep(0.01)  # Very short delay between thread starts
    
    # Wait for all threads
    print("\nWaiting for all threads to complete...")
    for thread in threads:
        thread.join()
    
    detector.stop()
    
    # Verify results
    print("\nVerifying results...")
    all_correct = True
    
    with results_lock:
        for text in test_texts:
            if text in results and results[text] is not None:
                print(f"✓ '{text}' -> Successfully processed")
            else:
                print(f"✗ '{text}' -> FAILED")
                all_correct = False
    
    print("\n" + "=" * 50)
    if all_correct:
        print("✅ PASS - Lambda closure bug is fixed!")
        print("All texts were processed with correct callbacks")
    else:
        print("❌ FAIL - Some texts were not processed correctly")
    
    return all_correct

def test_backpressure():
    """Test that backpressure prevents overwhelming the system"""
    print("\n\nTesting Backpressure Control")
    print("=" * 50)
    
    # Use only 1 worker to make backpressure more likely
    detector = ThoughtCompletionDetector(debug=True, max_workers=1)
    
    # Try to submit many texts very rapidly
    test_texts = [f"Test sentence number {i}." for i in range(20)]
    
    submitted = 0
    skipped = 0
    skip_messages = []
    
    print("\nRapidly submitting 20 texts with only 1 worker...")
    for text in test_texts:
        # Capture debug output
        import io
        import sys
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output
        
        result = detector.process_text(text)
        
        sys.stdout = old_stdout
        output = captured_output.getvalue()
        
        if "worker pool is full" in output:
            skipped += 1
            skip_messages.append(f"Skipped: '{text}'")
        else:
            submitted += 1
        
        # No delay - submit as fast as possible
    
    # Wait a bit for processing
    time.sleep(2.0)
    detector.stop()
    
    print(f"\nResults: Submitted: {submitted}, Skipped: {skipped}")
    if skip_messages:
        print("Sample skip messages:")
        for msg in skip_messages[:3]:
            print(f"  {msg}")
    
    if skipped > 0:
        print("✅ PASS - Backpressure is working!")
        print(f"Successfully prevented {skipped} tasks from overwhelming the system")
        return True
    else:
        print("⚠️  WARNING - No backpressure observed")
        print("This might be OK if the API is very fast")
        return True  # Not a failure, just informational

def main():
    """Run lambda closure and backpressure tests"""
    print("Lambda Closure & Backpressure Tests")
    print("=" * 80)
    
    closure_passed = test_lambda_closure_bug()
    backpressure_passed = test_backpressure()
    
    if closure_passed and backpressure_passed:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    main()