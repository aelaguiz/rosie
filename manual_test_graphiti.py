#!/usr/bin/env python3
"""
Manual test script for Graphiti Knowledge Store
Allows interactive testing of the knowledge store
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from knowledge_store import create_knowledge_store

# Load environment variables
load_dotenv()


async def main():
    """Interactive knowledge store testing"""
    print("Graphiti Knowledge Store - Interactive Test")
    print("=" * 50)
    print("Make sure Neo4j is running: docker-compose up")
    print()
    
    # Initialize store
    os.environ['KNOWLEDGE_BACKEND'] = 'graphiti'
    store = create_knowledge_store()
    
    print("Initializing knowledge store...")
    try:
        await store.initialize()
        print("✓ Connected to Neo4j successfully\n")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        print("Make sure Neo4j is running and OPENAI_API_KEY is set")
        return
    
    # Interactive loop
    while True:
        print("\nOptions:")
        print("1. Add a voice transcription")
        print("2. Search for facts")
        print("3. Search for facts + entries")
        print("4. List recent entries")
        print("5. Exit")
        
        try:
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                # Add entry
                print("\nEnter voice transcription (or 'cancel' to go back):")
                content = input("> ").strip()
                
                if content.lower() == 'cancel':
                    continue
                
                if not content:
                    print("Content cannot be empty")
                    continue
                
                print("\nAdding entry...")
                entry = await store.add_entry(
                    content=content,
                    metadata={"source": "manual_test"}
                )
                
                print(f"✓ Added entry: {entry.id[:8]}...")
                if entry.extracted_facts:
                    print(f"  Extracted {len(entry.extracted_facts)} facts:")
                    for fact in entry.extracted_facts:
                        print(f"    - {fact.fact}")
                else:
                    print("  No facts extracted")
            
            elif choice == '2':
                # Search for facts
                query = input("\nEnter search query: ").strip()
                if not query:
                    continue
                
                print(f"\nSearching for '{query}'...")
                result = await store.search(query, limit=10)
                
                print(f"Found {result.total_results} facts:")
                for i, fact in enumerate(result.facts, 1):
                    print(f"\n{i}. {fact.fact}")
                    print(f"   From {len(fact.episode_ids)} episode(s)")
            
            elif choice == '3':
                # Search with entries
                query = input("\nEnter search query: ").strip()
                if not query:
                    continue
                
                print(f"\nSearching for '{query}' with entries...")
                result = await store.search(query, limit=10, include_entries=True)
                
                print(f"Found {result.total_results} facts and {len(result.entries)} entries")
                
                if result.facts:
                    print("\nFacts:")
                    for i, fact in enumerate(result.facts[:5], 1):
                        print(f"{i}. {fact.fact}")
                
                if result.entries:
                    print("\nEntries:")
                    for entry in result.entries[:3]:
                        print(f"\n- {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  {entry.content[:100]}...")
            
            elif choice == '4':
                # List recent entries
                print("\nFetching recent entries...")
                entries = await store.get_entries_by_date(limit=5)
                
                if entries:
                    print(f"Found {len(entries)} recent entries:")
                    for entry in entries:
                        print(f"\n- {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  {entry.content[:100]}...")
                        if 'name' in entry.metadata:
                            print(f"  Name: {entry.metadata['name']}")
                else:
                    print("No entries found")
            
            elif choice == '5':
                print("\nClosing knowledge store...")
                await store.close()
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice, please try again")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted. Closing knowledge store...")
            await store.close()
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again")


if __name__ == "__main__":
    asyncio.run(main())