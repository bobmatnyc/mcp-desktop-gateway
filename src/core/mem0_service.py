from mem0 import Memory
from typing import Dict, List, Optional, Any
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Mem0Service:
    """Simplified memory service using mem0."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mem0 with configuration."""
        self.config = config
        
        # Extract mem0 config
        mem0_config = config.get("mem0_config", {})
        
        # If no embedder specified, use defaults that don't require API keys
        if "embedder" not in mem0_config:
            # Use default embeddings (no API key required)
            mem0_config["embedder"] = {
                "provider": "huggingface",
                "config": {
                    "model": "sentence-transformers/all-MiniLM-L6-v2"
                }
            }
            
        # Remove llm key if not specified to avoid API key requirement
        if "llm" in mem0_config and mem0_config["llm"] is None:
            del mem0_config["llm"]
        
        # Set up API keys from environment if needed
        if "embedder" in mem0_config and mem0_config["embedder"]:
            if mem0_config["embedder"].get("provider") == "openai":
                api_key = mem0_config["embedder"]["config"].get("api_key", "")
                if api_key.startswith("${") and api_key.endswith("}"):
                    env_var = api_key[2:-1]
                    mem0_config["embedder"]["config"]["api_key"] = os.getenv(env_var, "")
        
        if "llm" in mem0_config and mem0_config["llm"]:
            if mem0_config["llm"].get("provider") == "openai":
                api_key = mem0_config["llm"]["config"].get("api_key", "")
                if api_key.startswith("${") and api_key.endswith("}"):
                    env_var = api_key[2:-1]
                    mem0_config["llm"]["config"]["api_key"] = os.getenv(env_var, "")
        
        try:
            # Validate configuration
            if not mem0_config.get("vector_store"):
                logger.warning("No vector_store configured for mem0, using defaults")
                mem0_config["vector_store"] = {
                    "provider": "qdrant",
                    "config": {
                        "host": "localhost",
                        "port": 6333,
                        "collection_name": "mem0_memories"
                    }
                }
            
            # Log final configuration
            logger.info(f"Initializing mem0 with config: {mem0_config}")
            
            self.memory = Memory.from_config(mem0_config)
            self.default_user_id = "bob_matsuoka"
            logger.info("Mem0Service initialized successfully")
            
            # Test connection
            try:
                test_result = self.memory.add("test", user_id="test_init")
                logger.debug(f"mem0 test result: {test_result}")
            except Exception as test_error:
                logger.warning(f"mem0 test failed (non-fatal): {test_error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize mem0: {e}")
            logger.error(f"Config was: {mem0_config}")
            raise
        
    async def add_memory(
        self, 
        text: str, 
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a memory and return its ID."""
        try:
            result = self.memory.add(
                text, 
                user_id=user_id or self.default_user_id,
                metadata=metadata or {}
            )
            
            # Handle mem0's response format
            # mem0 returns: {'results': [{'id': 'xxx', 'memory': 'text', 'event': 'ADD'}, ...]}
            if isinstance(result, dict) and 'results' in result:
                results = result.get('results', [])
                if results:
                    # Return the first memory ID
                    first_result = results[0]
                    memory_id = first_result.get('id', '')
                    logger.info(f"Added {len(results)} memory chunk(s), returning first ID: {memory_id}")
                    return memory_id
                else:
                    logger.warning(f"mem0 returned empty results for text: {text[:100]}...")
                    logger.debug(f"Full mem0 response: {result}")
                    # Log configuration for debugging
                    logger.debug(f"mem0 config: {self.config.get('mem0_config', {})}")
                    return ""
            elif isinstance(result, dict) and 'error' in result:
                logger.error(f"mem0 error: {result.get('error')}")
                raise Exception(f"mem0 error: {result.get('error')}")
            else:
                # Fallback for other formats
                memory_id = result.get('id', '') if isinstance(result, dict) else str(result)
                logger.info(f"Added memory: {memory_id}")
                return memory_id
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise
    
    async def search_memories(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Search memories and return results."""
        try:
            result = self.memory.search(
                query, 
                user_id=user_id or self.default_user_id,
                limit=limit,
                filters=filters
            )
            
            # Handle mem0's response format
            # mem0 returns: {'results': [...]}
            if isinstance(result, dict) and 'results' in result:
                memories = result.get('results', [])
                logger.info(f"Found {len(memories)} memories for query: {query}")
                return memories
            elif isinstance(result, list):
                # Fallback if it returns a list directly
                return result
            else:
                logger.warning(f"Unexpected search result format: {type(result)}")
                return []
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_all_memories(
        self, 
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """Get all memories for a user."""
        try:
            result = self.memory.get_all(user_id=user_id or self.default_user_id)
            
            # Handle mem0's response format
            # mem0 returns: {'results': [...]}
            if isinstance(result, dict) and 'results' in result:
                memories = result.get('results', [])
                logger.info(f"Retrieved {len(memories)} memories")
                return memories
            elif isinstance(result, list):
                # Fallback if it returns a list directly
                return result
            else:
                logger.warning(f"Unexpected get_all result format: {type(result)}")
                return []
        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []
    
    async def delete_memory(
        self, 
        memory_id: str, 
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a specific memory."""
        try:
            self.memory.delete(memory_id, user_id=user_id or self.default_user_id)
            logger.info(f"Deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False
    
    async def update_memory(
        self, 
        memory_id: str, 
        text: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update an existing memory."""
        try:
            self.memory.update(
                memory_id, 
                text,
                user_id=user_id or self.default_user_id,
                metadata=metadata
            )
            logger.info(f"Updated memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False
    
    def get_timestamp(self) -> str:
        """Get current timestamp."""
        return datetime.utcnow().isoformat()