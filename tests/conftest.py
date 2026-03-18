"""
Fixtures compartidas para los tests del sistema.
"""
import json
import pytest
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock


@pytest.fixture
def sample_menu_data():
    """Datos de menú de ejemplo para tests."""
    return {
        "period": "2026-03",
        "source_url": "https://www.maisonslaffitte.fr/restauration-scolaire/10166/",
        "claude_file_id": "file_test123",
        "fetched_at": "2026-03-18T08:00:00Z",
        "days": {
            "2026-03-18": {
                "dejeuner": {
                    "entree": "Salade de carottes",
                    "plat": "Poulet rôti",
                    "garniture": "Purée de pommes de terre",
                    "dessert": "Yaourt",
                },
                "gouter": {
                    "composantes": ["Pain", "Beurre", "Pomme"],
                },
            },
            "2026-03-19": {
                "dejeuner": {
                    "entree": None,
                    "plat": "Poisson pané",
                    "garniture": "Riz",
                    "dessert": "Fruit de saison",
                },
                "gouter": {
                    "composantes": ["Pain", "Chocolat"],
                },
            },
        },
    }


@pytest.fixture
def today():
    """Fecha fija para tests: 2026-03-18."""
    return date(2026, 3, 18)


@pytest.fixture
def mock_claude_client():
    """Mock del cliente Claude."""
    client = MagicMock()
    client.upload_file.return_value = "file_test123"
    return client


@pytest.fixture
def mock_telegram_client():
    """Mock del cliente Telegram."""
    return MagicMock()


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Directorio temporal de datos para tests."""
    (tmp_path / "menus").mkdir(parents=True)
    return tmp_path
