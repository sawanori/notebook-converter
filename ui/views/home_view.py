"""
Home view for PDF to PPTX conversion.

Provides the main conversion interface including:
- File selection
- Progress display
- Log viewer
- Conversion controls
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import flet as ft
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError

try:
    from config.defaults import OCR_DPI
    from config.settings_manager import SettingsManager
    from core.ocr_processor import OCRProcessor
    from core.slide_builder import SlideBuilder
    from ui.log_handler import setup_logger
except ImportError:
    from ...config.defaults import OCR_DPI
    from ...config.settings_manager import SettingsManager
    from ...core.ocr_processor import OCRProcessor
    from ...core.slide_builder import SlideBuilder
    from ..log_handler import setup_logger


@dataclass
class HomeViewState:
    """Mutable state for the home view."""
    selected_file: Optional[Path] = None
    is_converting: bool = False
    worker: Optional["ConversionWorker"] = None


class ConversionWorker:
    """
    Handles PDF to PPTX conversion in a background thread.
    
    Communicates progress and status through Flet's PubSub system.
    """

    def __init__(
        self,
        page: ft.Page,
        settings_manager: SettingsManager,
    ):
        """
        Initialize the conversion worker.

        Args:
            page: Flet page for PubSub communication.
            settings_manager: Settings manager instance.
        """
        self.page = page
        self.settings_manager = settings_manager
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        
        # Set up logger with PubSub callback
        self.logger = setup_logger(
            "converter",
            lambda msg: self.page.pubsub.send_all_on_topic("log", msg)
        )

    def start(self, input_path: Path, output_path: Path) -> None:
        """
        Start the conversion process.

        Args:
            input_path: Path to input PDF file.
            output_path: Path to output PPTX file.
        """
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._process,
            args=(input_path, output_path),
            daemon=True
        )
        self.thread.start()

    def stop(self) -> None:
        """Request cancellation of the conversion."""
        self.stop_event.set()
        self.logger.info("Cancellation requested...")
        self.page.pubsub.send_all_on_topic("status", "cancelled")

    def _process(self, input_path: Path, output_path: Path) -> None:
        """
        Main conversion process (runs in background thread).

        Args:
            input_path: Path to input PDF.
            output_path: Path to output PPTX.
        """
        try:
            self.page.pubsub.send_all_on_topic("status", "busy")
            self.logger.info(f"Starting conversion: {input_path.name}")

            settings = self.settings_manager.settings

            # Validate settings
            if not settings.is_valid():
                self.logger.error("Invalid settings - check Tesseract/Poppler paths")
                self.page.pubsub.send_all_on_topic("status", "error")
                self.page.pubsub.send_all_on_topic(
                    "error_message",
                    "Configuration error: Check Settings page"
                )
                return

            # Convert PDF to images
            self.logger.info("Converting PDF to images...")
            try:
                images = convert_from_path(
                    str(input_path),
                    dpi=OCR_DPI,
                    poppler_path=settings.poppler_path,
                )
            except PDFPageCountError:
                self.logger.error("Invalid PDF: Could not determine page count")
                self.page.pubsub.send_all_on_topic("status", "error")
                self.page.pubsub.send_all_on_topic(
                    "error_message",
                    "Invalid PDF file"
                )
                return
            except PDFSyntaxError:
                self.logger.error("Invalid PDF: Syntax error in PDF file")
                self.page.pubsub.send_all_on_topic("status", "error")
                self.page.pubsub.send_all_on_topic(
                    "error_message",
                    "PDF syntax error"
                )
                return

            total_pages = len(images)
            self.logger.info(f"Found {total_pages} pages")

            if total_pages == 0:
                self.logger.error("PDF has no pages")
                self.page.pubsub.send_all_on_topic("status", "error")
                return

            if self.stop_event.is_set():
                return

            # Initialize OCR processor
            try:
                ocr = OCRProcessor(
                    tesseract_path=settings.tesseract_path,
                    languages=settings.ocr_languages,
                )
            except FileNotFoundError as e:
                self.logger.error(str(e))
                self.page.pubsub.send_all_on_topic("status", "error")
                self.page.pubsub.send_all_on_topic("error_message", str(e))
                return

            # Initialize slide builder
            builder = SlideBuilder(dpi=OCR_DPI)
            builder.create_presentation(images[0])

            # Process each page
            for i, image in enumerate(images):
                if self.stop_event.is_set():
                    self.logger.info("Conversion cancelled by user")
                    return

                page_num = i + 1
                self.logger.info(f"Processing page {page_num}/{total_pages}")

                # Run OCR
                text_blocks = ocr.extract_text_blocks(image, self.stop_event)
                
                if self.stop_event.is_set():
                    return
                    
                self.logger.info(f"  Found {len(text_blocks)} text blocks")

                # Add slide
                builder.add_slide(image, text_blocks, self.stop_event)

                # Update progress
                progress = (i + 1) / total_pages
                self.page.pubsub.send_all_on_topic("progress", progress)

            if self.stop_event.is_set():
                return

            # Save presentation
            self.logger.info(f"Saving to: {output_path}")
            builder.save(output_path)

            # Update last output directory
            self.settings_manager.update(last_output_dir=str(output_path.parent))

            self.logger.info("Conversion completed successfully!")
            self.page.pubsub.send_all_on_topic("status", "done")

        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            self.page.pubsub.send_all_on_topic("status", "error")
            self.page.pubsub.send_all_on_topic("error_message", str(e))


def create_home_view(
    page: ft.Page,
    settings_manager: SettingsManager,
) -> ft.Container:
    """
    Create the home view container.

    Args:
        page: Flet page instance.
        settings_manager: Settings manager instance.

    Returns:
        Container with home view UI.
    """
    # View state
    state = HomeViewState()
    state.worker = ConversionWorker(page, settings_manager)

    # UI elements
    file_label = ft.Text(
        "Click to select PDF file",
        size=16,
        text_align=ft.TextAlign.CENTER,
    )

    drop_icon = ft.Icon(
        ft.Icons.UPLOAD_FILE,
        size=64,
        color=ft.Colors.BLUE_400,
    )

    progress_bar = ft.ProgressBar(
        value=0,
        visible=False,
        width=400,
    )

    progress_text = ft.Text(
        "",
        visible=False,
    )

    log_view = ft.ListView(
        expand=True,
        spacing=2,
        auto_scroll=True,
    )

    convert_button = ft.ElevatedButton(
        "Convert to PPTX",
        icon=ft.Icons.PLAY_ARROW,
        disabled=True,
        width=200,
    )

    cancel_button = ft.ElevatedButton(
        "Cancel",
        icon=ft.Icons.STOP,
        visible=False,
        width=200,
        bgcolor=ft.Colors.RED_400,
        color=ft.Colors.WHITE,
    )

    # Drop container
    drop_container = ft.Container(
        content=ft.Column(
            controls=[drop_icon, file_label],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        width=500,
        height=200,
        border=ft.Border.all(2, ft.Colors.BLUE_200),
        border_radius=10,
        bgcolor=ft.Colors.BLUE_50,
        alignment=ft.Alignment(0, 0),
        ink=True,
    )

    def update_drop_container_hover(is_hover: bool) -> None:
        """Update drop container appearance on hover."""
        if is_hover:
            drop_container.border = ft.Border.all(3, ft.Colors.BLUE_400)
            drop_container.bgcolor = ft.Colors.BLUE_100
        else:
            drop_container.border = ft.Border.all(2, ft.Colors.BLUE_200)
            drop_container.bgcolor = ft.Colors.BLUE_50
        page.update()

    def on_drop_hover(e: ft.ControlEvent) -> None:
        """Handle hover events on drop container."""
        update_drop_container_hover(True)

    def on_drop_leave(e: ft.ControlEvent) -> None:
        """Handle leave events on drop container."""
        update_drop_container_hover(False)

    # Async event handlers for file picking (Flet 0.80+ uses async FilePicker API)
    async def on_drop_click(e: ft.ControlEvent) -> None:
        """Handle click on drop container - opens file picker dialog."""
        files = await ft.FilePicker().pick_files(
            dialog_title="Select PDF file",
            allowed_extensions=["pdf"],
            allow_multiple=False,
        )
        if files and len(files) > 0:
            state.selected_file = Path(files[0].path)
            file_label.value = f"Selected: {state.selected_file.name}"
            convert_button.disabled = not settings_manager.settings.is_valid()
            page.update()

    drop_container.on_click = on_drop_click
    drop_container.on_hover = on_drop_hover

    async def on_convert_click(e: ft.ControlEvent) -> None:
        """Handle convert button click - opens save dialog."""
        if state.selected_file is None:
            return

        # Get last output directory
        last_dir = settings_manager.settings.last_output_dir
        initial_dir = last_dir if last_dir and Path(last_dir).exists() else None

        # Open save dialog
        default_name = state.selected_file.stem + ".pptx"
        result = await ft.FilePicker().save_file(
            dialog_title="Save PPTX file",
            file_name=default_name,
            allowed_extensions=["pptx"],
            initial_directory=initial_dir,
        )

        if result and state.selected_file:
            output_path = Path(result)
            if not output_path.suffix:
                output_path = output_path.with_suffix(".pptx")
            # Start conversion
            state.worker.start(state.selected_file, output_path)

    convert_button.on_click = on_convert_click

    def on_cancel_click(e: ft.ControlEvent) -> None:
        """Handle cancel button click."""
        if state.worker:
            state.worker.stop()

    cancel_button.on_click = on_cancel_click

    # PubSub subscriptions
    def on_progress(topic: str, value: float) -> None:
        """Handle progress updates."""
        progress_bar.value = value
        progress_text.value = f"{int(value * 100)}%"
        page.update()

    def on_log(topic: str, message: str) -> None:
        """Handle log messages."""
        log_view.controls.append(
            ft.Text(
                message,
                size=12,
                font_family="monospace",
                selectable=True,
            )
        )
        # Limit log entries
        if len(log_view.controls) > 100:
            log_view.controls.pop(0)
        page.update()

    def on_status(topic: str, status: str) -> None:
        """Handle status changes."""
        state.is_converting = status == "busy"

        if status == "busy":
            convert_button.visible = False
            cancel_button.visible = True
            progress_bar.visible = True
            progress_text.visible = True
            progress_bar.value = 0
            progress_text.value = "0%"
        elif status in ("done", "error", "cancelled"):
            convert_button.visible = True
            cancel_button.visible = False
            progress_bar.visible = False
            progress_text.visible = False

            if status == "done":
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Conversion completed successfully!"),
                    bgcolor=ft.Colors.GREEN,
                )
                page.snack_bar.open = True
            elif status == "cancelled":
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Conversion cancelled"),
                    bgcolor=ft.Colors.ORANGE,
                )
                page.snack_bar.open = True

        page.update()

    def on_error_message(topic: str, message: str) -> None:
        """Handle error messages."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Error: {message}"),
            bgcolor=ft.Colors.RED,
            duration=5000,
        )
        page.snack_bar.open = True
        page.update()

    # Subscribe to PubSub topics
    page.pubsub.subscribe_topic("progress", on_progress)
    page.pubsub.subscribe_topic("log", on_log)
    page.pubsub.subscribe_topic("status", on_status)
    page.pubsub.subscribe_topic("error_message", on_error_message)

    # Build layout
    return ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Text(
                    "PDF to PPTX Converter",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),

                ft.Container(height=20),

                # Drop area
                ft.Row(
                    controls=[drop_container],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),

                ft.Container(height=20),

                # Progress section
                ft.Row(
                    controls=[progress_bar, progress_text],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),

                # Buttons
                ft.Row(
                    controls=[convert_button, cancel_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),

                ft.Container(height=20),

                # Log section
                ft.Text(
                    "Log",
                    size=14,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(
                    content=log_view,
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                    border_radius=5,
                    padding=10,
                    height=200,
                    expand=True,
                ),
            ],
            spacing=10,
            expand=True,
        ),
        padding=30,
        expand=True,
    )
