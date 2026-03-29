from src.load_images import ImageLoader
from src.transcribe import ImageTranscriber
from src.clean_text import TextCleaner
from src.generate_embeddings import EmbeddingGenerator
from src.store_data import ChromaDBStorage
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description='Document Processing Pipeline')
    parser.add_argument('--input-dir', required=True, help='Directory containing input images')
    parser.add_argument('--chroma-host', default='localhost', help='ChromaDB host')
    parser.add_argument('--chroma-port', type=int, default=8000, help='ChromaDB port')
    args = parser.parse_args()

    # Initialize components
    image_loader = ImageLoader()
    transcriber = ImageTranscriber()
    cleaner = TextCleaner()
    embedder = EmbeddingGenerator()
    storage = ChromaDBStorage(host=args.chroma_host, port=args.chroma_port)

    # Load images
    image_paths = image_loader.load_images(args.input_dir)
    
    # Transcribe
    raw_documents = []
    for path in image_paths:
        text = transcriber.transcribe_image(path)
        raw_documents.append(text)
    
    # Clean text
    cleaned_documents = [cleaner.clean(text) for text in raw_documents]
    
    # Generate embeddings
    embeddings = embedder.generate(cleaned_documents)
    
    # Store in ChromaDB
    ids = [f"doc_{i}" for i in range(len(cleaned_documents))]
    storage.store(ids=ids, documents=cleaned_documents, embeddings=embeddings)
    
    print(f"Successfully processed {len(image_paths)} documents and stored in ChromaDB.")

if __name__ == "__main__":
    main()
