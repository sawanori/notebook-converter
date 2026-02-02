"""
Custom logging handler for Flet PubSub integration.

Allows log messages to be displayed in the UI by forwarding
them through a callback function to PubSub topics.
"""
from __future__ import annotations

import logging
from typing import Callable


class PubSubLogHandler(logging.Handler):
    """
    Logging handler that forwards messages to a callback.
    
    Designed to integrate with Flet's PubSub system for
    displaying log messages in the UI.
    """

    def __init__(self, callback: Callable[[str], None]):
        """
        Initialize the handler.

        Args:
            callback: Function to call with formatted log messages.
                     Typically sends messages to page.pubsub.
        """
        super().__init__()
        self.callback = callback
        
        # Set default formatter
        self.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        ))

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record.

        Formats the record and calls the callback function.

        Args:
            record: Log record to emit.
        """
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


def setup_logger(
    name: str,
    callback: Callable[[str], None],
    level: int = logging.INFO
) -> logging.Logger:
    """
    Set up a logger with PubSub integration.

    Creates a logger that forwards messages to the provided
    callback function for UI display.

    Args:
        name: Logger name (typically module name).
        callback: Function to receive log messages.
        level: Logging level (default: INFO).

    Returns:
        Configured logger instance.

    Example:
        ```python
        def on_log(msg):
            page.pubsub.send_all_on_topic("log", msg)
        
        logger = setup_logger("converter", on_log)
        logger.info("Starting conversion...")
        ```
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add PubSub handler
    handler = PubSubLogHandler(callback)
    handler.setLevel(level)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def create_console_handler(level: int = logging.DEBUG) -> logging.Handler:
    """
    Create a console handler for development/debugging.

    Args:
        level: Logging level (default: DEBUG).

    Returns:
        Configured StreamHandler.
    """
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    ))
    return handler
