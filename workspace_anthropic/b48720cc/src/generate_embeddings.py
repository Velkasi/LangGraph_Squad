from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


def generate_embeddings(results: list[tuple[str, str]]) -> list[Document]:
    """Convert (image_path, text) pairs into LangChain Documents with embeddings metadata.

    Args:
        results: list of (image_path, transcribed_text) tuples

    Returns:
        list of Document with page_content=text and metadata={'source': image_path}
    """
    # Instantiate once before the loop
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # noqa: F841

    docs = []
    for image_path, text in results:
        if not text.strip():
            continue
        docs.append(Document(
            page_content=text,
            metadata={"source": image_path}
        ))
    return docs
