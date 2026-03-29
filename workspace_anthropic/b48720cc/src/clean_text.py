import re

def clean_text(text: str) -> str:
    # Normaliser les espaces (replacer 1+ espaces par 1 espace)
    text = re.sub(r'\s+', ' ', text)

    # Supprimer les lignes vides répétées
    lines = text.splitlines()
    non_empty_lines = [line for line in lines if line.strip()]
    text = '\n'.join(non_empty_lines)

    return text