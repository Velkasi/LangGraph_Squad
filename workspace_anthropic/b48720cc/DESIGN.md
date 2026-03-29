# Architecture — LangChain OCR Pipeline (Mistral Vision)

## Technical Stack

- **OCR / Vision** : `mistral-ocr-latest` via `mistralai` SDK
- **Embeddings** : `sentence-transformers/all-MiniLM-L6-v2` via `langchain-community HuggingFaceEmbeddings`
- **Vector store** : ChromaDB via `langchain-community Chroma` (HTTP client mode)
- **Orchestration** : LangChain only
- **Python** : 3.10

## System Structure

Modular pipeline with single responsibility per file:

```
load_images → transcribe → clean_text → generate_embeddings → store_data
```

Each stage is independent and testable in isolation. `pipeline.py` is the single entry point that wires them together.

## Data Flow

1. `load_image_paths(input_dir)` → `list[str]` of image paths
2. For each path: `transcribe_image(path, client)` → raw OCR text via Mistral Vision API
3. `clean_text(text)` → normalized text (whitespace, empty lines)
4. `generate_embeddings(results)` → `list[Document]` with `all-MiniLM-L6-v2` embeddings
5. `store_documents(docs, host, port)` → stored in ChromaDB collection `ocr_documents`

## Key Interface Contracts

- `transcribe_image` receives a pre-built `Mistral` client (instantiated once in `pipeline.py`)
- `store_documents` uses `chromadb.HttpClient` (not in-memory) — ChromaDB must be running
- `generate_embeddings` instantiates `HuggingFaceEmbeddings` once before the loop
- No call to `vector_store.persist()` — deprecated since ChromaDB 0.4

## ChromaDB

Deployed via `docker-compose.yml` (single service, port 8001→8000). No custom Dockerfile.

## Architecture Decision

**Stack:** mistralai>=1.0.0, langchain-community>=0.2.0, chromadb>=0.5.0, sentence-transformers>=2.2.0
**Structure:** modular pipeline, one file per responsibility, no sub-packages
**Key decisions:** Mistral Vision for OCR (not pytesseract/transformers), HttpClient for ChromaDB (not in-memory), HuggingFaceEmbeddings instantiated once
