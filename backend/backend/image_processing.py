import cv2
import numpy as np
import os

def load_and_threshold_image(image_path, debug_dir=None):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "thresholded.png"), binary)

    # Convert to boolean bitmap for potrace
    bitmap = (binary > 0).astype(np.uint8)
    return bitmap
