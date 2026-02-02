"""
PyInstaller compatible resource path resolution utilities
"""
import sys
import os
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """
    Returns correct resource path for both PyInstaller --onefile execution
    and normal script execution

    Args:
        relative_path: Relative path from project root

    Returns:
        Path: Absolute path
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller execution
        base_path = Path(sys._MEIPASS)
    else:
        # Normal script execution
        base_path = Path(__file__).parent.parent

    return base_path / relative_path

def get_app_data_dir() -> Path:
    """
    Get application data directory
    Windows: %APPDATA%/NotebookConverter

    Returns:
        Path: Application data directory
    """
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', ''))
    else:
        base = Path.home() / '.config'

    app_dir = base / 'NotebookConverter'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir
