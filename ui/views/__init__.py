"""
View package containing UI screens.
"""
from .home_view import create_home_view
from .settings_view import create_settings_view

__all__ = [
    "create_home_view",
    "create_settings_view",
]
