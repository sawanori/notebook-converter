"""
Settings management class
- Save/load settings in JSON format
- Auto-detect Tesseract/Poppler paths
"""
from __future__ import annotations
import json
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

try:
    from utils.system import get_app_data_dir
except ImportError:
    from ..utils.system import get_app_data_dir
from .defaults import (
    SETTINGS_FILENAME,
    DEFAULT_TESSERACT_PATHS,
    DEFAULT_POPPLER_PATHS,
    OCR_LANGUAGES,
)

logger = logging.getLogger(__name__)

@dataclass
class Settings:
    """Application settings"""
    tesseract_path: str = ""
    poppler_path: str = ""
    ocr_languages: str = OCR_LANGUAGES
    last_output_dir: str = ""

    def is_valid(self) -> bool:
        """Check if settings are valid"""
        tesseract_ok = self.tesseract_path and Path(self.tesseract_path).exists()
        poppler_ok = self.poppler_path and Path(self.poppler_path).exists()
        return tesseract_ok and poppler_ok


class SettingsManager:
    """Manages settings reading, writing, and auto-detection"""

    def __init__(self):
        self._settings_path = get_app_data_dir() / SETTINGS_FILENAME
        self._settings: Settings = Settings()
        self._load()

        # Auto-detect paths if not set or invalid
        if not self._settings.tesseract_path or not Path(self._settings.tesseract_path).exists():
            detected = self._detect_tesseract()
            if detected:
                self._settings.tesseract_path = str(detected)

        if not self._settings.poppler_path or not Path(self._settings.poppler_path).exists():
            detected = self._detect_poppler()
            if detected:
                self._settings.poppler_path = str(detected)

        self._save()

    @property
    def settings(self) -> Settings:
        return self._settings

    def update(self, **kwargs) -> None:
        """Update settings and save"""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        self._save()

    def _load(self) -> None:
        """Load settings from file"""
        if self._settings_path.exists():
            try:
                with open(self._settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._settings = Settings(**data)
            except (json.JSONDecodeError, TypeError):
                self._settings = Settings()

    def _save(self) -> None:
        """Save settings to file"""
        try:
            with open(self._settings_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._settings), f, indent=2, ensure_ascii=False)
        except (IOError, OSError) as e:
            logger.error(f"Failed to save settings: {e}")

    def _detect_tesseract(self) -> Optional[Path]:
        """Auto-detect Tesseract"""
        # Search from PATH using shutil.which
        which_result = shutil.which("tesseract")
        if which_result:
            return Path(which_result)

        # Check default paths in order
        for path in DEFAULT_TESSERACT_PATHS:
            if path.exists():
                return path

        return None

    def _detect_poppler(self) -> Optional[Path]:
        """Auto-detect Poppler"""
        # Search for pdftoppm using shutil.which
        which_result = shutil.which("pdftoppm")
        if which_result:
            return Path(which_result).parent

        # Check default paths
        for path in DEFAULT_POPPLER_PATHS:
            if path.exists():
                return path

        # Search for different versions using wildcards (Windows)
        # Use Pathlib's glob for cross-platform support
        program_files = Path(r"C:\Program Files")
        if program_files.exists():
            for poppler_dir in program_files.glob("poppler-*"):
                for bin_path in ["Library/bin", "bin"]:
                    candidate = poppler_dir / bin_path
                    if candidate.exists():
                        return candidate

        return None
