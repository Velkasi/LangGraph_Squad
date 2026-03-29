import os
from pathlib import Path
from typing import List

def load_image_paths(input_dir: str) -> List[str]:
    """Load all image file paths from input directory."""
    directory = Path(input_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    supported_extensions = ['.png', '.jpg', '.jpeg']
    image_paths = []
    
    for ext in supported_extensions:
        image_paths.extend(directory.glob(f"*{ext}"))
    
    return [str(path) for path in image_paths]
