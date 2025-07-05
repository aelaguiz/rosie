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

### ✅ Milestone 3 – Knowledge Storage Abstraction (COMPLETE)
* [x] **Phase 7** – Knowledge Storage Abstraction Layer ✅
  * [x] **Phase 7-explore** – Exploration: Understand Graphiti's Actual Behavior ✅
  * [x] **Phase 7a** – Design KnowledgeStore Interface (Based on Validated Findings) ✅
  * [x] **Phase 7b** – Implement GraphitiKnowledgeStore Driver ✅
  * [x] **Phase 7c** – Test Abstraction Independently ✅
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

### Phase 7-explore – Exploration: Understand Graphiti's Actual Behavior

#### Why Exploration First?
Initial analysis revealed a **fundamental mismatch** between our abstraction design and Graphiti's data model:
- **Our assumption**: Search returns stored content entries (like documents)
- **Graphiti reality**: Search returns facts/relationships (EntityEdges) between entities
- **The issue**: Trying to map relationship edges to content entries doesn't align

#### Implementation Steps ✅
* [x] Create explore_graphiti.py test script that:
  - Adds a voice transcription as an episode
  - Shows what entities and facts Graphiti extracts
  - Tests basic search() which returns EntityEdges (facts)
  - Tests advanced search_() which returns SearchResults with edges, nodes, episodes
  - Tests retrieve_episodes() to get episodes by date
  - Documents the relationship between episodes, entities, and facts

* [x] Run exploration script and document findings:
  - Episodes stored with full content, retrieved by UUID or date range
  - Search returns EntityEdges (facts), NOT episodes
  - Get episodes via retrieve_episodes() or EpisodicNode.get_by_uuids()
  - Facts link to episodes via episode_ids array

* [x] Test edge cases:
  - Empty transcriptions rejected with validation error
  - Short transcriptions ("Hello world") create minimal entities, no facts
  - Multiple episodes successfully share entities (deduplication confirmed)
  - Search with no matches returns empty list (no error)

#### Actual Findings from Exploration
1. **Episode Storage**: 
   - Voice transcriptions stored as Episodes with complete content preserved
   - Each episode gets UUID, name, timestamp, and entity_edges references
   - Example: "Voice Topic 2025-01-05 14:30:00" stored successfully

2. **Entity Extraction**: 
   - From our test: 9 entities extracted (Sarah, John, project timeline, etc.)
   - Entities are deduplicated across episodes
   - Each entity gets UUID and name

3. **Fact Generation**: 
   - 5 facts extracted from test transcript
   - Facts are EntityEdges with: fact text, source/target UUIDs, valid_at timestamp
   - Example: "Sarah will be joining the team as our new ML engineer"

4. **Search Behavior** (Critical Finding):
   - `search()` returns list of EntityEdges, NOT episodes or content
   - EntityEdges don't have source_node/target_node objects, only UUIDs
   - `search_()` returns SearchResults but nodes/episodes often empty
   - Must use episode_ids from facts to retrieve original content

5. **Retrieval Options**:
   - `retrieve_episodes()` - Get episodes by date range and group_id
   - `EpisodicNode.get_by_uuids()` - Get specific episodes by UUID
   - No direct content search - only fact search

6. **Edge Case Behavior**:
   - Empty transcriptions are rejected with validation error
   - Short transcriptions ("Hello world") create minimal entities, no facts
   - Multiple episodes successfully share entities (deduplication confirmed)
   - Search with no matches returns empty list (no error)

#### Environment Configuration Requirements
* **Neo4j Setup**: Must have Neo4j running (docker-compose up)
* **Environment Variables**: 
  - `DEFAULT_DATABASE=neo4j` (critical for Graphiti)
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for connection
  - `OPENAI_API_KEY` for entity/fact extraction
* **Initialization**: Must call `build_indices_and_constraints()` once

#### Key Implementation Insights from Exploration
* **Dual Model**: Store content as episodes, search returns facts as edges
* **Indirection**: Search → Facts → episode_ids → retrieve episodes → content
* **Abstraction Design**: Must handle both content storage and fact retrieval
* **EntityEdge objects**: In search results lack populated source/target nodes
* **Episode IDs**: In facts are arrays (can reference multiple episodes)
* **Search optimization**: Primarily for fact retrieval, not content search

### Phase 7a – Design KnowledgeStore Interface (Based on Validated Findings)

#### Validated Design from Exploration
Our exploration confirmed Graphiti's dual storage model:
1. **Episodes** = Stored voice transcriptions (complete content)
2. **EntityEdges** = Extracted facts that search returns
3. **Indirection** = Facts contain episode_ids to find original content

#### Key Design Constraints from Testing
- EntityEdge objects in search results lack populated source/target nodes
- Episode IDs in facts are arrays (can reference multiple episodes)
- Search primarily optimized for fact retrieval, not content search
- Must handle async operations throughout the stack

#### Abstraction Design
Based on our findings, the abstraction must support:

**Data Models**:
- **KnowledgeEntry**: Maps to Episodes (voice transcriptions)
  - id: Episode UUID
  - content: Full transcription text
  - timestamp: When recorded
  - metadata: Duration, voice cues, etc.
  - extracted_facts: List of facts found in this entry

