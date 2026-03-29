import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


def store_documents(docs: list[Document], host: str, port: int) -> None:
    """Store LangChain Documents into ChromaDB via HTTP client.

    Args:
        docs: list of Document (page_content + metadata)
        host: ChromaDB host
        port: ChromaDB port
    """
    chroma_client = chromadb.HttpClient(host=host, port=port)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    Chroma(
        client=chroma_client,
        collection_name="ocr_documents",
        embedding_function=embeddings,
    ).add_documents(docs)
