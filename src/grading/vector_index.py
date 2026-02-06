
import logging
from typing import Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class VectorIndex:
    """
    A vectorized search index for rapid O(1) similarity matching.
    Uses TF-IDF and Cosine Similarity to find best matches from a corpus.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        self.tfidf_matrix = None
        self.corpus: List[str] = []
        self.metadata: List[Any] = []
        self._is_built = False

    def add(self, text: str, metadata: Any):
        """Add an item to the index."""
        self.corpus.append(text)
        self.metadata.append(metadata)
        self._is_built = False

    def build(self):
        """Build the ID-IDF matrix."""
        if not self.corpus:
            return
            
        logger.info(f"Building VectorIndex with {len(self.corpus)} items...")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        self._is_built = True

    def query(self, text: str, top_k: int = 1, threshold: float = 0.0) -> List[Tuple[Any, float]]:
        """
        Query the index for the most similar items.
        Returns a list of (metadata, score) tuples.
        """
        if not self._is_built or self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([text])
        
        # Calculate cosine similarity: (1, n_features) . (n_samples, n_features).T = (1, n_samples)
        cosine_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top-k indices
        # If top_k is 1, use argmax for speed
        if top_k == 1:
            idx = np.argmax(cosine_sim)
            score = cosine_sim[idx]
            if score >= threshold:
                return [(self.metadata[idx], float(score))]
            return []
            
        # For k > 1, allow partial sorting
        # negative for descending sort
        if len(cosine_sim) > top_k:
             top_indices = np.argpartition(-cosine_sim, top_k)[:top_k]
             # Sort these top k precisely
             top_indices = top_indices[np.argsort(-cosine_sim[top_indices])]
        else:
             top_indices = np.argsort(-cosine_sim)
             
        results = []
        for idx in top_indices:
            score = cosine_sim[idx]
            if score >= threshold:
                results.append((self.metadata[idx], float(score)))
                
        return results
