"""
Core business logic package.

Contains PDF processing, OCR, and PPTX generation modules.
"""
from .geometry import (
    EMU_PER_INCH,
    calculate_slide_dimensions,
    emu_to_px,
    get_aspect_ratio,
    px_to_emu,
    scale_coordinates,
)
from .ocr_processor import OCRProcessor, TextBlock
from .slide_builder import SlideBuilder

__all__ = [
    # Geometry
    "px_to_emu",
    "emu_to_px",
    "calculate_slide_dimensions",
    "scale_coordinates",
    "get_aspect_ratio",
    "EMU_PER_INCH",
    # OCR
    "OCRProcessor",
    "TextBlock",
    # Slide Builder
    "SlideBuilder",
]
