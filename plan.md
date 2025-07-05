# Voice Transcription with Topic Grouping

## North Stars & Principles

### 🌟 Guiding Principles
1. **Long-Term Elegance Over Short-Term Hacks**
2. **Simplify, Simplify, Simplify**  
3. **No Heuristics - Use LLM Intelligence**
4. **Single Source of Truth**

---

## 🚧 Implementation Status
> **🚀 CURRENT:** *Phase 7 – Knowledge Storage Abstraction*  
> **🔜 NEXT:** *Phase 7a – Design KnowledgeStore Interface*

## Executive Summary
Replace thought-level grouping with topic/time/voice-command based approach. Uses GPT-4o's native **tool calling mode** (not JSON mode) to detect voice commands naturally without heuristics. Tool calling achieved 92% accuracy in tests vs 78% for JSON mode. Time-based buffering (5-10s) reduces API calls while maintaining good UX.

## Architecture – Before vs. After
|                | **Before** | **After** |
| -------------- | ---------- | --------- |
| Grouping | ThoughtCompletionDetector (hardcoded) | GroupingStrategy abstraction |
| Commands | None | GPT-4o tool calling mode (92% accuracy) |
| Detection | String matching | Tool definitions + natural language |
| Buffering | None | 5-10s buffer before API calls |
| State | Simple text accumulation | Buffer with timestamps + status |
| Output | Console only | Console + Graphiti knowledge graph |

---

## Milestones & Phases

### ✅ Milestone 1 – Core Implementation (COMPLETE)
* [x] **Phase 3** – Core Buffer Management in TopicGroupingStrategy
* [x] **Phase 4** – Basic Voice Cue Detection (string matching)
* [x] **Phase 5** – Timing Controls (90s gap, 5min lifetime)

### ✅ Milestone 2 – GPT-4o Integration (COMPLETE)
* [x] **Phase 6** – GPT-4o Tool Calling for Voice Commands

### 🔄 Milestone 3 – Knowledge Storage Abstraction (IN PROGRESS)
* [ ] **Phase 7** – Knowledge Storage Abstraction Layer
  * [ ] **Phase 7a** – Design KnowledgeStore Interface
  * [ ] **Phase 7b** – Implement GraphitiKnowledgeStore Driver
  * [ ] **Phase 7c** – Test Abstraction Independently
  * **Success Criteria**: Working abstraction with Graphiti backend, tested independently

### ⬜ Milestone 4 – Integration & Retrieval
* [ ] **Phase 8** – Integrate Knowledge Storage
  * [ ] **Phase 8a** – Initialize Knowledge Store in complete_thoughts.py
  * [ ] **Phase 8b** – Store Topics Using Abstraction
  * **Success Criteria**: Topics stored in Neo4j via abstraction layer
* [ ] **Phase 9** – Query Knowledge Tool
  * [ ] Create CLI tool using KnowledgeStore abstraction
  * [ ] Support multiple backends in the future
  * **Success Criteria**: Can search and retrieve past topics with relevant results

---

## Phase 6 – GPT-4o Tool Calling Mode (Not JSON Mode)

### Decision: Tool Calling Mode
Based on test results, we're using GPT-4o's **tool calling mode** (not JSON mode):
- **Tool mode accuracy: 92%** vs JSON mode: 78%
- Tool mode handles natural language variations better
- No need for complex prompts or output parsing

### Architecture
```
Whisper → Buffer (5-10s) → GPT-4o Tool Calling → Execute Actions
                              ↓
                    Tool definitions + System prompt
```

### Implementation Steps
* [ ] Remove `_detect_voice_cue()` string matching method
* [ ] Add async `_check_for_commands()` method using GPT-4o tool calling
* [ ] Define tools for GPT-4o with proper descriptions
* [ ] Modify timer thread to check periodically (not just for timeouts)
* [ ] Add OpenAI client initialization with API key

### GPT-4o Tool Definitions
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "new_topic",
            "description": "Start a new topic or note when the user wants to change subjects",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discard_last",
            "description": "Delete or remove the previously saved topic",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_current",
            "description": "Save the current topic immediately",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# System prompt (tested and refined)
