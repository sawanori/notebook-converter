"""
UI package for Flet-based user interface.

Contains the main layout, views, and logging utilities.
"""
from .log_handler import PubSubLogHandler, create_console_handler, setup_logger

__all__ = [
    "PubSubLogHandler",
    "setup_logger",
    "create_console_handler",
]
