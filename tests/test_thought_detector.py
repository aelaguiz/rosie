#!/usr/bin/env python3
"""Async test script for thought detector - validates complete thought detection"""

import os
import time
from dotenv import load_dotenv
from thought_detector import ThoughtCompletionDetector

# Load environment variables from .env file
load_dotenv()

# Check for API key
if not os.environ.get('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    print("Please set it in .env file")
    exit(1)

# Test cases with expected results
TEST_CASES = [
    # Complete thoughts
    ("I went to the store yesterday.", True, "Complete sentence"),
    ("What time is it?", True, "Complete question"),
    ("That's amazing!", True, "Complete exclamation"),
    ("The weather is nice today.", True, "Complete statement"),
    ("Yes.", True, "Complete response"),
    ("I love programming.", True, "Complete sentence"),
    ("How are you doing?", True, "Complete question"),
    
    # Incomplete thoughts
    ("I went to the", False, "Incomplete - ends mid-phrase"),
    ("What time is", False, "Incomplete question"),
    ("The weather is nice but", False, "Ends with conjunction"),
    ("One of the things I", False, "Incomplete phrase"),
    ("So basically what I'm trying to", False, "Incomplete explanation"),
    ("Um, so like", False, "Filler words only"),
    ("And then he said that", False, "Incomplete - expects continuation"),
    ("When I was", False, "Incomplete clause"),
]

def test_thought_detector():
    """Run async tests on the thought detector using wait_for_result"""
    print("Initializing thought detector...")
    detector = ThoughtCompletionDetector(debug=True)
    
    print("\nRunning async tests with proper synchronization...")
    print("=" * 80)
    
    correct = 0
    total = len(TEST_CASES)
    
    for text, expected_complete, description in TEST_CASES:
        print(f"\nTest: '{text}'")
        print(f"Expected: {'COMPLETE' if expected_complete else 'INCOMPLETE'} - {description}")
        
        # Time the analysis
        start_time = time.time()
        
        # Use wait_for_result to properly test async behavior
        result = detector.wait_for_result(text, timeout=5.0)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        if result:
            is_complete = result.is_complete
            print(f"Result: {'COMPLETE' if is_complete else 'INCOMPLETE'} (confidence: {result.confidence:.2f})")
            print(f"Reasoning: {result.reasoning}")
            print(f"Time: {elapsed_time:.3f}s")
        else:
            print(f"Result: TIMEOUT - No result received")
            print(f"Time: {elapsed_time:.3f}s")
            is_complete = False
        
        # Check if correct
        if result and is_complete == expected_complete:
            print("✅ CORRECT")
            correct += 1
        else:
            print("❌ INCORRECT")
        
        print("-" * 80)
    
    # Summary
    print(f"\n\nSUMMARY: {correct}/{total} correct ({(correct/total)*100:.1f}%)")
    
    if correct == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - correct} tests failed")
    
    # Cleanup
    detector.stop()
    print("\n\nTest completed!")

if __name__ == "__main__":
    test_thought_detector()