system_prompt = """You are a voice command detector. Analyze the transcribed speech 
and determine if the user is issuing a command to manage their notes.

Commands you should detect:
- Starting a new topic/note (e.g., "new topic", "start fresh", "next subject")
- Discarding the last saved topic (e.g., "delete that", "remove the last one")
- Saving the current topic (e.g., "save this", "keep that")

Only call a tool if you're confident the user intended a command."""
```

### Test Results Summary
```
Tool Calling Mode Performance:
- Overall accuracy: 92% (46/50 test cases)
- New topic detection: 95%
- Discard detection: 90%
- Save detection: 90%
- False positive rate: 2%

Failed cases:
- "scratch that thought" → missed (too ambiguous)
- "nevermind what I just said" → missed
- "I think we should start over" → false positive
- "let's begin with a new approach" → false positive
```

### Timing Strategy
- Check after 5 seconds of accumulated speech
- Check after 2+ second pause in speech
- Check if buffer exceeds 100 words
- Keep existing 90s gap / 5min lifetime timeouts

### Implementation Details
```python
async def _check_for_commands(self, text: str) -> Optional[str]:
    """Check for voice commands using GPT-4o tool calling"""
    try:
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0.1  # Low temperature for consistency
        )
        
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            return tool_call.function.name
            
        return None
    except Exception as e:
        logger.error(f"GPT-4o command detection failed: {e}")
        return None
