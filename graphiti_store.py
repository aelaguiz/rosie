"""
Graphiti Knowledge Store Implementation

Connects our abstraction to Graphiti's temporally-aware knowledge graph.
Handles the dual nature: Episodes for content, EntityEdges for facts.
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from knowledge_store import (
    KnowledgeStore, KnowledgeEntry, KnowledgeFact, SearchResult
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class GraphitiKnowledgeStore(KnowledgeStore):
    """
    Graphiti-based knowledge store implementation.
    
    Key behaviors from exploration:
    - Episodes store voice transcriptions with full content
    - Search returns EntityEdges (facts), not episodes
    - Must use episode_ids to retrieve original content
    - Entities are automatically extracted and deduplicated
    """
    
    def __init__(self):
        self._graphiti = None
        self._initialized = False
        
        # Load configuration from environment
        self._neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self._neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self._neo4j_password = os.getenv('NEO4J_PASSWORD', 'rosie_local_password')
        
        # Group ID for all voice transcriptions
        self._group_id = "voice_transcriptions"
    
    async def initialize(self) -> None:
        """Initialize Graphiti and Neo4j connection"""
        try:
            from graphiti_core import Graphiti
            from graphiti_core.nodes import EpisodeType
            
            # Store EpisodeType for later use
            self._episode_type = EpisodeType
            
            # Create Graphiti client
            self._graphiti = Graphiti(
                uri=self._neo4j_uri,
                user=self._neo4j_user,
                password=self._neo4j_password
            )
            
            # Build indices (safe to run multiple times)
            await self._graphiti.build_indices_and_constraints()
            
            self._initialized = True
            logger.info("Graphiti knowledge store initialized successfully")
            
        except ImportError:
            raise ImportError("graphiti-core not installed. Run: pip install graphiti-core")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise
    
    async def add_entry(self, 
                       content: str,
                       timestamp: Optional[datetime] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> KnowledgeEntry:
        """Add voice transcription as Graphiti episode"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        # Prepare episode name with timestamp
        ts = timestamp or datetime.now(timezone.utc)
        episode_name = f"Voice Topic {ts.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Add metadata to source description if available
        source_desc = "voice transcription"
        if metadata and metadata.get('voice_cues'):
            cues = metadata['voice_cues']
            source_desc += f" (cues: {', '.join(cues)})"
        
        try:
            # Add episode to Graphiti
            result = await self._graphiti.add_episode(
                name=episode_name,
                episode_body=content.strip(),
                source=self._episode_type.text,
                source_description=source_desc,
                reference_time=ts,
                group_id=self._group_id
            )
            
            # Convert to our abstraction
            extracted_facts = []
            for edge in result.edges:
                # Create KnowledgeFact from EntityEdge
                fact = KnowledgeFact(
                    id=edge.uuid,
                    fact=edge.fact,
                    source_entity=edge.source_node_uuid,  # We only have UUIDs
                    target_entity=edge.target_node_uuid,
                    episode_ids=[result.episode.uuid],
                    valid_at=edge.valid_at
                )
                extracted_facts.append(fact)
            
            # Create KnowledgeEntry
            entry = KnowledgeEntry(
                id=result.episode.uuid,
                content=content,
                timestamp=ts,
                metadata=metadata or {},
                extracted_facts=extracted_facts
            )
            
            logger.info(f"Added entry {entry.id} with {len(extracted_facts)} facts")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to add entry: {e}")
            raise
    
    async def search(self, 
                    query: str,
                    limit: int = 10,
                    include_entries: bool = False) -> SearchResult:
        """Search using Graphiti's hybrid search"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        try:
            # Use basic search which returns EntityEdges
            edges = await self._graphiti.search(
                query=query,
                group_ids=[self._group_id],
                num_results=limit
            )
            
            # Convert EntityEdges to KnowledgeFacts
            facts = []
            episode_ids_to_fetch = set()
            
            for edge in edges:
                # Get entity names if we need them
                # Note: From exploration, we know edges don't have populated nodes
                source_name = f"Entity_{edge.source_node_uuid[:8]}"
                target_name = f"Entity_{edge.target_node_uuid[:8]}" if edge.target_node_uuid else None
                
                fact = KnowledgeFact(
                    id=edge.uuid,
                    fact=edge.fact,
                    source_entity=source_name,
                    target_entity=target_name,
                    episode_ids=edge.episodes,
                    valid_at=edge.valid_at
                )
                facts.append(fact)
                
                # Collect episode IDs if we need to fetch entries
                if include_entries:
                    episode_ids_to_fetch.update(edge.episodes)
            
            # Fetch episodes if requested
            entries = []
            if include_entries and episode_ids_to_fetch:
                from graphiti_core.nodes import EpisodicNode
                
                episodes = await EpisodicNode.get_by_uuids(
                    self._graphiti.driver,
                    list(episode_ids_to_fetch)
                )
                
                for episode in episodes:
                    entry = KnowledgeEntry(
                        id=episode.uuid,
                        content=episode.content,
                        timestamp=episode.created_at,
                        metadata={
                            "name": episode.name,
                            "source_description": getattr(episode, 'source_description', '')
                        },
                        extracted_facts=[]  # We already have facts separately
                    )
                    entries.append(entry)
            
            return SearchResult(
                facts=facts,
                entries=entries,
                query=query,
                total_results=len(facts)
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Return empty results on error
            return SearchResult(query=query)
    
    async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get specific episode by UUID"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        try:
            from graphiti_core.nodes import EpisodicNode
            
            episodes = await EpisodicNode.get_by_uuids(
                self._graphiti.driver,
                [entry_id]
            )
            
            if not episodes:
                return None
            
            episode = episodes[0]
            
            # Convert to KnowledgeEntry
            entry = KnowledgeEntry(
                id=episode.uuid,
                content=episode.content,
                timestamp=episode.created_at,
                metadata={
                    "name": episode.name,
                    "source_description": getattr(episode, 'source_description', ''),
                    "entity_edges_count": len(episode.entity_edges)
                },
                extracted_facts=[]  # Would need separate query for facts
            )
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to get entry {entry_id}: {e}")
            return None
    
    async def get_entries_by_date(self,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 limit: int = 10) -> List[KnowledgeEntry]:
        """Get episodes within date range"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        try:
            # Use retrieve_episodes for date-based retrieval
            reference_time = end_date or datetime.now(timezone.utc)
            
            episodes = await self._graphiti.retrieve_episodes(
                reference_time=reference_time,
                last_n=limit,
                group_ids=[self._group_id]
            )
            
            # Filter by start date if provided
            if start_date:
                episodes = [ep for ep in episodes if ep.created_at >= start_date]
            
            # Convert to KnowledgeEntry objects
            entries = []
            for episode in episodes:
                entry = KnowledgeEntry(
                    id=episode.uuid,
                    content=episode.content,
                    timestamp=episode.created_at,
                    metadata={
                        "name": episode.name,
                        "source_description": getattr(episode, 'source_description', ''),
                        "entity_edges_count": len(episode.entity_edges)
                    },
                    extracted_facts=[]
                )
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get entries by date: {e}")
            return []
    
    async def close(self) -> None:
        """Close Graphiti connection"""
        if self._graphiti and hasattr(self._graphiti, 'close'):
            await self._graphiti.close()
        self._initialized = False
        logger.info("Graphiti knowledge store closed")