- **KnowledgeFact**: Maps to EntityEdges (extracted relationships)
  - id: Edge UUID
  - fact: The extracted statement
  - source_entity: Name (not UUID) for readability
  - target_entity: Optional related entity
  - episode_ids: Which entries this fact came from
  - valid_at: When fact became true

- **SearchResult**: Container for search results
  - facts: List of KnowledgeFact objects
  - entries: List of KnowledgeEntry objects (may be empty)
  - Can return facts without entries (common case)

**Key Design Decisions**:
1. Search primarily returns facts, not original content
2. Must provide episode retrieval separate from search
3. Support backends that only do storage (no fact extraction)
4. Handle Graphiti's UUID-only references gracefully

#### Implementation Steps ✅
* [x] Create knowledge_store.py with abstract base class defining:
  - KnowledgeEntry dataclass (stored content like voice transcriptions)
  - KnowledgeFact dataclass (extracted facts/relationships)
  - SearchResult dataclass (can contain both entries and facts)
  - KnowledgeStore ABC with methods: initialize, add_entry, search, get_entry, close
  
* [x] Create factory function for backend selection based on KNOWLEDGE_BACKEND env var

#### Test Plan ✅
* [x] Verify abstract methods are properly defined
* [x] Test factory function with different backends
* [x] Ensure data classes work correctly

### Phase 7b – Implement GraphitiKnowledgeStore Driver

#### Implementation Steps ✅
* [x] Create graphiti_store.py implementing the KnowledgeStore interface:
  - Initialize Graphiti with Neo4j connection from env vars
  - add_entry() stores voice transcriptions as Graphiti episodes
  - search() uses search() method (simpler than search_())
  - Converts Graphiti's EntityEdges to KnowledgeFact objects
  - Converts Episodes to KnowledgeEntry objects
  - Returns SearchResult containing both facts and entries
  
* [x] Add graphiti-core to requirements.txt
* [x] Handle the dual nature of Graphiti's returns (facts vs content)

#### Test Plan ✅
* [x] Integration test with real Neo4j:
  - Initialize store
  - Add test entries
  - Search for entries
  - Verify results format
* [x] Test error scenarios
* [x] Cross-episode fact linking verified

### Phase 7c – Test Abstraction Independently

#### Implementation Steps ✅
* [x] Create test_knowledge_store.py that:
  - Tests the abstraction lifecycle (initialize, add, search, close)
  - Adds test voice transcription entries
  - Searches and verifies results contain both facts and entries
  - Tests with real Neo4j/Graphiti backend
  - Provides manual test script for debugging

* [x] Create mock_knowledge_store.py for testing without Neo4j:
  - In-memory storage for unit tests
  - Implements same KnowledgeStore interface
  - No fact extraction (simple backend example)
  - Add to factory function as 'mock' backend

#### Test Plan ✅
* [x] Run test script with Neo4j running
* [x] Verify entries are stored and searchable
* [x] Test with mock store for unit tests
* [x] Created test_graphiti_store.py for comprehensive testing
* [x] Created manual_test_graphiti.py for interactive testing

### Success Criteria ✅
* [x] Abstraction works with real Graphiti/Neo4j
* [x] Clean separation of concerns
* [x] Easy to add new backends (demonstrated with mock)
* [x] Performance acceptable (verified in tests)

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
* [ ] Add knowledge store imports from our abstraction
* [ ] Create async init_knowledge_store() function that:
  - Creates store using factory function
  - Initializes the backend (Neo4j for Graphiti)
  - Handles failures gracefully (app continues without storage)
* [ ] Update main() to call init_knowledge_store on startup
* [ ] Handle async initialization properly

### Phase 8b – Store Topics Using Abstraction

#### Implementation Steps
* [ ] Update handle_complete_group to use abstraction:
  - Create KnowledgeEntry from completed topic
  - Include metadata (duration, voice cues, word count)
  - Call knowledge_store.add_entry() if available
  - Log success/failure but don't crash on storage errors

* [ ] Handle async callbacks properly:
  - Create wrapper to handle async callback from sync context
  - Use asyncio.create_task or asyncio.run as appropriate

* [ ] Add graceful shutdown:
  - Close knowledge store on KeyboardInterrupt
  - Clean up resources properly

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
  - Create and initialize knowledge store
  - Search using the abstraction
  - Handle both entries and facts in results
  - Support date filtering and result limits
  - Close store properly after use

* [ ] Add CLI argument parsing:
  - Query string (required)
  - --limit for max results
  - --from-date and --to-date for filtering
  - --show-facts to display extracted facts
  - --backend to override default backend

* [ ] Format and display results:
  - Show entries (original voice topics) if available
  - Show facts extracted from topics if available
  - Display metadata like duration and timestamps
  - Handle mixed results gracefully

### Advanced Features
* [ ] Add backend-specific features:
  - Allow backends to expose additional search methods
  - Graphiti might support contextual search or graph traversal
  - Simple backends might only support basic text search

* [ ] Add export functionality:
  - Export results to JSON for further analysis
  - Include both entries and facts in export
  - Support CSV export for simpler analysis

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