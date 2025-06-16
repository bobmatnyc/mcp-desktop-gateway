"""
Simple embedding generator for entities
Provides text embeddings for vector search functionality
"""

import hashlib
import numpy as np
from typing import Optional, List
import structlog

logger = structlog.get_logger()


class SimpleEmbeddingGenerator:
    """Simple embedding generator using hash-based embeddings as a fallback"""
    
    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
        self.initialized = False
        
    async def initialize(self):
        """Initialize the embedding generator"""
        # For now, we'll use a simple hash-based approach
        # In production, this would initialize OpenAI/sentence-transformers
        self.initialized = True
        logger.info("Simple embedding generator initialized")
        
    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        if not self.initialized:
            await self.initialize()
            
        # Simple hash-based embedding for POC
        # In production, use OpenAI embeddings or sentence-transformers
        hash_object = hashlib.sha256(text.encode())
        hash_hex = hash_object.hexdigest()
        
        # Convert hash to numbers
        embedding = []
        for i in range(0, len(hash_hex), 2):
            value = int(hash_hex[i:i+2], 16) / 255.0  # Normalize to 0-1
            embedding.append(value)
            
        # Pad or truncate to embedding dimension
        if len(embedding) < self.embedding_dim:
            # Pad with hash-derived values
            while len(embedding) < self.embedding_dim:
                embedding.append(embedding[len(embedding) % len(hash_hex) // 2])
        else:
            embedding = embedding[:self.embedding_dim]
            
        return np.array(embedding, dtype=np.float32)
    
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings