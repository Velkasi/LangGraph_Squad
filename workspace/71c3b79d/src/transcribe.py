from typing import Any
from langchain_community.document_loaders import UnstructuredFileLoader


class ImageTranscriber:
    """
    Transcribes images into text using UnstructuredFileLoader from LangChain.
    """
    def transcribe(self, image_path: str) -> str:
        """
        Extract text from an image file.

        Args:
            image_path (str): Path to the image file.

        Returns:
            str: Extracted raw text.
        """
        loader = UnstructuredFileLoader(image_path)
        documents = loader.load()
        return " ".join([doc.page_content for doc in documents])
