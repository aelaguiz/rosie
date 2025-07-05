#!/usr/bin/env python3
"""Test script for voice cue detection in TopicGroupingStrategy"""

from datetime import datetime
from topic_grouping_strategy import TopicGroupingStrategy

def test_callback(text, metadata):
    """Callback to handle completed topics"""
    print(f"\n✅ TOPIC COMPLETE:")
    print(f"   Text: {text}")
    print(f"   Metadata: {metadata}")
    print()

def main():
    print("Testing TopicGroupingStrategy voice cue detection\n")
    
    # Create strategy with debug enabled
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=True
    )
    
    # Test 1: Normal text accumulation
    print("=== Test 1: Normal text accumulation ===")
    strategy.process_text("This is the first sentence.")
    strategy.process_text("This is the second sentence.")
    strategy.process_text("This is the third sentence.")
    
    # Test 2: New note voice cue
    print("\n=== Test 2: 'new note' voice cue ===")
    strategy.process_text("And here's one more thought. New note.")
    
    # Test 3: Continue after new note
    print("\n=== Test 3: Continue after new note ===")
    strategy.process_text("This is a new topic now.")
    strategy.process_text("It should be separate from the previous one.")
    
    # Test 4: Discard voice cue
    print("\n=== Test 4: 'discard that' voice cue ===")
    strategy.process_text("Actually, discard that.")
    
    # Test 5: Pause and resume
    print("\n=== Test 5: Pause and resume ===")
    strategy.process_text("Starting a new topic here.")
    strategy.process_text("Pause note.")
    print(f"Current status: {strategy.get_status()}")
    strategy.process_text("This should be ignored while paused.")
    strategy.process_text("Resume note.")
    print(f"Current status: {strategy.get_status()}")
    strategy.process_text("This should be added to the topic.")
    
    # Test 6: Flush remaining
    print("\n=== Test 6: Flush remaining content ===")
    strategy.flush("store")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()