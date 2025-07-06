#!/usr/bin/env python3
"""Test script for timing controls in TopicGroupingStrategy"""

import time
from datetime import datetime, timedelta
from topic_grouping_strategy import TopicGroupingStrategy


# Storage for completed topics
completed_topics = []


def test_callback(text, metadata):
    """Callback to handle completed topics"""
    print(f"\n✅ TOPIC COMPLETE:")
    print(f"   Text: {text}")
    print(f"   Duration: {metadata.get('start_ts')} to {metadata.get('end_ts')}")
    print(f"   Voice cue flags: {metadata.get('voice_cue_flags', [])}")
    print(f"   Sentence count: {metadata.get('sentence_count', 0)}")
    completed_topics.append((text, metadata))
    print()


def test_max_gap_timeout():
    """Test that topics flush after 90 seconds of inactivity"""
    print("=== Test 1: Max Gap Timeout (90s) ===")
    print("This test will take ~92 seconds to complete...")
    
    # Create strategy with shorter gap for testing (5s instead of 90s)
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=True,
        max_gap=5.0,  # 5 seconds for testing
        max_lifetime=300.0  # Keep default 5 minutes
    )
    
    try:
        # Add some text
        strategy.process_text("This is the first sentence of my topic.")
        strategy.process_text("Here's another sentence to add.")
        
        print("\nWaiting 6 seconds for max_gap timeout...")
        time.sleep(6)
        
        # Check that the topic was flushed
        assert len(completed_topics) == 1, f"Expected 1 completed topic, got {len(completed_topics)}"
        assert "max_gap_exceeded" in completed_topics[0][1]['voice_cue_flags']
        print("✓ Max gap timeout worked correctly!")
        
    finally:
        strategy.stop()
    
    # Clear for next test
    completed_topics.clear()


def test_max_lifetime_timeout():
    """Test that topics flush after 5 minutes regardless of activity"""
    print("\n=== Test 2: Max Lifetime Timeout (5min) ===")
    print("This test will take ~11 seconds to complete...")
    
    # Create strategy with shorter lifetime for testing (10s instead of 5min)
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=True,
        max_gap=90.0,  # Keep default
        max_lifetime=10.0  # 10 seconds for testing
    )
    
    try:
        # Keep adding text to prevent gap timeout
        for i in range(12):
            strategy.process_text(f"Sentence {i+1} to keep the topic active.")
            time.sleep(1)
        
        # Check that the topic was flushed due to lifetime
        assert len(completed_topics) == 1, f"Expected 1 completed topic, got {len(completed_topics)}"
        assert "max_lifetime_exceeded" in completed_topics[0][1]['voice_cue_flags']
        print("✓ Max lifetime timeout worked correctly!")
        
    finally:
        strategy.stop()
    
    # Clear for next test
    completed_topics.clear()


def test_timer_reset_on_new_text():
    """Test that the gap timer resets when new text arrives"""
    print("\n=== Test 3: Timer Reset on New Text ===")
    
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=True,
        max_gap=3.0,  # 3 seconds for testing
        max_lifetime=300.0
    )
    
    try:
        # Add text
        strategy.process_text("First sentence.")
        
        # Wait 2 seconds (less than max_gap)
        time.sleep(2)
        
        # Add more text - this should reset the gap timer
        strategy.process_text("Second sentence added before timeout.")
        
        # Wait another 2 seconds (still less than max_gap from last text)
        time.sleep(2)
        
        # Add more text again
        strategy.process_text("Third sentence, timer keeps resetting.")
        
        # Now wait for the full timeout
        time.sleep(4)
        
        # Check that the topic was flushed with all 3 sentences
        assert len(completed_topics) == 1, f"Expected 1 completed topic, got {len(completed_topics)}"
        assert completed_topics[0][1]['sentence_count'] == 3
        print("✓ Timer reset worked correctly!")
        
    finally:
        strategy.stop()
    
    # Clear for next test
    completed_topics.clear()


def test_pause_prevents_timeout():
    """Test that pausing prevents timeout from occurring"""
    print("\n=== Test 4: Pause Prevents Timeout ===")
    
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=True,
        max_gap=3.0,  # 3 seconds for testing
        max_lifetime=300.0
    )
    
    try:
        # Add text
        strategy.process_text("This topic will be paused.")
        
        # Pause the topic
        strategy.process_text("Pause note.")
        
        # Wait longer than max_gap
        print("Waiting 4 seconds (topic is paused)...")
        time.sleep(4)
        
        # Should not have flushed
        assert len(completed_topics) == 0, f"Expected 0 completed topics, got {len(completed_topics)}"
        
        # Resume
        strategy.process_text("Resume note.")
        strategy.process_text("Now we're back.")
        
        # Wait for timeout
        time.sleep(4)
        
        # Now it should flush
        assert len(completed_topics) == 1, f"Expected 1 completed topic, got {len(completed_topics)}"
        print("✓ Pause prevention worked correctly!")
        
    finally:
        strategy.stop()
    
    # Clear for next test
    completed_topics.clear()


def test_stop_flushes_content():
    """Test that stopping the strategy flushes any remaining content"""
    print("\n=== Test 5: Stop Flushes Content ===")
    
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=True,
        max_gap=90.0,
        max_lifetime=300.0
    )
    
    try:
        # Add text but don't wait for timeout
        strategy.process_text("This text should be flushed on stop.")
        strategy.process_text("Even though no timeout occurred.")
        
        # Stop should flush
        strategy.stop()
        
        # Check that content was flushed
        assert len(completed_topics) == 1, f"Expected 1 completed topic, got {len(completed_topics)}"
        assert completed_topics[0][1]['sentence_count'] == 2
        print("✓ Stop flush worked correctly!")
        
    finally:
        pass  # Already stopped
    
    # Clear for next test
    completed_topics.clear()


def test_concurrent_operations():
    """Test thread safety with concurrent text processing"""
    print("\n=== Test 6: Thread Safety ===")
    
    import threading
    
    strategy = TopicGroupingStrategy(
        on_group_complete=test_callback,
        debug=False,  # Less debug output for concurrent test
        max_gap=90.0,
        max_lifetime=300.0
    )
    
    def add_text_worker(worker_id, count):
        """Worker thread that adds text"""
        for i in range(count):
            strategy.process_text(f"Worker {worker_id} sentence {i+1}.")
            time.sleep(0.1)
    
    try:
        # Start multiple threads adding text
        threads = []
        for i in range(3):
            t = threading.Thread(target=add_text_worker, args=(i+1, 5))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Manually flush to check
        strategy.flush("store")
        
        # Should have 15 sentences (3 workers * 5 sentences each)
        assert len(completed_topics) == 1, f"Expected 1 completed topic, got {len(completed_topics)}"
        assert completed_topics[0][1]['sentence_count'] == 15
        print("✓ Thread safety worked correctly!")
        
    finally:
        strategy.stop()


def main():
    print("Testing TopicGroupingStrategy Timing Controls\n")
    
    # Run all tests
    test_max_gap_timeout()
    test_max_lifetime_timeout()
    test_timer_reset_on_new_text()
    test_pause_prevents_timeout()
    test_stop_flushes_content()
    test_concurrent_operations()
    
    print("\n✅ All timing control tests passed!")


if __name__ == "__main__":
    main()