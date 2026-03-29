# LangChain OCR Pipeline (Mistral Vision)

Pipeline Python modulaire pour transcrire des documents complexes via l'API Mistral Vision et stocker les résultats dans ChromaDB.

## Stack
- **OCR** : `mistral-ocr-latest` via `mistralai` SDK
- **Embeddings** : `sentence-transformers/all-MiniLM-L6-v2` via `langchain-community`
- **Vector store** : ChromaDB HTTP client via `langchain-community`
- **Python** : 3.10+

## Structure

```
src/
├── load_images.py        → load_image_paths(dir) -> list[str]
├── transcribe.py         → transcribe_image(path, client) -> str
├── clean_text.py         → clean_text(text) -> str
├── generate_embeddings.py→ generate_embeddings(results) -> list[Document]
├── store_data.py         → store_documents(docs, host, port)
└── pipeline.py           → run_pipeline(input_dir, chroma_host, chroma_port)
query_example.py          → exemple de recherche dans Chroma
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Renseigner MISTRAL_API_KEY dans .env
```

## Démarrage ChromaDB

```bash
docker compose up -d
```

## Utilisation

```bash
python -m src.pipeline
```

## Recherche

```bash
python query_example.py
```

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `MISTRAL_API_KEY` | Clé API Mistral | — |
| `CHROMA_HOST` | Hôte ChromaDB | `localhost` |
| `CHROMA_PORT` | Port ChromaDB | `8001` |
| `INPUT_DIR` | Répertoire des images | `./images` |
