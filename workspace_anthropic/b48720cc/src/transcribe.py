import base64
from mistralai import Mistral


def transcribe_image(image_path: str, client: Mistral) -> str:
    """Extract text from an image using Mistral OCR API."""
    if not __import__("os").path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.complete(
        model="mistral-ocr-latest",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this document. Preserve the structure: titles, paragraphs, tables, lists. Return plain text only."
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                }
            ]
        }]
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Mistral returned empty response")
    return content.strip()
