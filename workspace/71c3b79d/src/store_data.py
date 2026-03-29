from chromadb import Client
from chromadb.config import Settings
from typing import List


class ChromaDBStorage:
    """
    Stores documents and their embeddings in ChromaDB.
    """
    def __init__(self, host: str = "localhost", port: int = 8000):
        """
        Initialize connection to ChromaDB.

        Args:
            host (str): ChromaDB server host.
            port (int): ChromaDB server port.
        """
        self.client = Client(Settings(chroma_api_impl="rest", chroma_server_host=host, chroma_server_port=port))
        self.collection = self.client.get_or_create_collection(name="document-store")

    def store(self, ids: List[str], documents: List[str], embeddings: List[List[float]]):
        """
        Store documents with embeddings in ChromaDB.

        Args:
            ids (List[str]): Document IDs.
            documents (List[str]): Document texts.
            embeddings (List[List[float]]): Embeddings for the documents.
        """
        self.collection.add(ids=ids, documents=documents, embeddings=embeddings)
