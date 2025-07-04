#!/usr/bin/env python3
"""Test simulating real-time speech with delays"""

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

def test_realtime_speech():
    """Simulate real-time speech transcription with delays"""
    print("Testing real-time speech simulation...")
    detector = ThoughtCompletionDetector(debug=True)
    
    # Simulate someone saying "I went to the store yesterday"
    updates = [
        ("I", 0.1),
        ("I went", 0.2),
        ("I went to", 0.15),
        ("I went to the", 0.1),
        ("I went to the store", 0.3),
        ("I went to the store yesterday", 0.2),
    ]
    
    print("\n" + "="*80)
    print("Simulating: 'I went to the store yesterday'")
    print("="*80)
    
    for text, delay in updates:
        print(f"\n[{time.strftime('%H:%M:%S')}] Speech update: '{text}'")
        
        # Process the text
        result = detector.process_text(text)
        
        if result:
            complete_thought, analysis = result
            print(f"✅ COMPLETE THOUGHT DETECTED: '{complete_thought}'")
            print(f"   Confidence: {analysis.confidence}")
            print(f"   Reasoning: {analysis.reasoning}")
            break
        else:
            print(f"⏳ Still listening...")
        
        # Simulate delay before next update
        time.sleep(delay)
    
    # Wait a bit for any pending results
    print("\nChecking for any pending results...")
    time.sleep(2)
    
    # Try one more time to get results
    result = detector.process_text(text)
    if result:
        complete_thought, analysis = result
        print(f"✅ LATE DETECTION: '{complete_thought}'")
    else:
        print("❌ No complete thought detected")
    
    detector.stop()
    print("\n\nTest completed!")

if __name__ == "__main__":
    test_realtime_speech()