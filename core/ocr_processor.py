"""
OCR processing module.

Handles text extraction from images using Tesseract OCR
and intelligent text grouping into blocks/paragraphs.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytesseract
from PIL import Image

try:
    from config.defaults import (
        LINE_MERGE_THRESHOLD_PX,
        OCR_CONFIDENCE_THRESHOLD,
        OCR_LANGUAGES,
        PARAGRAPH_GAP_MULTIPLIER,
    )
except ImportError:
    from ..config.defaults import (
        LINE_MERGE_THRESHOLD_PX,
        OCR_CONFIDENCE_THRESHOLD,
        OCR_LANGUAGES,
        PARAGRAPH_GAP_MULTIPLIER,
    )

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Represents a grouped text block with position information."""
    
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float

    @property
    def right(self) -> int:
        """Right edge coordinate."""
        return self.left + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge coordinate."""
        return self.top + self.height

    @property
    def center_x(self) -> int:
        """Center X coordinate."""
        return self.left + self.width // 2

    @property
    def center_y(self) -> int:
        """Center Y coordinate."""
        return self.top + self.height // 2


class OCRProcessor:
    """
    Handles OCR processing and text block grouping.
    
    Uses Tesseract for text recognition and implements
    intelligent grouping of words into lines and paragraphs.
    """

    def __init__(
        self,
        tesseract_path: str,
        languages: str = OCR_LANGUAGES
    ):
        """
        Initialize the OCR processor.

        Args:
            tesseract_path: Path to tesseract executable.
            languages: OCR languages (e.g., "jpn+eng").

        Raises:
            FileNotFoundError: If tesseract executable not found.
        """
        self.tesseract_path = tesseract_path
        self.languages = languages

        # Validate tesseract path
        if not Path(tesseract_path).exists():
            raise FileNotFoundError(
                f"Tesseract executable not found: {tesseract_path}"
            )

        # Configure pytesseract
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.info(f"OCR initialized with languages: {languages}")

    def extract_text_blocks(
        self,
        image: Image.Image,
        stop_event: Optional[threading.Event] = None
    ) -> List[TextBlock]:
        """
        Extract text blocks from an image.

        Performs OCR and groups results into logical text blocks.

        Args:
            image: PIL Image to process.
            stop_event: Optional event to signal cancellation.

        Returns:
            List of TextBlock objects with grouped text.
        """
        if stop_event and stop_event.is_set():
            logger.debug("OCR cancelled before start")
            return []

        logger.debug(f"Starting OCR on image: {image.size}")

        try:
            # Run Tesseract OCR
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.languages,
                output_type=pytesseract.Output.DICT
            )
        except pytesseract.TesseractError as e:
            logger.error(f"Tesseract error: {e}")
            return []

        if stop_event and stop_event.is_set():
            logger.debug("OCR cancelled after Tesseract")
            return []

        # Extract valid words
        words = self._extract_words(ocr_data)
        logger.debug(f"Extracted {len(words)} words")

        if not words:
            return []

        # Group words into lines
        lines = self._group_into_lines(words)
        logger.debug(f"Grouped into {len(lines)} lines")

        # Group lines into paragraphs/blocks
        blocks = self._group_into_paragraphs(lines)
        logger.debug(f"Created {len(blocks)} text blocks")

        return blocks

    def _extract_words(self, ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract valid words from OCR data.

        Filters out empty text and low-confidence results.

        Args:
            ocr_data: Dictionary from pytesseract.image_to_data().

        Returns:
            List of word dictionaries with position and text.
        """
        words = []
        n_boxes = len(ocr_data.get("text", []))

        for i in range(n_boxes):
            text = str(ocr_data["text"][i]).strip()
            
            # Skip empty text
            if not text:
                continue

            # Get confidence, handling -1 (structural elements)
            conf = float(ocr_data["conf"][i])
            if conf < 0:
                continue

            # Filter low confidence
            if conf < OCR_CONFIDENCE_THRESHOLD:
                continue

            words.append({
                "text": text,
                "left": int(ocr_data["left"][i]),
                "top": int(ocr_data["top"][i]),
                "width": int(ocr_data["width"][i]),
                "height": int(ocr_data["height"][i]),
                "conf": conf,
            })

        return words

    def _group_into_lines(
        self,
        words: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group words into lines based on Y-coordinate proximity.

        Words with similar Y coordinates are considered to be
        on the same line.

        Args:
            words: List of word dictionaries.

        Returns:
            List of lines, where each line is a list of words.
        """
        if not words:
            return []

        # Sort by vertical position, then horizontal
        sorted_words = sorted(words, key=lambda w: (w["top"], w["left"]))

        lines: List[List[Dict[str, Any]]] = []
        current_line = [sorted_words[0]]
        current_y = sorted_words[0]["top"]

        for word in sorted_words[1:]:
            # Check if word is on the same line
            y_diff = abs(word["top"] - current_y)
            
            if y_diff < LINE_MERGE_THRESHOLD_PX:
                # Same line
                current_line.append(word)
            else:
                # New line - save current and start new
                current_line.sort(key=lambda w: w["left"])
                lines.append(current_line)
                current_line = [word]
                current_y = word["top"]

        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda w: w["left"])
            lines.append(current_line)

        return lines

    def _group_into_paragraphs(
        self,
        lines: List[List[Dict[str, Any]]]
    ) -> List[TextBlock]:
        """
        Group lines into paragraphs based on vertical spacing.

        Lines with small vertical gaps are grouped together.

        Args:
            lines: List of lines (each line is a list of words).

        Returns:
            List of TextBlock objects representing paragraphs.
        """
        if not lines:
            return []

        paragraphs: List[TextBlock] = []
        current_paragraph_lines = [lines[0]]

        for i in range(1, len(lines)):
            prev_line = lines[i - 1]
            curr_line = lines[i]

            # Calculate average height of previous line
            avg_height = sum(w["height"] for w in prev_line) / len(prev_line)
            threshold = avg_height * PARAGRAPH_GAP_MULTIPLIER

            # Calculate vertical gap
            prev_bottom = max(w["top"] + w["height"] for w in prev_line)
            curr_top = min(w["top"] for w in curr_line)
            gap = curr_top - prev_bottom

            if gap < threshold:
                # Same paragraph
                current_paragraph_lines.append(curr_line)
            else:
                # New paragraph
                paragraphs.append(
                    self._merge_lines_to_block(current_paragraph_lines)
                )
                current_paragraph_lines = [curr_line]

        # Don't forget the last paragraph
        if current_paragraph_lines:
            paragraphs.append(
                self._merge_lines_to_block(current_paragraph_lines)
            )

        return paragraphs

    def _merge_lines_to_block(
        self,
        lines: List[List[Dict[str, Any]]]
    ) -> TextBlock:
        """
        Merge multiple lines into a single TextBlock.

        Combines text with line breaks and calculates
        bounding box for all words.

        Args:
            lines: List of lines to merge.

        Returns:
            TextBlock with combined text and bounding box.
        """
        all_words = [word for line in lines for word in line]

        # Build text with line breaks
        text_lines = []
        for line in lines:
            line_text = " ".join(w["text"] for w in line)
            text_lines.append(line_text)
        text = "\n".join(text_lines)

        # Calculate bounding box
        left = min(w["left"] for w in all_words)
        top = min(w["top"] for w in all_words)
        right = max(w["left"] + w["width"] for w in all_words)
        bottom = max(w["top"] + w["height"] for w in all_words)

        # Calculate average confidence
        avg_conf = sum(w["conf"] for w in all_words) / len(all_words)

        return TextBlock(
            text=text,
            left=left,
            top=top,
            width=right - left,
            height=bottom - top,
            confidence=avg_conf,
        )
