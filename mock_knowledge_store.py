"""
Mock Knowledge Store Implementation

In-memory implementation for testing without Neo4j.
Does not extract facts - simply stores and retrieves entries.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from knowledge_store import KnowledgeStore, KnowledgeEntry, KnowledgeFact, SearchResult


class MockKnowledgeStore(KnowledgeStore):
    """
    Simple in-memory knowledge store for testing.
    
    Features:
    - Stores entries in memory
    - Basic keyword search
    - No fact extraction (simulates simple backend)
    """
    
    def __init__(self):
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the mock store (no-op for in-memory)"""
        self._initialized = True
    
    async def add_entry(self, 
                       content: str,
                       timestamp: Optional[datetime] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> KnowledgeEntry:
        """Add entry to in-memory storage"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        entry_id = str(uuid.uuid4())
        entry = KnowledgeEntry(
            id=entry_id,
            content=content,
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata=metadata or {},
            extracted_facts=[]  # Mock doesn't extract facts
        )
        
        self._entries[entry_id] = entry
        return entry
    
    async def search(self, 
                    query: str,
                    limit: int = 10,
                    include_entries: bool = False) -> SearchResult:
        """Simple keyword search in content"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        query_lower = query.lower()
        matching_entries = []
        
        # Simple keyword matching
        for entry in self._entries.values():
            if query_lower in entry.content.lower():
                matching_entries.append(entry)
                if len(matching_entries) >= limit:
                    break
        
        return SearchResult(
            facts=[],  # Mock doesn't have facts
            entries=matching_entries if include_entries else [],
            query=query,
            total_results=len(matching_entries)
        )
    
    async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get entry by ID"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        return self._entries.get(entry_id)
    
    async def get_entries_by_date(self,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 limit: int = 10) -> List[KnowledgeEntry]:
        """Get entries within date range"""
        if not self._initialized:
            raise RuntimeError("Knowledge store not initialized")
        
        filtered_entries = []
        
        for entry in self._entries.values():
            # Check date range
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            
            filtered_entries.append(entry)
            if len(filtered_entries) >= limit:
                break
        
        # Sort by timestamp descending
        filtered_entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return filtered_entries
    
    async def close(self) -> None:
        """Clean up (clear memory)"""
        self._entries.clear()
        self._initialized = False
    
    # Override optional methods for mock
    
    async def update_entry_metadata(self, 
                                  entry_id: str, 
                                  metadata: Dict[str, Any]) -> bool:
        """Update metadata for an entry"""
        if entry_id in self._entries:
            self._entries[entry_id].metadata.update(metadata)
            return True
        return False
    
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False