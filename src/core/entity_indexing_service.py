"""
Entity Indexing Service
Background service for maintaining entity vector embeddings and relationships
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import structlog
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from ..connectors.entities.enhanced_connector import EnhancedEntitiesConnector
from .entities_memory_integration import EntitiesMemoryIntegration

logger = structlog.get_logger()


class EntityIndexingService:
    """Background service for entity indexing and maintenance"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.entities_connector = None
        self.memory_integration = None
        self.running = False
        self._tasks = []
        
        # Configuration
        self.batch_size = config.get("batch_size", 10)
        self.index_interval = config.get("index_interval", 60)  # seconds
        self.relationship_analysis_interval = config.get("relationship_interval", 300)  # 5 minutes
        self.cleanup_interval = config.get("cleanup_interval", 3600)  # 1 hour
        
    async def initialize(self):
        """Initialize the indexing service"""
        try:
            # Initialize enhanced entities connector
            self.entities_connector = EnhancedEntitiesConnector(
                name="entities",
                config=self.config.get("entities_config", {})
            )
            await self.entities_connector.initialize()
            
            # Initialize memory integration
            self.memory_integration = EntitiesMemoryIntegration(self.entities_connector)
            
            logger.info("Entity indexing service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize indexing service: {e}")
            raise
    
    async def start(self):
        """Start the background indexing service"""
        if self.running:
            logger.warning("Indexing service already running")
            return
            
        self.running = True
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._index_entities_loop()),
            asyncio.create_task(self._analyze_relationships_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._monitor_health())
        ]
        
        logger.info("Entity indexing service started")
        
        # Wait for tasks
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            logger.info("Indexing service tasks cancelled")
    
    async def stop(self):
        """Stop the indexing service"""
        self.running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            
        # Wait for cleanup
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Shutdown connector
        if self.entities_connector:
            await self.entities_connector.shutdown()
            
        logger.info("Entity indexing service stopped")
    
    async def _index_entities_loop(self):
        """Main loop for indexing entities"""
        while self.running:
            try:
                # Get unindexed entities
                unindexed = await self.entities_connector.get_unindexed_entities(self.batch_size)
                
                if unindexed:
                    logger.info(f"Indexing {len(unindexed)} entities")
                    
                    for entity in unindexed:
                        try:
                            # Generate embedding
                            await self.entities_connector._generate_entity_embedding(
                                entity["id"],
                                entity
                            )
                            
                            # Extract additional relationships from description
                            if entity.get("description"):
                                extraction = await self.memory_integration.extract_entities_from_text(
                                    entity["description"]
                                )
                                
                                # Create any new relationships found
                                entity_map = {entity["name"]: entity["id"]}
                                await self.memory_integration.create_relationships_from_extraction(
                                    extraction,
                                    entity_map
                                )
                                
                        except Exception as e:
                            logger.error(f"Failed to index entity {entity.get('id')}: {e}")
                            
                await asyncio.sleep(self.index_interval)
                
            except Exception as e:
                logger.error(f"Error in indexing loop: {e}")
                await asyncio.sleep(self.index_interval)
    
    async def _analyze_relationships_loop(self):
        """Analyze entity co-occurrences and create relationships"""
        while self.running:
            try:
                # This would analyze memories to find entity co-occurrences
                # and create inferred relationships
                
                # Get recent memories with entity references
                recent_memories = await self._get_recent_memories_with_entities()
                
                # Analyze co-occurrences
                cooccurrences = self._analyze_cooccurrences(recent_memories)
                
                # Create inferred relationships
                for (entity1_id, entity2_id), strength in cooccurrences.items():
                    if strength > 0.5:  # Threshold for relationship creation
                        await self._create_inferred_relationship(
                            entity1_id,
                            entity2_id,
                            strength
                        )
                        
                await asyncio.sleep(self.relationship_analysis_interval)
                
            except Exception as e:
                logger.error(f"Error in relationship analysis: {e}")
                await asyncio.sleep(self.relationship_analysis_interval)
    
    async def _cleanup_loop(self):
        """Clean up old or invalid data"""
        while self.running:
            try:
                # Clean up orphaned embeddings
                await self._cleanup_orphaned_embeddings()
                
                # Update stale embeddings
                await self._update_stale_embeddings()
                
                # Remove duplicate entities
                await self._merge_duplicate_entities()
                
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _monitor_health(self):
        """Monitor service health and metrics"""
        while self.running:
            try:
                # Get indexing statistics
                stats = await self._get_indexing_stats()
                
                logger.info(
                    "Indexing service health",
                    total_entities=stats["total_entities"],
                    indexed_entities=stats["indexed_entities"],
                    total_relationships=stats["total_relationships"],
                    pending_index=stats["pending_index"]
                )
                
                # Check for issues
                if stats["pending_index"] > 100:
                    logger.warning(f"High indexing backlog: {stats['pending_index']} entities")
                    
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _get_recent_memories_with_entities(self) -> List[Dict[str, Any]]:
        """Get recent memories that have entity references"""
        # This would query the memory system for recent memories with entity_refs
        # For now, return empty list - implementation depends on memory storage
        return []
    
    def _analyze_cooccurrences(self, memories: List[Dict[str, Any]]) -> Dict[tuple, float]:
        """Analyze entity co-occurrences in memories"""
        cooccurrences = {}
        
        for memory in memories:
            entity_refs = memory.get("entity_refs", [])
            
            # Count co-occurrences
            for i, ref1 in enumerate(entity_refs):
                for ref2 in entity_refs[i+1:]:
                    key = tuple(sorted([ref1["entity_id"], ref2["entity_id"]]))
                    cooccurrences[key] = cooccurrences.get(key, 0) + 1
                    
        # Normalize to get strength scores
        if cooccurrences:
            max_count = max(cooccurrences.values())
            for key in cooccurrences:
                cooccurrences[key] = cooccurrences[key] / max_count
                
        return cooccurrences
    
    async def _create_inferred_relationship(self, entity1_id: str, entity2_id: str, strength: float):
        """Create an inferred relationship between entities"""
        try:
            # Check if relationship already exists
            existing = await self.entities_connector.get_relationships({
                "from_entity_id": entity1_id,
                "to_entity_id": entity2_id
            })
            
            if not existing:
                await self.entities_connector.create_relationship({
                    "from_entity_id": entity1_id,
                    "to_entity_id": entity2_id,
                    "relationship_type": "collaborates_on",  # Generic relationship
                    "metadata": {
                        "inferred": True,
                        "strength": strength,
                        "created_by": "indexing_service",
                        "created_at": datetime.utcnow().isoformat()
                    }
                })
                
                logger.info(f"Created inferred relationship between {entity1_id} and {entity2_id}")
                
        except Exception as e:
            logger.error(f"Failed to create inferred relationship: {e}")
    
    async def _cleanup_orphaned_embeddings(self):
        """Remove embeddings for deleted entities"""
        if not self.entities_connector.embeddings_collection:
            return
            
        try:
            # Get all embedding entity IDs
            embeddings = await self.entities_connector.embeddings_collection.find(
                {}, {"entity_id": 1}
            ).to_list(length=None)
            
            embedding_ids = {e["entity_id"] for e in embeddings}
            
            # Check which entities still exist
            existing_entities = await self.entities_connector.entities_collection.find(
                {"_id": {"$in": [ObjectId(eid) for eid in embedding_ids]}},
                {"_id": 1}
            ).to_list(length=None)
            
            existing_ids = {str(e["_id"]) for e in existing_entities}
            
            # Delete orphaned embeddings
            orphaned = embedding_ids - existing_ids
            if orphaned:
                result = await self.entities_connector.embeddings_collection.delete_many(
                    {"entity_id": {"$in": list(orphaned)}}
                )
                logger.info(f"Cleaned up {result.deleted_count} orphaned embeddings")
                
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned embeddings: {e}")
    
    async def _update_stale_embeddings(self):
        """Update embeddings that are older than threshold"""
        if not self.entities_connector.embeddings_collection:
            return
            
        try:
            # Find embeddings older than 7 days
            threshold = datetime.utcnow() - timedelta(days=7)
            
            stale = await self.entities_connector.embeddings_collection.find(
                {"indexed_at": {"$lt": threshold}},
                {"entity_id": 1}
            ).limit(self.batch_size).to_list(length=None)
            
            for embedding_doc in stale:
                await self.entities_connector.update_entity_embedding(embedding_doc["entity_id"])
                
            if stale:
                logger.info(f"Updated {len(stale)} stale embeddings")
                
        except Exception as e:
            logger.error(f"Failed to update stale embeddings: {e}")
    
    async def _merge_duplicate_entities(self):
        """Detect and merge duplicate entities"""
        # This would use fuzzy matching or embedding similarity to find duplicates
        # For now, just a placeholder
        pass
    
    async def _get_indexing_stats(self) -> Dict[str, int]:
        """Get current indexing statistics"""
        stats = {
            "total_entities": 0,
            "indexed_entities": 0,
            "total_relationships": 0,
            "pending_index": 0
        }
        
        try:
            # Count total entities
            stats["total_entities"] = await self.entities_connector.entities_collection.count_documents({})
            
            # Count indexed entities
            if self.entities_connector.embeddings_collection:
                stats["indexed_entities"] = await self.entities_connector.embeddings_collection.count_documents({})
                
            # Count relationships
            stats["total_relationships"] = await self.entities_connector.relationships_collection.count_documents({})
            
            # Calculate pending
            stats["pending_index"] = stats["total_entities"] - stats["indexed_entities"]
            
        except Exception as e:
            logger.error(f"Failed to get indexing stats: {e}")
            
        return stats


async def run_indexing_service(config: Dict[str, Any]):
    """Run the entity indexing service"""
    service = EntityIndexingService(config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(service.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.initialize()
        await service.start()
    except Exception as e:
        logger.error(f"Indexing service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Configuration
    config = {
        "batch_size": 10,
        "index_interval": 60,
        "relationship_interval": 300,
        "cleanup_interval": 3600,
        "entities_config": {
            "settings": {
                "mongo_url": "mongodb://localhost:27017",
                "database_name": "eva-entities",
                "enable_vectors": True
            }
        }
    }
    
    # Run service
    asyncio.run(run_indexing_service(config))