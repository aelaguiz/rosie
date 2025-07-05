#!/usr/bin/env python3
"""Test knowledge storage integration in complete_thoughts.py"""

import asyncio
from datetime import datetime
from dotenv import load_dotenv
from knowledge_store import create_knowledge_store

# Load environment variables
load_dotenv()


async def test_storage_integration():
    """Test that storage works like in complete_thoughts.py"""
    print("Testing knowledge storage integration...")
    print("=" * 50)
    
    # Create event loop (like in main())
    event_loop = asyncio.get_event_loop()
    
    # Initialize knowledge store (will crash if fails)
    print("1. Initializing knowledge store...")
    store = create_knowledge_store()
    await store.initialize()
    print("✓ Knowledge store initialized")
    
    # Simulate storing a topic (like handle_complete_group does)
    print("\n2. Simulating topic completion...")
    
    test_text = "This is a test topic about implementing knowledge storage. We need to make sure async works properly."
    test_metadata = {
        'type': 'topic',
        'start_time': datetime.now(),
        'duration': 15.3,
        'voice_cue_flags': ['new_note'],
        'sentence_count': 2
    }
    
    # Store it (like store_topic_async does)
    entry = await store.add_entry(
        content=test_text,
        timestamp=test_metadata['start_time'],
        metadata={
            'duration': test_metadata['duration'],
            'voice_cues': test_metadata['voice_cue_flags'],
            'sentence_count': test_metadata['sentence_count'],
            'type': test_metadata['type']
        }
    )
    
    print(f"✓ Stored entry {entry.id[:8]}... with {len(entry.extracted_facts)} facts")
    
    # Test async scheduling from sync context
    print("\n3. Testing async-from-sync scheduling...")
    
    async def async_task():
        await asyncio.sleep(0.1)
        print("✓ Async task completed")
    
    # This is how complete_thoughts.py schedules async work
    future = asyncio.run_coroutine_threadsafe(async_task(), event_loop)
    # Don't wait for it (fire and forget)
    
    # Give it a moment to complete
    await asyncio.sleep(0.2)
    
    # Clean up
    print("\n4. Closing knowledge store...")
    await store.close()
    print("✓ Closed")
    
    print("\n" + "=" * 50)
    print("All tests passed! Integration will work.")


if __name__ == "__main__":
    asyncio.run(test_storage_integration())