```

### Success Criteria
* Natural language commands work reliably (>90% accuracy)
* Latency under 10s for command execution
* Cost under $0.01 per minute of speech
* Graceful fallback if API unavailable

---

## Phase 7 – Knowledge Storage Abstraction Layer

### Why an Abstraction Layer?
- **Future Flexibility**: Support multiple backends (Graphiti, vector DBs, JSONL, etc.)
- **Clean Architecture**: Separate storage concerns from business logic
- **Testability**: Test storage independently from voice transcription
- **Consistent Interface**: Same API regardless of backend
- **Follows GroupingStrategy Pattern**: Proven abstraction approach

### Design Principles
- Simple, minimal interface (add, search, get)
- Async-first for scalability
- Backend-agnostic data models
- Error handling built-in
- Configuration via environment variables

### Phase 7a – Design KnowledgeStore Interface

#### Implementation Steps
* [ ] Create knowledge_store.py with abstract base class:
  ```python
  from abc import ABC, abstractmethod
  from typing import List, Dict, Any, Optional
  from datetime import datetime
  from dataclasses import dataclass
  
  @dataclass
  class KnowledgeEntry:
      """Backend-agnostic knowledge entry"""
      id: Optional[str] = None
      content: str = ""
      timestamp: datetime = None
      metadata: Dict[str, Any] = None
      group_id: str = "default"
  
  @dataclass
  class SearchResult:
      """Backend-agnostic search result"""
      entry: KnowledgeEntry
      score: float = 1.0
      facts: List[str] = None
      relationships: List[Dict[str, Any]] = None
  
  class KnowledgeStore(ABC):
      """Abstract interface for knowledge storage backends"""
      
      @abstractmethod
      async def initialize(self) -> None:
          """Initialize the storage backend"""
          pass
      
      @abstractmethod
      async def add_entry(self, entry: KnowledgeEntry) -> str:
          """Add a knowledge entry and return its ID"""
          pass
      
      @abstractmethod
      async def search(self, query: str, limit: int = 10, 
                      group_id: Optional[str] = None) -> List[SearchResult]:
          """Search for relevant entries"""
          pass
      
      @abstractmethod
      async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
          """Retrieve a specific entry by ID"""
          pass
      
      @abstractmethod
      async def close(self) -> None:
          """Clean up resources"""
          pass
  ```

* [ ] Create factory function for backend selection:
  ```python
  def create_knowledge_store(backend: str = None) -> KnowledgeStore:
      """Factory to create appropriate knowledge store backend"""
      backend = backend or os.getenv('KNOWLEDGE_BACKEND', 'graphiti')
      
      if backend == 'graphiti':
          from .graphiti_store import GraphitiKnowledgeStore
          return GraphitiKnowledgeStore()
      else:
          raise ValueError(f"Unknown backend: {backend}")
  ```

#### Test Plan
* Verify abstract methods are properly defined
* Test factory function with different backends
* Ensure data classes work correctly

### Phase 7b – Implement GraphitiKnowledgeStore Driver

#### Implementation Steps
* [ ] Create graphiti_store.py implementing the KnowledgeStore interface:
  ```python
  import os
  import logging
  from typing import List, Optional
  from graphiti_core import Graphiti
  from graphiti_core.nodes import EpisodeType
  from .knowledge_store import KnowledgeStore, KnowledgeEntry, SearchResult
  
  logger = logging.getLogger(__name__)
  
  class GraphitiKnowledgeStore(KnowledgeStore):
      """Graphiti backend for knowledge storage"""
      
      def __init__(self):
          self.graphiti = None
          self.group_id = "voice_transcriptions"
      
      async def initialize(self) -> None:
          """Initialize Graphiti client and Neo4j indices"""
          self.graphiti = Graphiti(
              uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
              user=os.getenv('NEO4J_USER', 'neo4j'),
              password=os.getenv('NEO4J_PASSWORD', 'rosie_local_password')
          )
          # Build indices (only needs to run once)
          await self.graphiti.build_indices_and_constraints()
          logger.info("Graphiti knowledge store initialized")
      
      async def add_entry(self, entry: KnowledgeEntry) -> str:
          """Add entry as Graphiti episode"""
          try:
              result = await self.graphiti.add_episode(
                  name=f"Voice Topic {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                  episode_body=entry.content,
                  source=EpisodeType.text,
                  source_description="voice transcription topic",
                  reference_time=entry.timestamp,
                  group_id=entry.group_id or self.group_id
              )
              return result.episode.uuid
          except Exception as e:
              logger.error(f"Failed to add entry to Graphiti: {e}")
              raise
      
      async def search(self, query: str, limit: int = 10,
                      group_id: Optional[str] = None) -> List[SearchResult]:
          """Search using Graphiti's hybrid search"""
          try:
              edges = await self.graphiti.search(
                  query=query,
                  group_ids=[group_id or self.group_id],
                  num_results=limit
              )
              
              results = []
              for edge in edges:
                  # Convert Graphiti edge to our SearchResult
                  entry = KnowledgeEntry(
                      id=edge.source_node_uuid,
                      content=edge.source_node.name,
                      timestamp=edge.valid_at,
                      group_id=group_id or self.group_id
                  )
                  result = SearchResult(
                      entry=entry,
                      score=1.0,  # Graphiti doesn't expose scores
                      facts=[edge.fact],
                      relationships=[{
                          "type": "relates_to",
                          "target": edge.target_node.name if edge.target_node else None
                      }]
                  )
                  results.append(result)
              
              return results
          except Exception as e:
              logger.error(f"Search failed: {e}")
              return []
      
      async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
          """Retrieve specific episode by UUID"""
          # Graphiti doesn't have a direct get_episode method
          # Would need to implement using Neo4j query
          logger.warning("get_entry not fully implemented for Graphiti")
          return None
      
      async def close(self) -> None:
          """Close Graphiti connection"""
          if self.graphiti and hasattr(self.graphiti.driver, 'close'):
              await self.graphiti.driver.close()
  ```

* [ ] Add graphiti-core to requirements.txt
* [ ] Add error handling and retry logic
* [ ] Configure logging for debugging

#### Test Plan
* Unit tests mocking Graphiti client
* Integration test with real Neo4j:
  - Initialize store
  - Add test entries
  - Search for entries
  - Verify results format
* Test error scenarios

### Phase 7c – Test Abstraction Independently

#### Implementation Steps
* [ ] Create test_knowledge_store.py:
  ```python
  import asyncio
  import pytest
  from datetime import datetime
  from knowledge_store import KnowledgeEntry, create_knowledge_store
  
  @pytest.mark.asyncio
  async def test_graphiti_store_lifecycle():
      """Test basic lifecycle of Graphiti knowledge store"""
      # Create store
      store = create_knowledge_store('graphiti')
      
      # Initialize
      await store.initialize()
      
      # Add entry
      entry = KnowledgeEntry(
          content="This is a test topic about project planning",
          timestamp=datetime.now(),
          metadata={"source": "test"},
          group_id="test_group"
      )
      entry_id = await store.add_entry(entry)
      assert entry_id is not None
      
      # Search for it
      results = await store.search("project planning", limit=5)
      assert len(results) > 0
      assert "project" in results[0].entry.content.lower()
      
      # Clean up
      await store.close()
  
  async def main():
      """Manual test script"""
      print("Testing Knowledge Store Abstraction...")
      
      # Test with Neo4j running
      store = create_knowledge_store('graphiti')
      try:
          await store.initialize()
          print("✓ Store initialized")
          
          # Add test entries
          for i in range(3):
              entry = KnowledgeEntry(
                  content=f"Test topic {i}: Discussion about AI and machine learning",
                  timestamp=datetime.now(),
                  metadata={"test_id": i}
              )
              entry_id = await store.add_entry(entry)
              print(f"✓ Added entry {i}: {entry_id}")
          
          # Search test
          results = await store.search("machine learning", limit=10)
          print(f"✓ Found {len(results)} results")
          for r in results:
              print(f"  - {r.entry.content[:50]}...")
              if r.facts:
                  print(f"    Facts: {r.facts}")
      
      finally:
          await store.close()
          print("✓ Store closed")
  
  if __name__ == "__main__":
      asyncio.run(main())
  ```

* [ ] Create mock_knowledge_store.py for testing without Neo4j:
  ```python
  class MockKnowledgeStore(KnowledgeStore):
      """In-memory mock for testing"""
      def __init__(self):
          self.entries = {}
          self.counter = 0
      
      async def initialize(self):
          pass
      
      async def add_entry(self, entry):
          self.counter += 1
          entry_id = f"mock_{self.counter}"
          self.entries[entry_id] = entry
          return entry_id
      
      # ... implement other methods
  ```

* [ ] Add to factory function for testing

#### Test Plan
* Run test script with Neo4j running
* Verify entries are stored and searchable
* Test with mock store for unit tests
* Benchmark performance (add/search times)

### Success Criteria
* Abstraction works with real Graphiti/Neo4j
* Clean separation of concerns
* Easy to add new backends
* Performance acceptable (<100ms for add, <500ms for search)

### Future Backend Options
With this abstraction in place, we can easily add:
- **JSONLKnowledgeStore** - Simple file-based storage
- **ChromaKnowledgeStore** - Vector database for semantic search
- **PostgresKnowledgeStore** - Traditional SQL with full-text search
- **ElasticsearchKnowledgeStore** - Scalable search infrastructure

Each backend would implement the same KnowledgeStore interface, making them interchangeable.

### Docker Setup for Neo4j
```yaml
# docker-compose.yml for local development
services:
  neo4j:
    image: neo4j:5.26.2
    ports:
      - "7474:7474"  # Web interface
      - "7687:7687"  # Bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/localpassword
    volumes:
      - ./neo4j_data:/data
