#!/usr/bin/env python3
"""
Explore Graphiti's actual behavior with voice transcription data.
This will help us understand how to design our abstraction layer.
"""

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def explore_graphiti():
    """Run exploration tests to understand Graphiti's behavior"""
    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
    except ImportError:
        print("ERROR: graphiti-core not installed")
        print("Please install: pip install graphiti-core")
        return
    
    # Initialize Graphiti
    print("=== Initializing Graphiti ===")
    try:
        graphiti = Graphiti(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD', 'rosie_local_password')
        )
        print("✓ Created Graphiti client")
        
        
        # Build indices (only needs to run once)
        await graphiti.build_indices_and_constraints()
        print("✓ Built Neo4j indices and constraints")
    except Exception as e:
        print(f"✗ Failed to initialize Graphiti: {e}")
        print("Make sure Neo4j is running (docker-compose up)")
        return
    
    # Test 1: Add voice transcription as episode
    print("\n=== Test 1: Adding Voice Transcription ===")
    test_transcript = """
    We discussed the project timeline today. The deadline has been moved to February 
    because of the holidays. Sarah will be joining the team as our new ML engineer. 
    She has experience with transformer models and will help with the NLP components.
    John mentioned that the budget was increased by 20 percent to accommodate the new hire.
    """
    
    try:
        episode_result = await graphiti.add_episode(
            name="Voice Topic 2025-01-05 14:30:00",
            episode_body=test_transcript.strip(),
            source=EpisodeType.text,
            source_description="voice transcription",
            reference_time=datetime.now(timezone.utc),
            group_id="voice_transcriptions"
        )
        
        print(f"✓ Episode UUID: {episode_result.episode.uuid}")
        print(f"✓ Episode Name: {episode_result.episode.name}")
        print(f"\nExtracted {len(episode_result.nodes)} Entities:")
        for node in episode_result.nodes:
            print(f"  - {node.name} (labels: {node.labels})")
            
        print(f"\nExtracted {len(episode_result.edges)} Facts:")
        for i, edge in enumerate(episode_result.edges, 1):
            print(f"  {i}. {edge.fact}")
            
        episode_uuid = episode_result.episode.uuid
        
    except Exception as e:
        print(f"✗ Failed to add episode: {e}")
        return
    
    # Test 2: Basic search() - returns EntityEdges (facts)
    print("\n=== Test 2: Basic Search (returns facts) ===")
    try:
        results = await graphiti.search(
            "project timeline deadline", 
            group_ids=["voice_transcriptions"],
            num_results=10
        )
        
        print(f"Found {len(results)} facts:")
        for i, edge in enumerate(results, 1):
            print(f"\n{i}. Fact: {edge.fact}")
            print(f"   Type: {type(edge).__name__}")
            print(f"   Valid at: {edge.valid_at}")
            print(f"   Source UUID: {edge.source_node_uuid}")
            print(f"   Target UUID: {edge.target_node_uuid}")
            print(f"   Has source_node object: {hasattr(edge, 'source_node')}")
            print(f"   Episodes: {edge.episodes}")
            
    except Exception as e:
        print(f"✗ Search failed: {e}")
    
    # Test 3: Advanced search_() - returns SearchResults with edges, nodes, episodes
    print("\n=== Test 3: Advanced Search (returns full results) ===")
    try:
        from graphiti_core.search.search_config_recipes import (
            COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
            EDGE_HYBRID_SEARCH_RRF
        )
        
        search_results = await graphiti.search_(
            query="Sarah ML engineer transformer",
            config=EDGE_HYBRID_SEARCH_RRF,
            group_ids=["voice_transcriptions"]
        )
        
        print(f"SearchResults object contains:")
        print(f"  - {len(search_results.edges)} edges (facts)")
        print(f"  - {len(search_results.nodes)} nodes (entities)")
        print(f"  - {len(search_results.episodes)} episodes")
        print(f"  - {len(search_results.communities)} communities")
        
        if search_results.nodes:
            print("\nSample Nodes:")
            for node in search_results.nodes[:3]:
                print(f"  - {node.name} (uuid: {node.uuid})")
                
        if search_results.episodes:
            print("\nEpisodes returned in search:")
            for ep in search_results.episodes:
                print(f"  - {ep.name}")
                print(f"    Content preview: {ep.content[:100]}...")
                
    except Exception as e:
        print(f"✗ Advanced search failed: {e}")
    
    # Test 4: Retrieve episodes by date
    print("\n=== Test 4: Retrieve Episodes by Date ===")
    try:
        episodes = await graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc),
            last_n=10,
            group_ids=["voice_transcriptions"]
        )
        
        print(f"Retrieved {len(episodes)} episodes:")
        for ep in episodes:
            print(f"\n- Name: {ep.name}")
            print(f"  UUID: {ep.uuid}")
            print(f"  Created: {ep.created_at}")
            print(f"  Valid at: {ep.valid_at}")
            print(f"  Content preview: {ep.content[:100]}...")
            print(f"  Entity edges: {len(ep.entity_edges)} edges referenced")
            
    except Exception as e:
        print(f"✗ Episode retrieval failed: {e}")
    
    # Test 5: Add another episode to test relationships
    print("\n=== Test 5: Adding Related Episode ===")
    try:
        related_transcript = """
        Sarah started working on the transformer model implementation today.
        She's collaborating with John on the architecture. The project timeline
        looks good for the February deadline.
        """
        
        episode_result2 = await graphiti.add_episode(
            name="Voice Topic 2025-01-06 10:00:00",
            episode_body=related_transcript.strip(),
            source=EpisodeType.text,
            source_description="voice transcription",
            reference_time=datetime.now(timezone.utc) + timedelta(days=1),
            group_id="voice_transcriptions"
        )
        
        print(f"✓ Added second episode: {episode_result2.episode.uuid}")
        print(f"  Extracted {len(episode_result2.edges)} new facts")
        
    except Exception as e:
        print(f"✗ Failed to add related episode: {e}")
    
    # Test 6: Search across multiple episodes
    print("\n=== Test 6: Search Across Episodes ===")
    try:
        results = await graphiti.search(
            "Sarah transformer February", 
            group_ids=["voice_transcriptions"],
            num_results=20
        )
        
        print(f"Found {len(results)} facts across episodes:")
        
        # Group facts by episode
        facts_by_episode = {}
        for edge in results:
            for ep_id in edge.episodes:
                if ep_id not in facts_by_episode:
                    facts_by_episode[ep_id] = []
                facts_by_episode[ep_id].append(edge.fact)
        
        for ep_id, facts in facts_by_episode.items():
            print(f"\nEpisode {ep_id[:8]}...:")
            for fact in facts[:3]:  # Show first 3 facts
                print(f"  - {fact}")
                
    except Exception as e:
        print(f"✗ Cross-episode search failed: {e}")
    
    # Test 7: Get specific episode by UUID
    print("\n=== Test 7: Get Specific Episode ===")
    try:
        # Try to get the episode we created
        from graphiti_core.nodes import EpisodicNode
        
        retrieved_episodes = await EpisodicNode.get_by_uuids(
            graphiti.driver, 
            [episode_uuid]
        )
        
        if retrieved_episodes:
            ep = retrieved_episodes[0]
            print(f"✓ Retrieved episode by UUID:")
            print(f"  Name: {ep.name}")
            print(f"  Content: {ep.content[:200]}...")
            print(f"  Has {len(ep.entity_edges)} entity edge references")
        else:
            print("✗ Could not retrieve episode by UUID")
            
    except Exception as e:
        print(f"✗ Failed to get episode by UUID: {e}")
    
    # Summary of findings
    print("\n=== SUMMARY OF FINDINGS ===")
    print("""
1. Episodes store the original content (voice transcriptions)
2. Graphiti automatically extracts:
   - Entities (people, concepts, etc.) as nodes
   - Facts/relationships between entities as edges
3. Basic search() returns EntityEdges (facts), NOT episodes
4. Advanced search_() returns SearchResults with edges, nodes, and episodes
5. Episodes can be retrieved by date range or UUID
6. Facts link back to source episodes via episode_ids
7. Multiple episodes can share entities (deduplication happens)

Key insight: Our abstraction needs to handle both:
- Storage/retrieval of original content (episodes)
- Search that primarily returns extracted facts (edges)
""")

