"""
Unified memory service for both Eva Agent and MCP Bridge.
This is the single entry point for all memory operations.
"""

import asyncio
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# Suppress logs during import when in MCP mode
_original_level = logging.root.level
if not os.sys.stdin.isatty():  # Running in MCP mode
    logging.root.setLevel(logging.CRITICAL)
    # Also suppress specific loggers that output during model loading
    logging.getLogger("sentence_transformers").setLevel(logging.CRITICAL)
    logging.getLogger("transformers").setLevel(logging.CRITICAL)
    logging.getLogger("torch").setLevel(logging.CRITICAL)
    logging.getLogger("filelock").setLevel(logging.CRITICAL)

try:
    import structlog
    
    # Import Eva's memory components
    import sys
    eva_path = Path(__file__).parent.parent.parent / "eva-agent" / "src"
    if str(eva_path) not in sys.path:
        sys.path.insert(0, str(eva_path))
    
    from memory.memory_manager import MemoryManager
    from memory.models import (
        BaseMemory,
        KnowledgeMemory,
        MemorySearchQuery,
        MemorySearchResult,
        MemoryType,
        MemoryPriority,
    )
    
    logger = structlog.get_logger()
finally:
    # Restore original logging level
    logging.root.setLevel(_original_level)


class UnifiedMemoryService:
    """Unified memory service that both Eva and MCP connectors use"""
    
    _instance: Optional['UnifiedMemoryService'] = None
    _lock = asyncio.Lock()
    
    def __init__(
        self,
        mongodb_url: Optional[str] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        use_vector_memory: bool = True,
    ):
        """Initialize unified memory service
        
        Args:
            mongodb_url: MongoDB connection URL
            qdrant_host: Qdrant host
            qdrant_port: Qdrant port  
            use_vector_memory: Whether to use vector memory
        """
        # Use environment variables or defaults
        self.mongodb_url = mongodb_url or os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
        self.qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))
        self.use_vector_memory = use_vector_memory
        
        # Create the underlying memory manager
        self.memory_manager = MemoryManager(
            mongodb_url=self.mongodb_url,
            qdrant_host=self.qdrant_host,
            qdrant_port=self.qdrant_port,
            use_vector_memory=self.use_vector_memory
        )
        
        self._initialized = False
        
    @classmethod
    async def get_instance(cls, **kwargs) -> 'UnifiedMemoryService':
        """Get or create the singleton instance
        
        This ensures both Eva and MCP use the same memory service.
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(**kwargs)
                await cls._instance.initialize()
            return cls._instance
    
    async def initialize(self):
        """Initialize the memory service"""
        if self._initialized:
            return
            
        await self.memory_manager.initialize()
        self._initialized = True
        logger.info(
            "Unified memory service initialized",
            mongodb_url=self.mongodb_url,
            qdrant_host=self.qdrant_host,
            use_vector_memory=self.use_vector_memory
        )
    
    async def shutdown(self):
        """Shutdown the memory service"""
        if self._initialized:
            await self.memory_manager.shutdown()
            self._initialized = False
            logger.info("Unified memory service shutdown")
    
    # Memory operations - single interface for all consumers
    
    async def remember(
        self,
        content: str,
        source: str = "unknown",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: str = "medium"
    ) -> KnowledgeMemory:
        """Store a memory (for MCP connector)
        
        Args:
            content: The memory content to store
            source: Source of the memory (e.g., "claude", "eva", "user")
            tags: Optional tags for categorization
            metadata: Optional metadata
            priority: Priority level (critical, high, medium, low)
            
        Returns:
            The created memory
        """
        # Create a knowledge memory
        memory = KnowledgeMemory(
            content=content,
            subject=source,
            facts=[content],  # For now, treat the whole content as one fact
            source=source,
            tags=tags or [],
            metadata=metadata or {},
            priority=MemoryPriority(priority),
            reliability=0.9  # High reliability for user-provided memories
        )
        
        # Add to working memory
        await self.memory_manager.working_memory.add_memory(memory)
        
        # Add to vector memory for semantic search
        if self.use_vector_memory and self.memory_manager.vector_memory:
            try:
                await self.memory_manager.vector_memory.add_memory(memory)
            except Exception as e:
                logger.error("Failed to add to vector memory", error_msg=str(e))
        
        logger.info(
            "Memory stored",
            id=memory.id,
            source=source,
            content_preview=content[:100]
        )
        
        return memory
    
    async def recall(
        self,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[str]] = None,
        semantic_search: bool = True
    ) -> List[MemorySearchResult]:
        """Search and retrieve memories (for MCP connector)
        
        Args:
            query: Search query
            limit: Maximum number of results
            memory_types: Types of memory to search (if None, search all)
            semantic_search: Whether to use semantic search
            
        Returns:
            List of search results
        """
        # Convert string memory types to enum if provided
        if memory_types:
            try:
                memory_type_enums = [MemoryType(t) for t in memory_types]
            except ValueError:
                # If invalid type provided, search all types
                memory_type_enums = None
        else:
            memory_type_enums = None
        
        # Create search query
        search_query = MemorySearchQuery(
            query=query,
            memory_types=memory_type_enums,
            limit=limit,
            semantic_search=semantic_search
        )
        
        # Search memories
        results = await self.memory_manager.search(search_query)
        
        logger.info(
            "Memory search completed",
            query=query,
            results_count=len(results),
            semantic=semantic_search
        )
        
        return results
    
    # Eva-specific methods (delegate to memory manager)
    
    async def add_conversation(self, *args, **kwargs):
        """Add a conversation (Eva-specific)"""
        return await self.memory_manager.add_conversation(*args, **kwargs)
    
    async def add_decision(self, *args, **kwargs):
        """Add a decision (Eva-specific)"""
        return await self.memory_manager.add_decision(*args, **kwargs)
    
    async def add_pattern(self, *args, **kwargs):
        """Add a pattern (Eva-specific)"""
        return await self.memory_manager.add_pattern(*args, **kwargs)
    
    async def add_preference(self, *args, **kwargs):
        """Add a preference (Eva-specific)"""
        return await self.memory_manager.add_preference(*args, **kwargs)
    
    async def get_or_create_user_profile(self, *args, **kwargs):
        """Get or create user profile (Eva-specific)"""
        return await self.memory_manager.get_or_create_user_profile(*args, **kwargs)
    
    async def update_user_profile(self, *args, **kwargs):
        """Update user profile (Eva-specific)"""
        return await self.memory_manager.update_user_profile(*args, **kwargs)
    
    async def get_user_context(self, *args, **kwargs):
        """Get user context (Eva-specific)"""
        return await self.memory_manager.get_user_context(*args, **kwargs)
    
    async def get_context_for_task(self, *args, **kwargs):
        """Get context for a task (Eva-specific)"""
        return await self.memory_manager.get_context_for_task(*args, **kwargs)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return await self.memory_manager.get_stats()


# Convenience function for getting the service
async def get_memory_service(**kwargs) -> UnifiedMemoryService:
    """Get the unified memory service instance"""
    return await UnifiedMemoryService.get_instance(**kwargs)