```

---

## Phase 8 – Integrate Knowledge Storage

### Phase 8a – Initialize Knowledge Store in complete_thoughts.py

#### Implementation Steps
* [ ] Add knowledge store imports:
  ```python
  from knowledge_store import create_knowledge_store, KnowledgeEntry
  ```

* [ ] Initialize store on startup:
  ```python
  # Global knowledge store instance
  knowledge_store = None
  
  async def init_knowledge_store():
      """Initialize knowledge store on startup"""
      global knowledge_store
      try:
          knowledge_store = create_knowledge_store()
          await knowledge_store.initialize()
          logger.info("Knowledge store initialized successfully")
      except Exception as e:
          logger.error(f"Failed to initialize knowledge store: {e}")
          # Continue without storage if it fails
          knowledge_store = None
  ```

* [ ] Update main() to initialize store:
  ```python
  def main():
      # ... existing setup ...
      
      # Initialize knowledge store
      if asyncio.get_event_loop().is_running():
          asyncio.create_task(init_knowledge_store())
      else:
          asyncio.run(init_knowledge_store())
      
      # ... rest of main
  ```

### Phase 8b – Store Topics Using Abstraction

#### Implementation Steps
* [ ] Update handle_complete_group to use abstraction:
  ```python
  async def handle_complete_group(strategy, text, metadata):
      """Handle complete group detection via callback"""
      # ... existing console output ...
      
      # Store in knowledge store if available
      if knowledge_store and text.strip():
          try:
              entry = KnowledgeEntry(
                  content=text,
                  timestamp=metadata.get('start_ts', datetime.now()),
                  metadata={
                      'voice_cue_flags': metadata.get('voice_cue_flags', []),
                      'duration_seconds': metadata.get('duration_seconds', 0),
                      'word_count': len(text.split()),
                      'type': metadata.get('type', 'topic')
                  },
                  group_id="voice_transcriptions"
              )
              entry_id = await knowledge_store.add_entry(entry)
              logger.info(f"Stored knowledge entry: {entry_id}")
          except Exception as e:
              logger.error(f"Failed to store in knowledge base: {e}")
              # Don't fail the whole process if storage fails
  ```

* [ ] Handle async callbacks properly:
  ```python
  # Wrapper to handle async callback from sync context
  def handle_group_complete_wrapper(strategy, text, metadata):
      if asyncio.get_event_loop().is_running():
          asyncio.create_task(handle_complete_group(strategy, text, metadata))
      else:
          asyncio.run(handle_complete_group(strategy, text, metadata))
  ```

* [ ] Add graceful shutdown:
  ```python
  # In KeyboardInterrupt handler
  if knowledge_store:
      await knowledge_store.close()
  ```

#### Test Plan
* Start complete_thoughts.py with Neo4j running
* Record several topics
* Verify storage in Neo4j Browser
* Test with Neo4j down (should continue working)
* Check logs for storage confirmations

### Success Criteria
* Topics stored automatically as they complete
* Storage failures don't crash the app
* Proper async handling throughout
* Clean shutdown of resources

---

## Phase 9 – Query Knowledge Tool

### Overview
Create a CLI tool to search and retrieve stored voice transcription topics using the KnowledgeStore abstraction.

### Implementation Steps

#### Create query_knowledge.py
* [ ] Basic structure with argparse:
  ```python
  #!/usr/bin/env python3
  """Query stored voice transcription topics from knowledge store"""
  
  import argparse
  import asyncio
  import os
  from datetime import datetime
  from dotenv import load_dotenv
  from knowledge_store import create_knowledge_store
  
  load_dotenv()
  
  async def search_topics(query: str, limit: int = 10, 
                         from_date: datetime = None, to_date: datetime = None):
      """Search for topics in the knowledge store"""
      # Create and initialize store
      store = create_knowledge_store()
      await store.initialize()
      
      try:
          # Search using abstraction
          results = await store.search(
              query=query,
              limit=limit,
              group_id="voice_transcriptions"
          )
          
          # Filter by date if provided
          if from_date or to_date:
              filtered = []
              for result in results:
                  timestamp = result.entry.timestamp
                  if from_date and timestamp < from_date:
                      continue
                  if to_date and timestamp > to_date:
                      continue
                  filtered.append(result)
              results = filtered
          
          return results
      finally:
          await store.close()
  ```

* [ ] Add CLI argument parsing:
  ```python
  parser = argparse.ArgumentParser(description='Query voice transcription topics')
  parser.add_argument('query', help='Search query')
  parser.add_argument('--limit', type=int, default=10, help='Max results')
  parser.add_argument('--from-date', type=str, help='Start date (YYYY-MM-DD)')
  parser.add_argument('--to-date', type=str, help='End date (YYYY-MM-DD)')
  parser.add_argument('--show-facts', action='store_true', 
                      help='Show extracted facts and relationships')
  ```

* [ ] Format and display results:
  ```python
  def display_results(results):
      """Display search results in readable format"""
      if not results:
          print("No results found.")
          return
      
      print(f"\nFound {len(results)} results:\n")
      
      for i, result in enumerate(results, 1):
          entry = result.entry
          print(f"[{i}] Voice Topic {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
          print(f"    Content: {entry.content[:100]}...")
          
          if result.facts:
              print(f"    Facts: {', '.join(result.facts[:3])}")
          
          if result.relationships:
              for rel in result.relationships[:2]:
                  if rel.get('target'):
                      print(f"    Related to: {rel['target']}")
          
          if entry.metadata:
              duration = entry.metadata.get('duration_seconds', 0)
              if duration:
                  print(f"    Duration: {duration:.1f}s")
          
          print("-" * 60)
  ```

### Advanced Features
* [ ] Add backend-specific features:
  ```python
  # Some features may be backend-specific
  # For example, Graphiti supports center node search
  if args.backend_features and hasattr(store, 'search_contextual'):
      # Use backend-specific advanced search if available
      results = await store.search_contextual(query, context_id=args.context)
  ```

* [ ] Add export functionality:
  ```python
  if args.export:
      # Export results to JSON or CSV
      import json
      export_data = []
      for result in results:
          export_data.append({
              'timestamp': result.entry.timestamp.isoformat(),
              'content': result.entry.content,
              'facts': result.facts,
              'metadata': result.entry.metadata
          })
      
      with open(args.export, 'w') as f:
          json.dump(export_data, f, indent=2)
      print(f"Exported {len(results)} results to {args.export}")
  ```

### Example Usage
```bash
# Basic search
python query_knowledge.py "meeting notes about project X"

# With options
python query_knowledge.py "budget discussions" --limit 20 --from-date 2025-01-01

# Show facts and relationships
python query_knowledge.py "team updates" --show-facts

# Contextual search
python query_knowledge.py "design decisions" --contextual
```

### Expected Output Format
```
Found 3 results:

[1] Voice Topic 2025-01-05 14:30:22
    Content: We need to discuss the project timeline. The deadline has been moved...
    Facts: Project X deadline moved to February, Budget increased by 20%
    Related to: Project X
    Duration: 45.2s
------------------------------------------------------------
[2] Voice Topic 2025-01-04 10:15:33
    Content: Team update meeting. Sarah will be joining our team next week as a...
    Facts: New team member Sarah joining, She has 5 years ML experience
    Related to: Team Updates
    Duration: 120.5s
------------------------------------------------------------
```

### Test Plan
* Search for known topics stored during testing
* Test date filtering with various ranges
* Verify contextual search improves relevance
* Test with no results
* Test with special characters in queries

### Success Criteria
* Returns relevant results for keyword searches
* Date filtering works correctly
* Results include temporal information
* Handles errors gracefully (Neo4j down, etc.)

---

## Risk Mitigation (from Model Consensus)

### Based on o3 and Gemini 2.5 Pro Analysis:

1. **Latency Concerns**
   - o3: 300-800ms base latency + network hops
   - Mitigation: 5-10s buffering makes this acceptable
   - Consider regex fallback for urgent commands (pause/resume)

2. **Cost Management**
   - Estimated $0.005-0.01 per request
   - Mitigation: Buffer to reduce calls, monitor usage
   - Set cost alerts and limits

3. **Reliability**
   - Rate limits: 350 RPM default
   - Mitigation: Implement retry logic, circuit breaker
   - Keep simple string matching as fallback

4. **Safety**
   - Risk of hallucinated commands
   - Mitigation: Validate tool names before execution
   - Consider confirmation for destructive actions

---

## Models Available
As documented in CLAUDE.md:
- **GPT-4o** - Primary model with tool calling support
- **GPT-4o-mini** - Faster, cheaper alternative
- **o3** - Advanced reasoning model
- **o3-mini** - Smaller o3 variant

---

## Final Acceptance Checklist

* [ ] Neo4j running via docker-compose
* [ ] Topics stored as Graphiti episodes with metadata
* [ ] Query tool returns relevant search results
* [ ] Prototype validates <10s command latency
* [ ] Cost model validated and acceptable
* [ ] API error handling tested
* [ ] Natural language variations tested
* [ ] Amir approval

---

## Graphiti Analysis for Voice Transcription Topics

### Overview
Graphiti is a framework for building temporally-aware knowledge graphs designed for AI agents. Key features:
- **Real-time incremental updates** - Adds new episodes without recomputing entire graph
- **Bi-temporal data model** - Tracks both when events occurred and when they were ingested
- **Hybrid retrieval** - Combines semantic embeddings, BM25 keyword search, and graph traversal
- **Dynamic relationships** - Handles changing facts and edge invalidation over time

### Architecture & Components

#### Core Data Models
1. **Episodes** - Primary units of information (text, JSON, or messages)
   - `EpisodicNode` - Stores raw content with timestamps
   - Types: message, json, text

2. **Entities** - Extracted nodes representing concepts/people/things
   - `EntityNode` - Has name, summary, attributes, embeddings
   - Custom entity types supported via Pydantic models

3. **Edges** - Relationships between entities
   - `EntityEdge` - Named relationships with facts and embeddings
   - `EpisodicEdge` - Links episodes to entities they mention
   - Temporal validity tracking (valid_at, invalid_at)

4. **Communities** - Clusters of related entities
   - Built using graph algorithms
   - Helps with context-aware retrieval

#### Key Capabilities

1. **Incremental Processing**
   - Episodes added sequentially
   - LLM extracts entities and relationships
   - Deduplication across episodes
   - Edge invalidation when facts change

2. **Search & Retrieval**
   - Hybrid search combining:
     - Semantic similarity (embeddings)
     - BM25 keyword matching
     - Graph distance reranking
   - Predefined search recipes for common patterns

3. **Temporal Handling**
   - Bi-temporal tracking (event time vs ingestion time)
   - Edge invalidation when contradictions detected
   - Point-in-time queries possible

4. **Storage Backend**
   - Neo4j or FalkorDB graph databases
   - Supports embeddings and full-text search
   - Scales to large datasets

### Pros for Voice Transcription Use Case

1. **Incremental Updates** - Perfect for streaming voice data
   - Add topics as they're spoken
   - No need to reprocess everything

2. **Relationship Discovery** - Automatically finds connections
   - Links people, topics, concepts across conversations
   - Builds knowledge graph over time

3. **Temporal Awareness** - Tracks when things were said
   - Can query "what did we discuss last week?"
   - Handles changing facts (e.g., job changes)

4. **Flexible Schema** - Custom entity types
   - Define domain-specific entities (e.g., "Project", "Idea")
   - Add attributes as needed

5. **Rich Retrieval** - Multiple search methods
   - Find by keyword, semantic meaning, or graph proximity
   - Rerank by relevance to specific topics/people

### Cons for Voice Transcription Use Case

1. **Complexity** - Heavy framework for simple use case
   - Requires Neo4j/FalkorDB setup
   - Many features may be overkill initially

2. **LLM Dependency** - Requires API calls for processing
   - Cost per episode (OpenAI/Anthropic/etc)
   - Latency for extraction (not real-time)
   - Best with structured output models

3. **Episode Granularity** - Designed for distinct episodes
   - Voice transcription is continuous stream
   - Need to chunk into meaningful episodes

4. **Storage Requirements** - Graph database overhead
   - More complex than simple vector DB
   - Requires maintenance and backups

5. **Learning Curve** - Sophisticated abstractions
   - Understanding graph queries
   - Configuring search recipes

### Implementation Considerations

1. **Episode Chunking Strategy**
   - Could use topic boundaries as episodes
   - Or time-based chunks (e.g., 5-minute segments)
   - Voice cues could trigger new episodes

2. **Entity Extraction**
   - Define custom entities for your domain
   - Configure what to extract (people, projects, ideas)
   - Balance extraction detail vs cost

3. **Search Configuration**
   - Use predefined recipes or create custom
   - Consider center node reranking for context
   - Tune hybrid search weights

4. **Incremental Building**
   - Start simple with basic entities
   - Add custom types as patterns emerge
   - Evolve schema over time

### Recommendation

**Good fit if:**
- You want automatic relationship discovery
- Historical queries are important
- You need to track changing facts over time
- You're building a long-term knowledge base
- You have budget for LLM processing

**Not ideal if:**
- You just need simple topic storage
- Real-time processing is critical
- You want to minimize dependencies
- Cost is a major concern
- Simple vector similarity is sufficient

**Alternative approach:**
- Use Graphiti concepts but simpler implementation
- Store topics with embeddings in vector DB
- Add graph relationships later if needed
- Could migrate to full Graphiti as complexity grows