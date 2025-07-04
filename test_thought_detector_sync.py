#!/usr/bin/env python3
"""Synchronous test script for thought detector - validates complete thought detection"""

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

class ThoughtAnalysis(BaseModel):
    """Response model for thought completion analysis"""
    is_complete: bool = Field(description="Whether the text represents a complete thought")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation of the assessment")

def analyze_text_sync(text: str) -> ThoughtAnalysis:
    """Synchronous version of thought analysis for testing"""
    system_prompt = """You are a linguistic expert analyzing real-time speech transcription.
Your task is to determine if the given text represents a COMPLETE THOUGHT.

A complete thought is:
- A grammatically complete sentence (has subject and predicate)
- A complete question
- A coherent standalone statement
- An interjection or exclamation that stands alone

A thought is INCOMPLETE if:
- It ends mid-sentence or mid-phrase
- It's missing essential grammatical components
- It appears to be building toward something not yet expressed
- It ends with filler words suggesting continuation (um, uh, like, so)

Remember: In speech, people often pause mid-thought. Be conservative - only mark as complete if you're confident the speaker has finished expressing that particular idea.

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
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=150
    )
    
    # Parse the response
    return ThoughtAnalysis.model_validate_json(response.choices[0].message.content)

def main():
    """Run synchronous tests"""
    print("Running synchronous thought detector tests...")
    print("=" * 80)
    
    correct = 0
    total = len(TEST_CASES)
    
    for text, expected_complete, description in TEST_CASES:
        print(f"\nTest: '{text}'")
        print(f"Expected: {'COMPLETE' if expected_complete else 'INCOMPLETE'} - {description}")
        
        try:
            # Analyze the text
            result = analyze_text_sync(text)
            
            print(f"Result: {'COMPLETE' if result.is_complete else 'INCOMPLETE'} (confidence: {result.confidence:.2f})")
            print(f"Reasoning: {result.reasoning}")
            
            # Check if correct
            if result.is_complete == expected_complete:
                print("✅ CORRECT")
                correct += 1
            else:
                print("❌ INCORRECT")
                
        except Exception as e:
            print(f"Error: {e}")
            print("❌ ERROR")
        
        print("-" * 80)
    
    # Summary
    print(f"\n\nSUMMARY: {correct}/{total} correct ({(correct/total)*100:.1f}%)")
    
    if correct == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - correct} tests failed")

if __name__ == "__main__":
    main()