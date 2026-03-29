# Prompt — LangChain OCR Pipeline (Mistral Vision)

## Objectif
Créer un pipeline Python modulaire utilisant LangChain pour transcrire des documents complexes (tableaux, formulaires, mise en page multi-colonnes) via l'API Mistral Vision et stocker le résultat dans ChromaDB.

## Stack imposée (ne pas dévier)
- **OCR / Vision** : `mistral-ocr-latest` via API Mistral (`mistralai` SDK)
- **Embeddings** : `sentence-transformers/all-MiniLM-L6-v2` via `langchain-community` `HuggingFaceEmbeddings`
- **Vector store** : ChromaDB via `langchain-community` `Chroma` (mode HTTP client)
- **Orchestration** : LangChain uniquement
- **Python** : 3.10

## Fichiers à produire — liste exhaustive

Un seul fichier par responsabilité. Pas de doublon, pas de sous-dossier.

```
src/
├── load_images.py          → load_images_from_directory(dir: str) -> list[str]
├── transcribe.py           → transcribe_image(image_path: str, client: Mistral) -> str
├── clean_text.py           → clean_text(text: str) -> str
├── generate_embeddings.py  → generate_embeddings(results: list[tuple[str,str]]) -> list[Document]
├── store_data.py           → store_documents(docs: list[Document], host: str, port: int) -> None
└── pipeline.py             → run_pipeline(input_dir, chroma_host, chroma_port) — point d'entrée
requirements.txt            → à la racine uniquement
docker-compose.yml          → ChromaDB uniquement
.env.example
query_example.py            → exemple de recherche dans Chroma
```

## Contrats d'interface stricts

### `transcribe.py`
- Utiliser le modèle `mistral-ocr-latest` via `mistralai` SDK
- Encoder l'image en base64 et l'envoyer comme `image_url` avec le prefix `data:image/jpeg;base64,`
- Prompt système : `"Extract all text from this document. Preserve the structure: titles, paragraphs, tables, lists. Return plain text only."`
- Retourner le contenu texte de la première `choice.message.content`
- Raise `FileNotFoundError` si le fichier n'existe pas
- Raise `MistralAPIException` si l'appel échoue (ne pas silencer)

Exemple d'appel :
```python
import base64
from mistralai import Mistral

def transcribe_image(image_path: str, client: Mistral) -> str:
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.complete(
        model="mistral-ocr-latest",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract all text from this document. Preserve the structure: titles, paragraphs, tables, lists. Return plain text only."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        }]
    )
    return response.choices[0].message.content.strip()
```

### `pipeline.py`
- Instancier `Mistral(api_key=os.getenv("MISTRAL_API_KEY"))` une seule fois
- Passer le client à `transcribe_image` — ne pas le réinstancier dans la boucle
- Logger chaque image traitée avec succès et chaque erreur
- Continuer le pipeline si une image échoue (ne pas arrêter)

### `generate_embeddings.py`
- Instancier `HuggingFaceEmbeddings` **une seule fois** avant la boucle
- Retourne `list[Document]` avec `page_content=text` et `metadata={"source": image_path}`

### `store_data.py`
- Utilise `chromadb.HttpClient(host=host, port=port)`
- Utilise `Chroma(client=chroma_client, collection_name="ocr_documents", embedding_function=embeddings)`
- **Ne pas appeler** `vector_store.persist()` — deprecated depuis ChromaDB 0.4
- Raise si la connexion ChromaDB échoue

### `clean_text.py`
- Normaliser les espaces (`re.sub(r'\s+', ' ', text)`)
- Supprimer les lignes vides répétées
- **Ne pas remplacer** les chiffres par des lettres

### `docker-compose.yml`
- Service `chromadb` uniquement, image `chromadb/chroma:latest`
- Port exposé : `8001:8000`
- Variable `CHROMA_SERVER_HTTP_PORT=8000`
- Pas de `build:`, pas de Dockerfile custom

### `requirements.txt`
```
mistralai>=1.0.0
langchain-community>=0.2.0
langchain-core>=0.2.0
chromadb>=0.5.0
sentence-transformers>=2.2.0
Pillow>=10.0.0
python-dotenv>=1.0.0
```
- **Ne pas inclure** : `pytesseract`, `tensorflow`, `torch`, `transformers`, `tesseract-ocr`

## `.env.example`
```
MISTRAL_API_KEY=your_mistral_api_key_here
CHROMA_HOST=localhost
CHROMA_PORT=8001
INPUT_DIR=./images
```

## `query_example.py`
Montrer comment :
1. Se connecter à Chroma en HTTP
2. Instancier les mêmes embeddings `all-MiniLM-L6-v2`
3. Faire une recherche par similarité avec une question textuelle
4. Afficher les résultats avec leur score et métadonnée `source`

## Gestion d'erreurs
- Image illisible ou format non supporté → logger et continuer
- Clé API Mistral manquante → raise `ValueError` au démarrage de `run_pipeline`
- ChromaDB inaccessible → raise avec message clair
- Réponse Mistral vide → logger un warning et sauter l'image
