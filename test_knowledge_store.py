#!/usr/bin/env python3
"""
Test script for KnowledgeStore abstraction
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from knowledge_store import create_knowledge_store, KnowledgeBackend


async def test_mock_store():
    """Test the mock knowledge store implementation"""
    print("=== Testing Mock Knowledge Store ===")
    
    # Force mock backend for testing
    os.environ['KNOWLEDGE_BACKEND'] = 'mock'
    
    # Create store
    store = create_knowledge_store()
    print("✓ Created mock store")
    
    # Initialize
    await store.initialize()
    print("✓ Initialized store")
    
    # Add some test entries
    print("\n--- Adding test entries ---")
    
    entry1 = await store.add_entry(
        content="Today we discussed the new project timeline. The deadline is February.",
        metadata={"duration": 45.2, "voice_cues": ["new topic"]}
    )
    print(f"✓ Added entry 1: {entry1.id[:8]}...")
    
    await asyncio.sleep(0.1)  # Small delay to ensure different timestamps
    
    entry2 = await store.add_entry(
        content="Sarah will be joining the team as our ML engineer. She has transformer experience.",
        metadata={"duration": 30.5}
    )
    print(f"✓ Added entry 2: {entry2.id[:8]}...")
    
    await asyncio.sleep(0.1)
    
    entry3 = await store.add_entry(
        content="Budget meeting notes: increased by 20 percent for new hires.",
        metadata={"duration": 120.0}
    )
    print(f"✓ Added entry 3: {entry3.id[:8]}...")
    
    # Test search
    print("\n--- Testing search ---")
    
    result = await store.search("Sarah", include_entries=True)
    print(f"Search for 'Sarah': {result.total_results} results")
    if result.entries:
        print(f"  - Found: {result.entries[0].content[:50]}...")
    
    result = await store.search("timeline project", include_entries=True)
    print(f"Search for 'timeline project': {result.total_results} results")
    
    # Test get by ID
    print("\n--- Testing get by ID ---")
    retrieved = await store.get_entry(entry1.id)
    if retrieved:
        print(f"✓ Retrieved entry by ID: {retrieved.content[:50]}...")
    else:
        print("✗ Failed to retrieve entry")
    
    # Test get by date
    print("\n--- Testing get by date ---")
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    entries = await store.get_entries_by_date(start_date=yesterday, limit=5)
    print(f"Entries since yesterday: {len(entries)}")
    for entry in entries:
        print(f"  - {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {entry.content[:40]}...")
    
    # Test metadata update
    print("\n--- Testing metadata update ---")
    success = await store.update_entry_metadata(entry1.id, {"reviewed": True})
    print(f"Update metadata: {'✓ Success' if success else '✗ Failed'}")
    
    # Test delete
    print("\n--- Testing delete ---")
    success = await store.delete_entry(entry3.id)
    print(f"Delete entry: {'✓ Success' if success else '✗ Failed'}")
    
    # Verify deletion
    deleted = await store.get_entry(entry3.id)
    print(f"Verify deletion: {'✓ Entry gone' if deleted is None else '✗ Entry still exists'}")
    
    # Clean up
    await store.close()
    print("\n✓ Store closed successfully")


async def test_factory():
    """Test the factory function"""
    print("\n=== Testing Factory Function ===")
    
    # Test with environment variable
    os.environ['KNOWLEDGE_BACKEND'] = 'mock'
    store = create_knowledge_store()
    print("✓ Created store from env var")
    
    # Test with explicit backend
    store = create_knowledge_store('mock')
    print("✓ Created store with explicit backend")
    
    # Test unsupported backend
    try:
        store = create_knowledge_store('unsupported')
        print("✗ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
    
    # Test GraphitiKnowledgeStore (not implemented yet)
    try:
        store = create_knowledge_store('graphiti')
        print("✗ Should have raised NotImplementedError")
    except NotImplementedError as e:
        print(f"✓ Correctly raised NotImplementedError: {e}")


async def main():
    """Run all tests"""
    print("Knowledge Store Abstraction Test")
    print("=" * 50)
    
    await test_mock_store()
    await test_factory()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())