async def test_empty_and_edge_cases():
    """Test edge cases to understand Graphiti's behavior"""
    print("\n=== EDGE CASE TESTS ===")
    
    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
        
        graphiti = Graphiti(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USER', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD', 'rosie_local_password')
        )
        
        # Test empty transcript
        print("\n1. Testing empty transcript:")
        try:
            result = await graphiti.add_episode(
                name="Empty test",
                episode_body="",
                source=EpisodeType.text,
                source_description="test",
                reference_time=datetime.now(timezone.utc),
                group_id="test"
            )
            print("  ✓ Empty episode accepted")
        except Exception as e:
            print(f"  ✗ Empty episode rejected: {e}")
        
        # Test very short transcript
        print("\n2. Testing very short transcript:")
        result = await graphiti.add_episode(
            name="Short test",
            episode_body="Hello world",
            source=EpisodeType.text,
            source_description="test",
            reference_time=datetime.now(timezone.utc),
            group_id="test"
        )
        print(f"  ✓ Short episode created")
        print(f"  Extracted {len(result.nodes)} nodes, {len(result.edges)} edges")
        
        # Test search with no results
        print("\n3. Testing search with no matches:")
        results = await graphiti.search(
            "xyzabc123notfound",
            group_ids=["test"],
            num_results=10
        )
        print(f"  Search returned {len(results)} results (expected 0)")
        
    except Exception as e:
        print(f"Edge case testing failed: {e}")

if __name__ == "__main__":
    print("Graphiti Exploration Script")
    print("=" * 50)
    print("Make sure Neo4j is running: docker-compose up")
    print("=" * 50)
    
    # Run main exploration
    asyncio.run(explore_graphiti())
    
    # Run edge case tests
    asyncio.run(test_empty_and_edge_cases())