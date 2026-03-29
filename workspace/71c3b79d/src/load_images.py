import os
from typing import List


class ImageLoader:
    """
    Load image files from a directory.
    """
    def __init__(self):
        pass

    def load_images(self, directory: str) -> List[str]:
        """
        Load all image files (PNG, JPG, JPEG) from the input directory.

        Args:
            directory (str): Path to the input directory.

        Returns:
            List[str]: List of image file paths.
        """
        supported_extensions = ('.png', '.jpg', '.jpeg')
        if not os.path.isdir(directory):
            raise ValueError(f"Directory not found: {directory}")

        image_paths = [
            os.path.join(directory, file)
            for file in os.listdir(directory)
            if file.lower().endswith(supported_extensions)
        ]
        
        if not image_paths:
            raise ValueError(f"No supported image files found in {directory}")

        return image_paths
