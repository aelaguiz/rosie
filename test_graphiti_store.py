#!/usr/bin/env python3
"""
Test script for GraphitiKnowledgeStore implementation
Requires Neo4j to be running (docker-compose up)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from knowledge_store import create_knowledge_store

# Load environment variables
load_dotenv()


async def test_graphiti_store():
    """Test the Graphiti knowledge store implementation"""
    print("=== Testing Graphiti Knowledge Store ===")
    print("Make sure Neo4j is running: docker-compose up")
    print()
    
    # Set to use Graphiti backend
    os.environ['KNOWLEDGE_BACKEND'] = 'graphiti'
    
    try:
        # Create store
        store = create_knowledge_store()
        print("✓ Created Graphiti store")
        
        # Initialize (connects to Neo4j)
        print("Initializing (connecting to Neo4j)...")
        await store.initialize()
        print("✓ Initialized store and built Neo4j indices")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Please install: pip install graphiti-core")
        return
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        print("Make sure Neo4j is running (docker-compose up)")
        return
    
    # Add some test entries
    print("\n--- Adding test entries ---")
    
    try:
        entry1 = await store.add_entry(
            content="Today we discussed the new project timeline. The deadline is February 15th.",
            metadata={"duration": 45.2, "voice_cues": ["new topic"]}
        )
        print(f"✓ Added entry 1: {entry1.id[:8]}...")
        print(f"  Extracted {len(entry1.extracted_facts)} facts:")
        for fact in entry1.extracted_facts:
            print(f"    - {fact.fact}")
        
        await asyncio.sleep(1)  # Small delay
        
        entry2 = await store.add_entry(
            content="Sarah will be joining the team as our ML engineer. She has 5 years experience with transformer models and will help with the NLP components.",
            metadata={"duration": 30.5}
        )
        print(f"\n✓ Added entry 2: {entry2.id[:8]}...")
        print(f"  Extracted {len(entry2.extracted_facts)} facts:")
        for fact in entry2.extracted_facts:
            print(f"    - {fact.fact}")
        
        await asyncio.sleep(1)
        
        entry3 = await store.add_entry(
            content="Budget meeting notes: The budget was increased by 20 percent to accommodate new hires. John mentioned this covers Sarah's position.",
            metadata={"duration": 120.0}
        )
        print(f"\n✓ Added entry 3: {entry3.id[:8]}...")
        print(f"  Extracted {len(entry3.extracted_facts)} facts")
        
    except Exception as e:
        print(f"✗ Failed to add entries: {e}")
        return
    
    # Test search (returns facts)
    print("\n--- Testing fact search ---")
    
    try:
        # Search for facts about Sarah
        result = await store.search("Sarah ML engineer", limit=5)
        print(f"\nSearch 'Sarah ML engineer': {result.total_results} facts")
        for i, fact in enumerate(result.facts, 1):
            print(f"  {i}. {fact.fact}")
            print(f"     Episodes: {len(fact.episode_ids)}")
        
        # Search with entries included
        print("\n--- Testing search with entries ---")
        result = await store.search("project timeline February", include_entries=True)
        print(f"\nSearch 'project timeline February': {result.total_results} facts, {len(result.entries)} entries")
        
        if result.facts:
            print("Facts found:")
            for fact in result.facts[:3]:
                print(f"  - {fact.fact}")
        
        if result.entries:
            print("\nEntries retrieved:")
            for entry in result.entries:
                print(f"  - {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {entry.content[:60]}...")
        
    except Exception as e:
        print(f"✗ Search failed: {e}")
    
    # Test get by ID
    print("\n--- Testing get by ID ---")
    try:
        retrieved = await store.get_entry(entry1.id)
        if retrieved:
            print(f"✓ Retrieved entry by ID: {retrieved.content[:60]}...")
            print(f"  Metadata: {retrieved.metadata}")
        else:
            print("✗ Failed to retrieve entry")
    except Exception as e:
        print(f"✗ Get by ID failed: {e}")
    
    # Test get by date
    print("\n--- Testing get by date ---")
    try:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        
        entries = await store.get_entries_by_date(start_date=yesterday, limit=5)
        print(f"Entries since yesterday: {len(entries)}")
        for entry in entries:
            print(f"  - {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {entry.content[:50]}...")
            print(f"    Metadata: {entry.metadata.get('name', 'No name')}")
    except Exception as e:
        print(f"✗ Get by date failed: {e}")
    
    # Test cross-episode fact linking
    print("\n--- Testing cross-episode relationships ---")
    try:
        # Add another entry mentioning Sarah
        entry4 = await store.add_entry(
            content="Sarah started working on the transformer implementation. She's collaborating with John on the architecture.",
            metadata={"duration": 25.0}
        )
        print(f"✓ Added entry 4 mentioning Sarah and John")
        
        # Search should find facts across multiple episodes
        result = await store.search("Sarah John collaboration", limit=10)
        print(f"\nSearch 'Sarah John collaboration': {result.total_results} facts")
        
        # Group facts by episode
        episode_fact_count = {}
        for fact in result.facts:
            for ep_id in fact.episode_ids:
                episode_fact_count[ep_id] = episode_fact_count.get(ep_id, 0) + 1
        
        print(f"Facts distributed across {len(episode_fact_count)} episodes")
        
    except Exception as e:
        print(f"✗ Cross-episode test failed: {e}")
    
    # Clean up
    print("\n--- Cleaning up ---")
    await store.close()
    print("✓ Store closed successfully")


async def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n\n=== Testing Edge Cases ===")
    
    os.environ['KNOWLEDGE_BACKEND'] = 'graphiti'
    store = create_knowledge_store()
    await store.initialize()
    
    # Test empty content
    print("\n1. Testing empty content:")
    try:
        result = await store.add_entry("")
        print("  ✗ Empty content accepted (unexpected)")
    except Exception as e:
        print(f"  ✓ Empty content rejected: {type(e).__name__}")
    
    # Test very short content
    print("\n2. Testing very short content:")
    try:
        result = await store.add_entry("Hello world")
        print(f"  ✓ Short content accepted")
        print(f"  Extracted {len(result.extracted_facts)} facts")
    except Exception as e:
        print(f"  ✗ Short content rejected: {e}")
    
    # Test search with no results
    print("\n3. Testing search with no matches:")
    result = await store.search("xyzabc123notfound", limit=5)
    print(f"  Found {result.total_results} results (expected 0)")
    
    # Test get non-existent entry
    print("\n4. Testing get non-existent entry:")
    fake_id = "00000000-0000-0000-0000-000000000000"
    entry = await store.get_entry(fake_id)
    print(f"  Result: {'None' if entry is None else 'Found (unexpected)'}")
    
    await store.close()


async def main():
    """Run all tests"""
    print("Graphiti Knowledge Store Test")
    print("=" * 50)
    
    # Check if graphiti-core is installed
    try:
        import graphiti_core
        print("✓ graphiti-core is installed")
    except ImportError:
        print("✗ graphiti-core not installed")
        print("Please run: pip install graphiti-core")
        sys.exit(1)
    
    # Run main tests
    await test_graphiti_store()
    
    # Run edge case tests
    await test_edge_cases()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())