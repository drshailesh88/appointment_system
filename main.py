#!/usr/bin/env python3
"""
DocAssist Practice Manager - Main Entry Point

Premium appointment scheduling and practice management for Indian doctors.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import get_settings


def setup_logging() -> None:
    """Configure application logging."""
    settings = get_settings()

    log_level = logging.DEBUG if settings.debug else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))

    # File handler
    log_file = settings.log_path / "practice_manager.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def init_database() -> None:
    """Initialize database and create tables."""
    from src.models.base import init_db

    logging.info("Initializing database...")
    init_db()
    logging.info("Database initialized successfully")


def check_ollama() -> bool:
    """Check if Ollama is available."""
    settings = get_settings()

    try:
        import httpx

        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            logging.info("Ollama is available")
            return True
    except Exception as e:
        logging.warning(f"Ollama not available: {e}")

    return False


def main() -> None:
    """Main entry point for DocAssist Practice Manager."""
    print(
        """
    ╔═══════════════════════════════════════════════════════════╗
    ║           DocAssist Practice Manager v0.1.0               ║
    ║   Premium Appointment & Practice Management for Doctors   ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    )

    # Setup
    setup_logging()
    settings = get_settings()

    logging.info(f"Starting {settings.app_name} v{settings.app_version}")
    logging.info(f"Data directory: {settings.data_dir.absolute()}")

    # Initialize database
    init_database()

    # Check LLM availability
    ollama_available = check_ollama()
    if not ollama_available:
        logging.warning("Continuing without LLM features. Install Ollama for AI capabilities.")

    # Start UI application
    try:
        import flet as ft

        def app(page: ft.Page) -> None:
            """Flet application entry point."""
            page.title = settings.app_name
            page.window.width = settings.window_width
            page.window.height = settings.window_height
            page.theme_mode = ft.ThemeMode.SYSTEM

            # Placeholder UI until full implementation
            page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "DocAssist Practice Manager",
                                size=32,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Premium Appointment & Practice Management",
                                size=16,
                                color=ft.Colors.GREY_500,
                            ),
                            ft.Divider(height=40),
                            ft.Text(
                                "Project initialized successfully!",
                                size=18,
                            ),
                            ft.Text(
                                "Development in progress...",
                                size=14,
                                color=ft.Colors.GREY_400,
                            ),
                            ft.Container(height=20),
                            ft.Row(
                                [
                                    ft.Chip(
                                        label=ft.Text("Flet UI"),
                                        bgcolor=ft.Colors.BLUE_100,
                                    ),
                                    ft.Chip(
                                        label=ft.Text("SQLite"),
                                        bgcolor=ft.Colors.GREEN_100,
                                    ),
                                    ft.Chip(
                                        label=ft.Text(
                                            "Ollama" if ollama_available else "Ollama (offline)"
                                        ),
                                        bgcolor=(
                                            ft.Colors.GREEN_100
                                            if ollama_available
                                            else ft.Colors.ORANGE_100
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=50,
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )

        ft.app(target=app)

    except ImportError:
        logging.error("Flet not installed. Run: pip install flet")
        print("\nTo run the UI, install dependencies:")
        print("  pip install -r requirements.txt")
        print("\nOr run in development mode:")
        print("  pip install -e .[dev]")


if __name__ == "__main__":
    main()
