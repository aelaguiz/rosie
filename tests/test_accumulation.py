#!/usr/bin/env python3
"""Test to prove that incomplete thoughts are not accumulated properly"""

import os
import time
from dotenv import load_dotenv
from thought_detector import ThoughtCompletionDetector

# Load environment variables
load_dotenv()

# Check for API key
if not os.environ.get('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY not set in .env file")
    exit(1)

def test_text_accumulation():
    """Test that incomplete thoughts should accumulate"""
    print("Testing text accumulation behavior...")
    detector = ThoughtCompletionDetector(debug=True)
    
    # Simulate incremental speech transcription
    test_sequence = [
        ("I", False, "Just starting"),
        ("I went", False, "Still incomplete"),
        ("I went to", False, "Still building"),
        ("I went to the", False, "Missing object"),
        ("I went to the store", False, "Missing when/why"), 
        ("I went to the store yesterday", True, "Complete sentence"),
    ]
    
    print("\n" + "="*80)
    print("TEST 1: Incremental text should accumulate")
    print("="*80)
    
    accumulated = ""
    for text, should_be_complete, description in test_sequence:
        print(f"\n--- Processing: '{text}' ({description}) ---")
        
        # Process the text
        result = detector.process_text(text)
        
        if result:
            complete_thought, analysis = result
            print(f"✅ Complete thought detected: '{complete_thought}'")
            print(f"   Confidence: {analysis.confidence}")
            if not should_be_complete:
                print("❌ ERROR: Detected as complete when it shouldn't be!")
        else:
            print(f"⏳ Not complete yet")
            if should_be_complete:
                print("❌ ERROR: Should have been detected as complete!")
    
    # Test 2: Direct complete vs incomplete
    print("\n" + "="*80)
    print("TEST 2: Direct analysis of complete vs incomplete")
    print("="*80)
    
    # Wait a bit to avoid rate limits
    time.sleep(1)
    
    # Test incomplete directly
    incomplete_text = "I went to the"
    print(f"\nTesting incomplete: '{incomplete_text}'")
    result = detector.wait_for_result(incomplete_text, timeout=5.0)
    if result:
        print(f"Result: is_complete={result.is_complete}, confidence={result.confidence}")
        print(f"Reasoning: {result.reasoning}")
    
    # Test complete directly
    complete_text = "I went to the store yesterday."
    print(f"\nTesting complete: '{complete_text}'")
    result = detector.wait_for_result(complete_text, timeout=5.0)
    if result:
        print(f"Result: is_complete={result.is_complete}, confidence={result.confidence}")
        print(f"Reasoning: {result.reasoning}")
    
    # Test 3: What happens with overlapping updates
    print("\n" + "="*80)
    print("TEST 3: Overlapping updates (simulating real speech)")
    print("="*80)
    
    updates = [
        "Hello",
        "Hello there",
        "Hello there how", 
        "Hello there how are",
        "Hello there how are you",
        "Hello there how are you doing",
        "Hello there how are you doing today"
    ]
    
    for update in updates:
        print(f"\nUpdate: '{update}'")
        result = detector.process_text(update)
        if result:
            complete_thought, _ = result
            print(f"✅ Complete: '{complete_thought}'")
            # Reset for next sequence
            print("   (Would reset accumulated text here)")
    
    detector.stop()
    print("\n\nTest completed!")

if __name__ == "__main__":
    test_text_accumulation()