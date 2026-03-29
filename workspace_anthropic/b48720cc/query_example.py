"""Example: query the ChromaDB OCR collection by similarity."""
import os

import chromadb
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

chroma_host = os.getenv("CHROMA_HOST", "localhost")
chroma_port = int(os.getenv("CHROMA_PORT", "8001"))

chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vector_store = Chroma(
    client=chroma_client,
    collection_name="ocr_documents",
    embedding_function=embeddings,
)

query = "invoice total amount"
results = vector_store.similarity_search_with_score(query, k=3)

for doc, score in results:
    print(f"Score: {score:.4f} | Source: {doc.metadata.get('source')}")
    print(doc.page_content[:300])
    print("---")
