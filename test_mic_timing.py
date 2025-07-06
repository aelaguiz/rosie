#!/usr/bin/env python3
"""Quick test of timing controls with microphone input"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import complete_thoughts to test the full integration
if __name__ == "__main__":
    # Modify command line args to use topic strategy with short timeouts
    sys.argv = [
        'complete_thoughts.py',
        '--strategy', 'topic',
        '--model', 'tiny'
    ]
    
    # Temporarily modify the TopicGroupingStrategy defaults for testing
    import topic_grouping_strategy
    
    # Save original __init__
    original_init = topic_grouping_strategy.TopicGroupingStrategy.__init__
    
    # Create wrapper that uses shorter timeouts
    def test_init(self, on_group_complete=None, debug=False,
                  short_gap=0.5, max_gap=90.0, max_lifetime=300.0):
        # Use much shorter timeouts for testing
        original_init(self, on_group_complete, debug,
                     short_gap=0.5,
                     max_gap=10.0,    # 10 seconds instead of 90
                     max_lifetime=30.0)  # 30 seconds instead of 5 minutes
        print("\n⚡ TESTING MODE: Using short timeouts (10s gap, 30s lifetime)")
    
    # Monkey patch for testing
    topic_grouping_strategy.TopicGroupingStrategy.__init__ = test_init
    
    print("=" * 60)
    print("TIMING CONTROLS TEST")
    print("=" * 60)
    print("\nThis test uses shortened timeouts:")
    print("- Max gap: 10 seconds (normally 90s)")
    print("- Max lifetime: 30 seconds (normally 5 min)")
    print("\nTry these scenarios:")
    print("1. Speak, then stay silent for 10+ seconds → auto-flush")
    print("2. Keep talking for 30+ seconds → auto-flush") 
    print("3. Say 'pause note', wait, then 'resume note'")
    print("4. Say 'new note' to manually split topics")
    print("=" * 60)
    
    # Import and run the main app
    from complete_thoughts import main
    main()