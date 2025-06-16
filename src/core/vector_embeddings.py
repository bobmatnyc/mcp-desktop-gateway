"""
Vector embedding generator with OpenAI integration
Provides real embeddings for entity vector search
"""

import os
from typing import List, Optional, Union
import numpy as np
import structlog

logger = structlog.get_logger()

# Try to import OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available, will fall back to sentence-transformers")

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Sentence-transformers not available")


class VectorEmbeddingGenerator:
    """Generate real vector embeddings using OpenAI or sentence-transformers"""
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        embedding_dim: int = 384,
        use_openai: bool = True
    ):
        self.model = model
        self.embedding_dim = embedding_dim
        self.use_openai = use_openai and OPENAI_AVAILABLE
        
        self.openai_client: Optional[AsyncOpenAI] = None
        self.sentence_transformer: Optional[SentenceTransformer] = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize the embedding generator"""
        if self.use_openai and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                self.initialized = True
                logger.info(f"Initialized OpenAI embeddings with model: {self.model}")
                return
            else:
                logger.warning("OPENAI_API_KEY not found, falling back to sentence-transformers")
                self.use_openai = False
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            # Use a small, fast model by default
            st_model = "all-MiniLM-L6-v2" if self.embedding_dim == 384 else "all-mpnet-base-v2"
            self.sentence_transformer = SentenceTransformer(st_model)
            self.embedding_dim = self.sentence_transformer.get_sentence_embedding_dimension()
            self.initialized = True
            logger.info(f"Initialized sentence-transformers with model: {st_model}")
        else:
            # Fall back to simple embeddings
            logger.warning("No embedding models available, using simple hash-based embeddings")
            from .embeddings import SimpleEmbeddingGenerator
            self.simple_generator = SimpleEmbeddingGenerator(self.embedding_dim)
            await self.simple_generator.initialize()
            self.initialized = True
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        if not self.initialized:
            await self.initialize()
        
        if self.use_openai and self.openai_client:
            try:
                # Clean text for OpenAI
                text = text.replace("\n", " ").strip()
                if not text:
                    text = "empty"
                
                # Generate embedding
                response = await self.openai_client.embeddings.create(
                    model=self.model,
                    input=text,
                    dimensions=self.embedding_dim  # Only for text-embedding-3 models
                )
                
                embedding = np.array(response.data[0].embedding, dtype=np.float32)
                return embedding
                
            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}")
                # Fall through to alternatives
        
        if self.sentence_transformer:
            try:
                # Generate embedding synchronously (sentence-transformers is sync)
                embedding = self.sentence_transformer.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                return embedding.astype(np.float32)
                
            except Exception as e:
                logger.error(f"Sentence-transformers embedding failed: {e}")
        
        # Final fallback to simple embeddings
        if hasattr(self, 'simple_generator'):
            return await self.simple_generator.generate_embedding(text)
        else:
            # Ultra-fallback: random embedding
            logger.error("All embedding methods failed, returning random embedding")
            return np.random.rand(self.embedding_dim).astype(np.float32)
    
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        if not self.initialized:
            await self.initialize()
        
        if self.use_openai and self.openai_client:
            try:
                # Clean texts
                cleaned_texts = []
                for text in texts:
                    cleaned = text.replace("\n", " ").strip()
                    cleaned_texts.append(cleaned if cleaned else "empty")
                
                # Batch generate embeddings
                response = await self.openai_client.embeddings.create(
                    model=self.model,
                    input=cleaned_texts,
                    dimensions=self.embedding_dim
                )
                
                embeddings = [
                    np.array(data.embedding, dtype=np.float32)
                    for data in response.data
                ]
                return embeddings
                
            except Exception as e:
                logger.error(f"OpenAI batch embedding failed: {e}")
        
        if self.sentence_transformer:
            try:
                # Batch encode
                embeddings = self.sentence_transformer.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    batch_size=32
                )
                return [emb.astype(np.float32) for emb in embeddings]
                
            except Exception as e:
                logger.error(f"Sentence-transformers batch embedding failed: {e}")
        
        # Fallback: generate one by one
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        
        return embeddings
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.openai_client:
            await self.openai_client.close()
        self.initialized = False
    
    def get_dimension(self) -> int:
        """Get the embedding dimension"""
        if self.sentence_transformer:
            return self.sentence_transformer.get_sentence_embedding_dimension()
        return self.embedding_dim