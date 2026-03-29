import logging
import os

from dotenv import load_dotenv
from mistralai import Mistral

from src.clean_text import clean_text
from src.generate_embeddings import generate_embeddings
from src.load_images import load_image_paths
from src.store_data import store_documents
from src.transcribe import transcribe_image

load_dotenv()

logger = logging.getLogger(__name__)


def run_pipeline(input_dir: str, chroma_host: str, chroma_port: int) -> None:
    """Run the full OCR → embed → store pipeline.

    Args:
        input_dir: directory containing images to process
        chroma_host: ChromaDB HTTP host
        chroma_port: ChromaDB HTTP port
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set")

    client = Mistral(api_key=api_key)

    image_paths = load_image_paths(input_dir)
    if not image_paths:
        logger.warning("No images found in %s", input_dir)
        return

    results: list[tuple[str, str]] = []
    for path in image_paths:
        try:
            raw = transcribe_image(path, client)
            text = clean_text(raw)
            results.append((path, text))
            logger.info("Transcribed: %s", path)
        except Exception as exc:
            logger.error("Failed to transcribe %s: %s", path, exc)

    if not results:
        logger.warning("No images were successfully transcribed")
        return

    docs = generate_embeddings(results)
    store_documents(docs, host=chroma_host, port=chroma_port)
    logger.info("Stored %d documents in ChromaDB", len(docs))


if __name__ == "__main__":
    run_pipeline(
        input_dir=os.getenv("INPUT_DIR", "./images"),
        chroma_host=os.getenv("CHROMA_HOST", "localhost"),
        chroma_port=int(os.getenv("CHROMA_PORT", "8001")),
    )
