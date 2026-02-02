"""
Main application layout with sidebar navigation.

Provides the overall structure of the application including
navigation rail and view switching.
"""
from __future__ import annotations

import flet as ft

try:
    from config.defaults import APP_NAME, THEME_PRIMARY
    from config.settings_manager import SettingsManager
    from ui.views.home_view import create_home_view
    from ui.views.settings_view import create_settings_view
except ImportError:
    from ..config.defaults import APP_NAME, THEME_PRIMARY
    from ..config.settings_manager import SettingsManager
    from .views.home_view import create_home_view
    from .views.settings_view import create_settings_view


def create_app_layout(
    page: ft.Page,
    settings_manager: SettingsManager,
) -> ft.Row:
    """
    Create the main application layout.

    Args:
        page: Flet page instance.
        settings_manager: Settings manager instance.

    Returns:
        Row containing sidebar and content area.
    """
    # Content container for views
    content_area = ft.Container(expand=True)

    # Create views
    home_view = create_home_view(page, settings_manager)

    def on_settings_changed() -> None:
        """Callback when settings are updated."""
        # Refresh UI elements that depend on settings
        page.update()

    settings_view = create_settings_view(
        page,
        settings_manager,
        on_settings_changed
    )

    # Initial view
    content_area.content = home_view
    current_index = 0

    def on_nav_change(e: ft.ControlEvent) -> None:
        """Handle navigation selection change."""
        nonlocal current_index
        index = e.control.selected_index
        current_index = index

        if index == 0:
            content_area.content = home_view
        elif index == 1:
            content_area.content = settings_view

        page.update()

    # Navigation rail (sidebar)
    sidebar = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        bgcolor=ft.Colors.SURFACE,
        leading=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.SLIDESHOW,
                        size=32,
                        color=THEME_PRIMARY,
                    ),
                    ft.Text(
                        "Slide\nConverter",
                        size=12,
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            padding=ft.Padding(top=20, bottom=20, left=0, right=0),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label="Home",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
        ],
        on_change=on_nav_change,
    )

    # Main layout: sidebar + divider + content
    return ft.Row(
        controls=[
            sidebar,
            ft.VerticalDivider(width=1),
            content_area,
        ],
        expand=True,
    )
