"""
Application default settings and constants
"""
from pathlib import Path
import sys

# =============================================================================
# Application Information
# =============================================================================
APP_NAME = "NotebookLM Slide Converter"
APP_VERSION = "1.0.0"

# =============================================================================
# OCR Settings
# =============================================================================
OCR_LANGUAGES = "jpn+eng"  # Japanese + English
OCR_DPI = 300              # DPI for PDF to image conversion
OCR_CONFIDENCE_THRESHOLD = 40  # OCR confidence threshold (0-100)

# =============================================================================
# Text Grouping Settings
# =============================================================================
LINE_MERGE_THRESHOLD_PX = 10      # Y-coordinate difference to consider as same line (px)
PARAGRAPH_GAP_MULTIPLIER = 1.5    # Paragraph gap = font height × this value

# =============================================================================
# Memory Monitoring Settings
# =============================================================================
MEMORY_WARNING_THRESHOLD = 80.0   # Memory usage warning threshold (%)

# =============================================================================
# Windows Default Paths
# =============================================================================
if sys.platform == 'win32':
    DEFAULT_TESSERACT_PATHS = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    # Note: Poppler for Windows may have bin or Library\bin depending on distribution
    DEFAULT_POPPLER_PATHS = [
        Path(r"C:\Program Files\poppler-24.02.0\Library\bin"),
        Path(r"C:\Program Files\poppler-24.02.0\bin"),
        Path(r"C:\Program Files\poppler\Library\bin"),
        Path(r"C:\Program Files\poppler\bin"),
        Path(r"C:\poppler\Library\bin"),
        Path(r"C:\poppler\bin"),
    ]
else:
    # macOS/Linux: assume they exist in system paths
    DEFAULT_TESSERACT_PATHS = []
    DEFAULT_POPPLER_PATHS = []

# =============================================================================
# UI Theme Colors
# =============================================================================
THEME_PRIMARY = "#1976D2"      # Deep Blue
THEME_SECONDARY = "#00897B"    # Teal
THEME_BACKGROUND = "#FAFAFA"   # Light Grey
THEME_SURFACE = "#FFFFFF"      # White
THEME_ERROR = "#D32F2F"        # Red
THEME_TEXT_PRIMARY = "#212121"
THEME_TEXT_SECONDARY = "#757575"

# =============================================================================
# Settings File
# =============================================================================
SETTINGS_FILENAME = "settings.json"
