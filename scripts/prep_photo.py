"""
prep_photo.py — turn a raw photo into a clean, high-contrast grayscale
source ready for ASCII conversion.

Usage:
    python scripts/prep_photo.py <input.jpg> <output.png>

Steps:
  1. Remove the background with rembg (subject isolation).
  2. Boost local contrast with OpenCV CLAHE.
  3. Composite onto pure white so the background maps to the blank
     end of the ASCII ramp (white -> spaces).
"""

import sys
import io
import numpy as np
import cv2
from PIL import Image
from rembg import remove


def prep(input_path: str, output_path: str) -> None:
    with open(input_path, "rb") as f:
        raw = f.read()

    # 1. Background removal -> RGBA with alpha mask of the subject
    cutout_bytes = remove(raw)
    cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")

    # 1b. rembg's raw alpha is often noisy on busy backgrounds (rocks,
    # foliage, textured snow get partially included). Hard-threshold it,
    # keep only the largest connected blob (the person), then feather
    # the edge back slightly so it doesn't look cut with scissors.
    alpha = np.array(cutout.split()[-1])
    _, mask = cv2.threshold(alpha, 180, 255, cv2.THRESH_BINARY)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels > 1:
        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    cutout.putalpha(Image.fromarray(mask))

    # 2. Composite onto pure white using the cleaned alpha mask
    white_bg = Image.new("RGBA", cutout.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, cutout).convert("RGB")

    # 3. Convert to grayscale + CLAHE contrast boost
    gray = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    boosted = clahe.apply(gray)

    Image.fromarray(boosted).save(output_path)
    print(f"wrote {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python prep_photo.py <input.jpg> <output.png>")
        sys.exit(1)
    prep(sys.argv[1], sys.argv[2])
