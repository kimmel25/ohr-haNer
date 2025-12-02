"""
Vector Search Engine - BEREL-based Similarity Search
====================================================

This module handles vector similarity search using BEREL (Dicta's Hebrew BERT) embeddings.

How it works:
1. Pre-computed embeddings stored in embeddings/ directory (created once from Sefaria export)
2. User query gets embedded using BEREL
3. Cosine similarity finds closest matches
4. Returns top-k candidates for Claude verification

Setup required:
- Run prepare_sefaria_embeddings.py once to create embeddings
- Embeddings are cached and never need regeneration (unless Sefaria updates)
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path

# BEREL imports
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    BEREL_AVAILABLE = True
except ImportError:
    BEREL_AVAILABLE = False

from logging_config import get_logger

logger = get_logger(__name__)


class VectorSearchEngine:
    """
    Handles vector similarity search using BEREL embeddings.
    
    Directory structure:
        embeddings/
            metadata.json      # Index of all texts with references
            embeddings.npy     # Numpy array of all embeddings
    """
    
    def __init__(self, embeddings_dir: str = "embeddings"):
        self.embeddings_dir = Path(__file__).parent / embeddings_dir
        self.model = None
        self.tokenizer = None
        self.embeddings = None
        self.metadata = None
        self.loaded = False
        
        logger.info(f"VectorSearchEngine initializing...")
        logger.info(f"  Embeddings directory: {self.embeddings_dir}")
        
        # Check if BEREL is available
        if not BEREL_AVAILABLE:
            logger.error("  ✗ BEREL not available! Install: pip install transformers torch")
            logger.error("  Vector search will not work until dependencies are installed")
            return
        
        # Try to load embeddings (lazy loading - only when needed)
        # We don't load in __init__ to keep startup fast
        logger.info("  ✓ BEREL dependencies available")
        logger.info("  Note: Embeddings will be loaded on first search")
    
    def _load_berel_model(self):
        """Load BEREL model and tokenizer (lazy loading)"""
        if self.model is not None:
            return  # Already loaded
        
        logger.info("Loading BEREL model...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("dicta-il/BEREL")
            self.model = AutoModel.from_pretrained("dicta-il/BEREL")
            self.model.eval()  # Set to evaluation mode
            
            logger.info("  ✓ BEREL model loaded successfully")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to load BEREL model: {e}")
            raise
    
    def _load_embeddings(self):
        """Load pre-computed embeddings and metadata (lazy loading)"""
        if self.loaded:
            return  # Already loaded
        
        logger.info("Loading pre-computed embeddings...")
        
        # Check if embeddings exist
        metadata_path = self.embeddings_dir / "metadata.json"
        embeddings_path = self.embeddings_dir / "embeddings.npy"
        
        if not metadata_path.exists() or not embeddings_path.exists():
            logger.error("  ✗ Embeddings not found!")
            logger.error(f"  Expected files:")
            logger.error(f"    - {metadata_path}")
            logger.error(f"    - {embeddings_path}")
            logger.error("")
            logger.error("  TO SETUP:")
            logger.error("  1. Run: python prepare_sefaria_embeddings.py")
            logger.error("  2. Wait ~4 hours for embedding creation")
            logger.error("  3. Then restart the backend")
            logger.error("")
            logger.error("  Vector search unavailable until setup is complete")
            return
        
        try:
            # Load metadata (list of all text references)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            # Load embeddings (numpy array)
            self.embeddings = np.load(embeddings_path)
            
            logger.info(f"  ✓ Loaded {len(self.metadata)} text embeddings")
            logger.info(f"  ✓ Embedding dimension: {self.embeddings.shape[1]}")
            
            self.loaded = True
            
        except Exception as e:
            logger.error(f"  ✗ Failed to load embeddings: {e}")
            raise
    
    def _embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single text using BEREL.
        
        Returns 768-dimensional embedding vector.
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use [CLS] token embedding (first token)
        embedding = outputs.last_hidden_state[0][0].numpy()
        
        return embedding
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Search for texts similar to query.
        
        Args:
            query: User's search query (can be transliteration)
            top_k: Number of top matches to return
        
        Returns:
            List of matches with scores and metadata:
            [
                {
                    'ref': 'Chullin 10a',
                    'he_text': 'Hebrew text...',
                    'en_text': 'English text...',
                    'score': 0.742,
                    'rank': 1
                },
                ...
            ]
        """
        logger.debug(f"Vector search for: '{query}' (top_k={top_k})")
        
        # Ensure model and embeddings are loaded
        try:
            if not BEREL_AVAILABLE:
                logger.error("BEREL not available - cannot perform vector search")
                return []
            
            self._load_berel_model()
            self._load_embeddings()
            
            if not self.loaded:
                logger.error("Embeddings not loaded - cannot perform vector search")
                return []
            
        except Exception as e:
            logger.error(f"Failed to initialize vector search: {e}")
            return []
        
        # Embed the query
        try:
            query_embedding = self._embed_text(query)
            logger.debug(f"  Query embedded (shape: {query_embedding.shape})")
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []
        
        # Compute similarities with all texts
        similarities = []
        for i, embedding in enumerate(self.embeddings):
            score = self._cosine_similarity(query_embedding, embedding)
            similarities.append((i, score))
        
        # Sort by score (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top-k matches
        top_matches = similarities[:top_k]
        
        # Build result list with metadata
        results = []
        for rank, (idx, score) in enumerate(top_matches, 1):
            if idx >= len(self.metadata):
                logger.warning(f"Index {idx} out of bounds for metadata")
                continue
            
            meta = self.metadata[idx]
            
            results.append({
                'rank': rank,
                'score': float(score),
                'ref': meta.get('ref', ''),
                'he_text': meta.get('he_text', ''),
                'en_text': meta.get('en_text', ''),
                'category': meta.get('category', '')
            })
        
        logger.debug(f"  Top 3 matches:")
        for r in results[:3]:
            logger.debug(f"    [{r['rank']}] {r['ref']} (score: {r['score']:.3f})")
        
        return results
    
    def is_ready(self) -> bool:
        """Check if vector search is ready to use"""
        if not BEREL_AVAILABLE:
            return False
        
        metadata_path = self.embeddings_dir / "metadata.json"
        embeddings_path = self.embeddings_dir / "embeddings.npy"
        
        return metadata_path.exists() and embeddings_path.exists()


# Global instance
_engine = None


def get_engine() -> VectorSearchEngine:
    """Get global vector search engine instance"""
    global _engine
    if _engine is None:
        _engine = VectorSearchEngine()
    return _engine