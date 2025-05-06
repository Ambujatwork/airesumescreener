import os
import logging
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating embeddings using Azure OpenAI.
    Updated to use the newer OpenAI client library.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            # Get API credentials from environment variables
            self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
            self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
            self.model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
            self.max_token_length = 8191  # Max tokens for embedding model

            # Initialize the client
            self.client = AzureOpenAI(
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
                api_key=self.api_key
            )
            
            self._initialized = True
            logger.info("EmbeddingService initialized successfully.")
            
        except Exception as e:
            logger.error(f"Failed to initialize EmbeddingService: {str(e)}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for the given text using Azure OpenAI.
        Returns an empty list if there's an error.
        """
        if not text:
            logger.warning("Empty text provided for embedding generation")
            return []
            
        try:
            # Truncate text if needed to fit model's context window
            truncated_text = text[:self.max_token_length]
            
            response = self.client.embeddings.create(
                model=self.model,
                input=truncated_text
            )
            
            # Extract the embedding from the response
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return []
            
    def get_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two text strings.
        Returns a value between 0 and 1, where 1 is the highest similarity.
        """
        import numpy as np
        
        if not text1 or not text2:
            return 0.0
            
        try:
            # Generate embeddings
            embedding1 = self.generate_embedding(text1)
            embedding2 = self.generate_embedding(text2)
            
            if not embedding1 or not embedding2:
                return 0.0
                
            # Calculate cosine similarity
            a = np.array(embedding1)
            b = np.array(embedding2)
            
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating text similarity: {str(e)}")
            return 0.0