#!/usr/bin/env python3
"""
Generate installer/bimap.ico using Pillow (already a project dependency).

Produces a simple map-pin style icon at 16, 32, 48, 64, and 256 px resolutions.

Usage:
    python installer/create_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw


def _draw_icon(size: int) -> Image.Image:
    """Draw a single-resolution map-pin icon on a transparent background."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer blue circle
    draw.ellipse([0, 0, size - 1, size - 1], fill=(33, 133, 208, 255))

    # White ring
    margin = max(2, size // 5)
    draw.ellipse(
        [margin, margin, size - margin - 1, size - margin - 1],
        fill=(255, 255, 255, 255),
    )

    # Inner blue dot
    center = size // 2
    dot_r = max(1, size // 8)
    draw.ellipse(
        [center - dot_r, center - dot_r, center + dot_r, center + dot_r],
        fill=(33, 133, 208, 255),
    )

    return img


def main() -> None:
    out = Path(__file__).parent / "bimap.ico"
    sizes = [16, 32, 48, 64, 256]
    images = [_draw_icon(s) for s in sizes]

    # PIL wants the largest image first when saving ICO with multiple sizes
    images[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Created {out}  ({', '.join(str(s) for s in sizes)} px)")


if __name__ == "__main__":
    main()
