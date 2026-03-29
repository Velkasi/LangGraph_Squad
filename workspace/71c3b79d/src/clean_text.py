import re
from typing import Any

class TextCleaner:
    """
    Cleans and normalizes extracted text.
    """
    def clean(self, text: str) -> str:
        """
        Clean raw extracted text by normalizing whitespace and removing excessive line breaks.

        Args:
            text (str): Raw text from OCR.

        Returns:
            str: Cleaned and normalized text.
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive line breaks
        text = re.sub(r'(\n\s*){3,}', '\n\n', text)
        return text.strip()
