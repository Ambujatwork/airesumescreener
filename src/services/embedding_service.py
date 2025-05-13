from typing import List, Optional, Dict, Any, Union
import os
import numpy as np
import logging
import asyncio
from datetime import datetime
import openai
from openai import AsyncAzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class EmbeddingService:
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        # Default model for embeddings
        self.embedding_model = "text-embedding-ada-002"  # Azure's embedding model name
        self.embedding_dimension = 1536  # Default dimension for ada-002 model
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def generate_embedding(self, text: str) -> List[float]:
        
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            # Return zero vector with correct dimensionality
            return [0.0] * self.embedding_dimension
            
        try:
            # Truncate text if necessary (model has token limits)
            truncated_text = text[:8000]  # Reasonable limit for most embedding models
            
            response = await self.client.embeddings.create(
                input=[truncated_text],
                model=self.embedding_model
            )
            
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Process batch concurrently
            batch_results = await asyncio.gather(
                *[self.generate_embedding(text) for text in batch]
            )
            results.extend(batch_results)
            
        return results
            
    def compute_similarity(self, embedding1: Union[List[float], np.ndarray], embedding2: Union[List[float], np.ndarray]) -> float:
        
        try:
            # Check for empty or None embeddings
            if embedding1 is None or embedding2 is None:
                return 0.0
                
            if isinstance(embedding1, list) and len(embedding1) == 0:
                return 0.0
                
            if isinstance(embedding2, list) and len(embedding2) == 0:
                return 0.0
                
            # Convert to numpy arrays if they aren't already
            if not isinstance(embedding1, np.ndarray):
                vec1 = np.array(embedding1, dtype=np.float32)
            else:
                vec1 = embedding1
                
            if not isinstance(embedding2, np.ndarray):
                vec2 = np.array(embedding2, dtype=np.float32)
            else:
                vec2 = embedding2
            
            # Compute cosine similarity
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            # Check for zero norms to avoid division by zero
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            # Calculate dot product and normalize
            dot_product = np.dot(vec1, vec2)
            
            # Handle the case when dot_product is an array
            if isinstance(dot_product, np.ndarray):
                # This means we're dealing with multi-dimensional embeddings
                dot_product = float(np.sum(dot_product))
                
            # Calculate similarity
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure the result is a scalar
            if isinstance(similarity, np.ndarray):
                if similarity.size == 1:
                    similarity = float(similarity.item())
                else:
                    # If we have an array with multiple values, take the mean
                    similarity = float(np.mean(similarity))
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            return 0.0