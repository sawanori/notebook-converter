"""
Coordinate conversion utilities.

Converts between pixel coordinates and PowerPoint EMUs (English Metric Units).
Calculates slide dimensions based on PDF/image aspect ratio.
"""
from __future__ import annotations

from typing import Tuple

# Constants
EMU_PER_INCH = 914400  # 1 inch = 914400 EMU

# Standard slide dimensions (for reference)
STANDARD_SLIDE_WIDTH_EMU = 9144000   # 10 inches
STANDARD_SLIDE_HEIGHT_EMU = 6858000  # 7.5 inches


def px_to_emu(pixels: int, dpi: int = 300) -> int:
    """
    Convert pixels to EMU (English Metric Units).

    Args:
        pixels: Number of pixels.
        dpi: Dots per inch of the source image (default: 300).

    Returns:
        EMU value as integer.

    Example:
        >>> px_to_emu(300, 300)  # 1 inch at 300 DPI
        914400
    """
    inches = pixels / dpi
    return int(inches * EMU_PER_INCH)


def emu_to_px(emu: int, dpi: int = 300) -> int:
    """
    Convert EMU to pixels.

    Args:
        emu: EMU value.
        dpi: Target DPI (default: 300).

    Returns:
        Pixel value as integer.
    """
    inches = emu / EMU_PER_INCH
    return int(inches * dpi)


def calculate_slide_dimensions(
    image_width_px: int,
    image_height_px: int,
    dpi: int = 300
) -> Tuple[int, int]:
    """
    Calculate slide dimensions from image size.

    Maintains the aspect ratio of the PDF/image to create
    appropriately sized slides.

    Args:
        image_width_px: Image width in pixels.
        image_height_px: Image height in pixels.
        dpi: Image DPI (default: 300).

    Returns:
        Tuple of (width_emu, height_emu).

    Example:
        >>> calculate_slide_dimensions(3000, 2250, 300)  # 10x7.5 inches
        (9144000, 6858000)
    """
    width_emu = px_to_emu(image_width_px, dpi)
    height_emu = px_to_emu(image_height_px, dpi)
    return (width_emu, height_emu)


def scale_coordinates(
    x: int,
    y: int,
    width: int,
    height: int,
    source_dpi: int,
    target_dpi: int = 300
) -> Tuple[int, int, int, int]:
    """
    Scale coordinates between different DPI values.

    Useful when working with images at different resolutions.

    Args:
        x: X coordinate.
        y: Y coordinate.
        width: Width value.
        height: Height value.
        source_dpi: Source DPI.
        target_dpi: Target DPI (default: 300).

    Returns:
        Tuple of scaled (x, y, width, height).
    """
    scale = target_dpi / source_dpi
    return (
        int(x * scale),
        int(y * scale),
        int(width * scale),
        int(height * scale)
    )


def get_aspect_ratio(width: int, height: int) -> float:
    """
    Calculate aspect ratio (width / height).

    Args:
        width: Width value.
        height: Height value.

    Returns:
        Aspect ratio as float.

    Raises:
        ValueError: If height is zero.
    """
    if height == 0:
        raise ValueError("Height cannot be zero")
    return width / height
