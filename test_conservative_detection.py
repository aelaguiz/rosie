#!/usr/bin/env python3
"""Test conservative thought detection - verifies Phase 1 implementation"""

import os
from dotenv import load_dotenv
from thought_detector import ThoughtCompletionDetector
import litellm
from litellm import completion
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Check for API key
if not os.environ.get('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    exit(1)

# Test cases for conservative detection
TEST_CASES = [
    # Cases that should NOT be detected as complete (even if grammatically valid)
    ("I went to the store", False, "No period - likely to continue"),
    ("The weather is nice", False, "No period - may continue"),
    ("What I mean is", False, "Clear setup for continuation"),
    ("The thing is", False, "Conversational setup"),
    ("One thing about that is", False, "Setup phrase"),
    ("So basically", False, "Discourse marker expecting more"),
    ("I think that", False, "Incomplete thought setup"),
    ("And then I", False, "Starts with 'and', incomplete"),
    ("But the problem is", False, "Setup for explanation"),
    ("What happened was", False, "Story setup"),
    
    # Discourse markers at end
    ("I went to the store and", False, "Ends with 'and'"),
    ("The weather is nice but", False, "Ends with 'but'"),
    ("I like programming so", False, "Ends with 'so'"),
    ("We could do that or", False, "Ends with 'or'"),
    ("I went there because", False, "Ends with 'because'"),
    
    # Cases that SHOULD be detected as complete (with punctuation)
    ("I went to the store.", True, "Period indicates completion"),
    ("I went to the store yesterday.", True, "Complete sentence with period"),
    ("What time is it?", True, "Complete question with punctuation"),
    ("That's amazing!", True, "Complete exclamation"),
    ("Yes.", True, "Complete response with period"),
    ("No.", True, "Complete response with period"),
    ("The weather is nice today.", True, "Complete statement with period"),
    ("I love programming.", True, "Complete sentence with period"),
    
    # Edge cases
    ("Really?", True, "Complete question"),
    ("Wow!", True, "Complete exclamation"),
    ("Oh.", True, "Complete interjection with period"),
    ("I see.", True, "Complete acknowledgment"),
    ("Got it.", True, "Complete confirmation"),
]

class ThoughtAnalysis(BaseModel):
    """Response model for thought completion analysis"""
    is_complete: bool = Field(description="Whether the text represents a complete thought")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation of the assessment")

def main():
    """Run conservative detection tests"""
    print("Testing conservative thought detection (Phase 1)...")
    print("=" * 80)
    
    # Initialize detector
    detector = ThoughtCompletionDetector(debug=True)
    
    correct = 0
    total = len(TEST_CASES)
    failures = []
    
    for text, expected_complete, description in TEST_CASES:
        print(f"\nTest: '{text}'")
        print(f"Expected: {'COMPLETE' if expected_complete else 'INCOMPLETE'} - {description}")
        
        try:
            # Use wait_for_result for synchronous testing
            result = detector.wait_for_result(text, timeout=5.0)
            
            if result:
                print(f"Result: {'COMPLETE' if result.is_complete else 'INCOMPLETE'} (confidence: {result.confidence:.2f})")
                print(f"Reasoning: {result.reasoning}")
                
                # Check if correct
                if result.is_complete == expected_complete:
                    print("✅ CORRECT")
                    correct += 1
                else:
                    print("❌ INCORRECT")
                    failures.append((text, expected_complete, result.is_complete))
            else:
                print("❌ TIMEOUT - No result received")
                failures.append((text, expected_complete, None))
                
        except Exception as e:
            print(f"Error: {e}")
            print("❌ ERROR")
            failures.append((text, expected_complete, None))
        
        print("-" * 80)
    
    # Summary
    print(f"\n\nSUMMARY: {correct}/{total} correct ({(correct/total)*100:.1f}%)")
    
    if failures:
        print("\nFAILURES:")
        for text, expected, actual in failures:
            print(f"  '{text}' - Expected: {expected}, Got: {actual}")
    
    # Cleanup
    detector.stop()
    
    # Phase 1 success criteria check
    print("\n" + "=" * 80)
    print("PHASE 1 SUCCESS CRITERIA CHECK:")
    
    # Check specific criteria from plan
    criteria_checks = [
        ("I went to the store", False, "Not detected as complete"),
        ("I went to the store.", True, "Detected as complete"),
    ]
    
    all_criteria_met = True
    for text, expected, criteria in criteria_checks:
        result = detector.results.get(text)
        if result and result.is_complete == expected:
            print(f"✅ {criteria}: '{text}'")
        else:
            print(f"❌ {criteria}: '{text}'")
            all_criteria_met = False
    
    if all_criteria_met:
        print("\n✅ ALL PHASE 1 SUCCESS CRITERIA MET!")
    else:
        print("\n❌ Some Phase 1 criteria not met")

if __name__ == "__main__":
    main()