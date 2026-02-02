"""
Settings view for configuring external dependencies.

Provides UI for setting Tesseract and Poppler paths,
with browse buttons and validation status.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import flet as ft

try:
    from config.settings_manager import SettingsManager
except ImportError:
    from ...config.settings_manager import SettingsManager


def create_settings_view(
    page: ft.Page,
    settings_manager: SettingsManager,
    on_settings_changed: Optional[Callable[[], None]] = None
) -> ft.Container:
    """
    Create the settings view container.

    Args:
        page: Flet page instance.
        settings_manager: Settings manager for reading/writing settings.
        on_settings_changed: Optional callback when settings change.

    Returns:
        Container with settings UI.
    """
    settings = settings_manager.settings

    # Text fields for paths
    tesseract_field = ft.TextField(
        label="Tesseract Path",
        value=settings.tesseract_path,
        hint_text=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        expand=True,
        read_only=True,
        border_color=ft.Colors.BLUE_200,
    )

    poppler_field = ft.TextField(
        label="Poppler bin Path",
        value=settings.poppler_path,
        hint_text=r"C:\Program Files\poppler-xx.xx.x\Library\bin",
        expand=True,
        read_only=True,
        border_color=ft.Colors.BLUE_200,
    )

    # Status indicator
    status_icon = ft.Icon(
        ft.Icons.CHECK_CIRCLE if settings.is_valid() else ft.Icons.ERROR,
        color=ft.Colors.GREEN if settings.is_valid() else ft.Colors.RED,
    )

    status_text = ft.Text(
        value="Settings are valid" if settings.is_valid() else "Configuration incomplete",
        color=ft.Colors.GREEN if settings.is_valid() else ft.Colors.RED,
    )

    def update_status() -> None:
        """Update status display based on current settings."""
        is_valid = settings_manager.settings.is_valid()
        
        if is_valid:
            status_icon.icon = ft.Icons.CHECK_CIRCLE
            status_icon.color = ft.Colors.GREEN
            status_text.value = "Settings are valid"
            status_text.color = ft.Colors.GREEN
        else:
            status_icon.icon = ft.Icons.ERROR
            status_icon.color = ft.Colors.RED
            
            # Build detailed error message
            missing = []
            s = settings_manager.settings
            
            if not s.tesseract_path:
                missing.append("Tesseract path not set")
            elif not Path(s.tesseract_path).exists():
                missing.append("Tesseract file not found")
                
            if not s.poppler_path:
                missing.append("Poppler path not set")
            elif not Path(s.poppler_path).exists():
                missing.append("Poppler directory not found")
            
            status_text.value = "; ".join(missing) if missing else "Configuration incomplete"
            status_text.color = ft.Colors.RED
        
        page.update()

    # File pickers (Flet 0.80+ async API)
    tesseract_picker = ft.FilePicker()
    tesseract_picker.data = "tesseract_picker"

    poppler_picker = ft.FilePicker()
    poppler_picker.data = "poppler_picker"

    # Register pickers (avoid duplicates)
    existing_pickers = {p.data for p in page.overlay if hasattr(p, 'data')}
    if "tesseract_picker" not in existing_pickers:
        page.overlay.append(tesseract_picker)
    if "poppler_picker" not in existing_pickers:
        page.overlay.append(poppler_picker)

    async def browse_tesseract(e: ft.ControlEvent) -> None:
        """Open file picker for Tesseract."""
        files = await tesseract_picker.pick_files_async(
            dialog_title="Select tesseract.exe",
            allowed_extensions=["exe"],
            allow_multiple=False,
        )
        if files and len(files) > 0:
            path = files[0].path
            tesseract_field.value = path
            settings_manager.update(tesseract_path=path)
            update_status()
            if on_settings_changed:
                on_settings_changed()

    async def browse_poppler(e: ft.ControlEvent) -> None:
        """Open directory picker for Poppler."""
        dir_path = await poppler_picker.get_directory_path_async(
            dialog_title="Select Poppler bin directory"
        )
        if dir_path:
            poppler_field.value = dir_path
            settings_manager.update(poppler_path=dir_path)
            update_status()
            if on_settings_changed:
                on_settings_changed()

    # Initialize status
    update_status()

    # Build UI layout
    return ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Text(
                    "Settings",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),

                # Description
                ft.Text(
                    "External Dependencies",
                    size=16,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    "Configure paths to Tesseract-OCR and Poppler utilities. "
                    "These are required for PDF processing and text recognition.",
                    color=ft.Colors.GREY_600,
                ),

                ft.Container(height=20),

                # Tesseract path
                ft.Row(
                    controls=[
                        tesseract_field,
                        ft.ElevatedButton(
                            "Browse",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=browse_tesseract,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),

                ft.Container(height=10),

                # Poppler path
                ft.Row(
                    controls=[
                        poppler_field,
                        ft.ElevatedButton(
                            "Browse",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=browse_poppler,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),

                ft.Container(height=20),

                # Status display
                ft.Row(
                    controls=[status_icon, status_text],
                    spacing=10,
                ),

                ft.Container(height=30),

                # Help section
                ft.Text(
                    "Installation Help",
                    size=16,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=10),
                
                ft.Row(
                    controls=[
                        ft.TextButton(
                            "Download Tesseract",
                            icon=ft.Icons.DOWNLOAD,
                            url="https://github.com/UB-Mannheim/tesseract/wiki",
                        ),
                        ft.TextButton(
                            "Download Poppler",
                            icon=ft.Icons.DOWNLOAD,
                            url="https://github.com/oschwartz10612/poppler-windows/releases",
                        ),
                    ],
                    spacing=20,
                ),

                ft.Container(height=10),
                
                ft.Text(
                    "Note: During Tesseract installation, make sure to select "
                    "Japanese language pack (jpn) for proper OCR support.",
                    color=ft.Colors.GREY_600,
                    size=12,
                ),
            ],
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=30,
        expand=True,
    )
