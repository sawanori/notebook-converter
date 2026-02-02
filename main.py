"""
NotebookLM Slide Converter

Application entry point.
Converts PDF slides to editable PowerPoint presentations.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import flet as ft

from config.defaults import (
    APP_NAME,
    APP_VERSION,
    THEME_BACKGROUND,
    THEME_PRIMARY,
)
from config.settings_manager import SettingsManager
from ui.app_layout import create_app_layout
from utils.system import resource_path

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def main(page: ft.Page) -> None:
    """
    Flet application main function.

    Args:
        page: Flet page instance.
    """
    # Page configuration
    page.title = f"{APP_NAME} v{APP_VERSION}"
    page.window.width = 1000
    page.window.height = 700
    page.window.min_width = 800
    page.window.min_height = 600
    page.bgcolor = THEME_BACKGROUND

    # Theme configuration
    page.theme = ft.Theme(
        color_scheme_seed=THEME_PRIMARY,
    )
    page.theme_mode = ft.ThemeMode.LIGHT

    # Set window icon if available
    icon_path = resource_path("assets/icon.png")
    if icon_path.exists():
        page.window.icon = str(icon_path)

    # Initialize settings manager
    logger.info("Initializing settings...")
    settings_manager = SettingsManager()

    if settings_manager.settings.is_valid():
        logger.info("Settings loaded successfully")
    else:
        logger.warning("Settings incomplete - please configure in Settings page")

    # Build main layout
    logger.info("Building UI...")
    layout = create_app_layout(page, settings_manager)

    # Add layout to page
    page.add(layout)

    logger.info(f"{APP_NAME} started")


if __name__ == "__main__":
    # ft.app() is deprecated in 0.80+, use ft.run() instead
    # For web mode: ft.run(main, view=ft.AppView.WEB_BROWSER, port=8550)
    ft.run(main)
