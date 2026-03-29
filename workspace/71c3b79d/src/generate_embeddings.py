from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingGenerator:
    """
    Generates embeddings for text using Sentence-BERT model.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.

        Args:
            model_name (str): Name of the pre-trained Sentence-BERT model.
        """
        self.model = SentenceTransformer(model_name)

    def generate(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts (List[str]): List of texts to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        return self.model.encode(texts).tolist()
