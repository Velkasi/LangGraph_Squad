## README.md

Project Overview
---------------

This project aims to develop a transcription and embedding pipeline using ChromaDB.

### Architecture Summary

The pipeline consists of several components, including image loading, transcription, text cleaning, embedding generation, and data storage in ChromaDB.

### Setup Instructions

1. Install the requirements using `pip install -r requirements.txt`.
2. Deploy ChromaDB using `docker-compose up -d`.
3. Run the pipeline using `python pipeline.py` with the required arguments.

### Docker Usage

This project uses Docker to deploy ChromaDB. Make sure to pull the ChromaDB image before running the pipeline.

### Environment Variables

The project requires several environment variables to be set, including `CHROMA_HOST` and `CHROMA_PORT`.

### API Endpoints

The project does not include any API endpoints.

## TODO

1. Implement error handling and logging mechanisms.
2. Optimize the pipeline for performance.
3. Expand the project to include more features.
