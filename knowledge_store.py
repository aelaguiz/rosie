"""
Knowledge Store Abstraction Layer

This module provides an abstraction over different knowledge storage backends,
starting with Graphiti but designed to support other backends in the future.

Based on exploration findings:
- Episodes store original content (voice transcriptions)
- Search returns facts (EntityEdges), not content
- Must handle dual nature: content storage vs fact retrieval
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class KnowledgeBackend(Enum):
    """Supported knowledge storage backends"""
    GRAPHITI = "graphiti"
    MOCK = "mock"  # For testing


@dataclass
class KnowledgeEntry:
    """
    Represents a stored piece of knowledge (voice transcription).
    Maps to Graphiti Episodes.
    """
    id: str  # UUID
    content: str  # Full transcription text
    timestamp: datetime  # When recorded
    metadata: Dict[str, Any] = field(default_factory=dict)  # Duration, voice cues, etc.
    extracted_facts: List['KnowledgeFact'] = field(default_factory=list)  # Facts from this entry
    
    def __post_init__(self):
        # Ensure metadata is always a dict
        if self.metadata is None:
            self.metadata = {}


@dataclass
class KnowledgeFact:
    """
    Represents an extracted fact or relationship.
    Maps to Graphiti EntityEdges.
    """
    id: str  # UUID
    fact: str  # The extracted statement
    source_entity: str  # Name (not UUID) for readability
    target_entity: Optional[str] = None  # Optional related entity
    episode_ids: List[str] = field(default_factory=list)  # Which entries this came from
    valid_at: Optional[datetime] = None  # When fact became true
    confidence: float = 1.0  # Confidence score if available
    
    def __post_init__(self):
        # Ensure episode_ids is always a list
        if self.episode_ids is None:
            self.episode_ids = []


@dataclass
class SearchResult:
    """
    Container for search results.
    Can contain facts without entries (common case with Graphiti).
    """
    facts: List[KnowledgeFact] = field(default_factory=list)
    entries: List[KnowledgeEntry] = field(default_factory=list)
    query: str = ""
    total_results: int = 0
    
    def __post_init__(self):
        # Calculate total if not set
        if self.total_results == 0:
            self.total_results = len(self.facts) + len(self.entries)


class KnowledgeStore(ABC):
    """
    Abstract base class for knowledge storage backends.
    
    Implementations must handle:
    1. Storing voice transcriptions as entries
    2. Searching for facts/relationships
    3. Retrieving original content
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the knowledge store connection and any required setup.
        For Graphiti, this includes building Neo4j indices.
        """
        pass
    
    @abstractmethod
    async def add_entry(self, 
                       content: str,
                       timestamp: Optional[datetime] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> KnowledgeEntry:
        """
        Add a new knowledge entry (voice transcription).
        
        Args:
            content: The transcription text
            timestamp: When the content was recorded (defaults to now)
            metadata: Additional metadata (duration, voice cues, etc.)
            
        Returns:
            The created KnowledgeEntry with ID and any extracted facts
        """
        pass
    
    @abstractmethod
    async def search(self, 
                    query: str,
                    limit: int = 10,
                    include_entries: bool = False) -> SearchResult:
        """
        Search for knowledge using natural language query.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            include_entries: Whether to include full entries (not just facts)
            
        Returns:
            SearchResult containing facts and optionally entries
        """
        pass
    
    @abstractmethod
    async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """
        Retrieve a specific entry by ID.
        
        Args:
            entry_id: The UUID of the entry
            
        Returns:
            The KnowledgeEntry if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_entries_by_date(self,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 limit: int = 10) -> List[KnowledgeEntry]:
        """
        Retrieve entries within a date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            limit: Maximum number of entries
            
        Returns:
            List of KnowledgeEntry objects
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close connections and clean up resources.
        """
        pass
    
    # Optional methods that backends can override
    
    async def update_entry_metadata(self, 
                                  entry_id: str, 
                                  metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for an existing entry.
        Default implementation returns False (not supported).
        """
        return False
    
    async def delete_entry(self, entry_id: str) -> bool:
        """
        Delete an entry. 
        Default implementation returns False (not supported).
        """
        return False


def create_knowledge_store(backend: Optional[str] = None) -> KnowledgeStore:
    """
    Factory function to create appropriate knowledge store backend.
    
    Args:
        backend: Backend name or None to use environment variable
        
    Returns:
        KnowledgeStore instance
        
    Raises:
        ValueError: If backend is not supported
    """
    if backend is None:
        backend = os.getenv('KNOWLEDGE_BACKEND', 'graphiti')
    
    backend_enum = KnowledgeBackend(backend.lower())
    
    if backend_enum == KnowledgeBackend.GRAPHITI:
        # Import will be added when we implement GraphitiKnowledgeStore
        raise NotImplementedError("GraphitiKnowledgeStore not yet implemented")
    elif backend_enum == KnowledgeBackend.MOCK:
        from mock_knowledge_store import MockKnowledgeStore
        return MockKnowledgeStore()
    else:
        raise ValueError(f"Unsupported knowledge backend: {backend}")