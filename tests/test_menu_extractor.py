"""
Tests para tasks/menu/extractor.py.
"""
import json
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from tasks.menu.extractor import extract_menus, get_today_menu, _parse_menu_json
from lib.exceptions import ClaudeAPIError


# Respuesta JSON simulada de Claude
_VALID_CLAUDE_RESPONSE = json.dumps({
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
                "dessert": "Compote",
            },
        },
    }
})


class TestParseMenuJson:
    def test_parses_clean_json(self):
        result = _parse_menu_json(_VALID_CLAUDE_RESPONSE)
        assert "2026-03-18" in result
        assert result["2026-03-18"]["dejeuner"]["plat"] == "Poulet rôti"

    def test_parses_json_with_surrounding_text(self):
        """Claude a veces añade texto antes/después del JSON."""
        raw = f"Voici les menus extraits:\n{_VALID_CLAUDE_RESPONSE}\nJ'espère que c'est utile."
        result = _parse_menu_json(raw)
        assert "2026-03-18" in result

    def test_parses_json_without_days_wrapper(self):
        """Si Claude devuelve el dict de días directamente (sin wrapper 'days')."""
        raw = json.dumps({
            "2026-03-18": {
                "dejeuner": {"plat": "Poulet", "entree": None, "garniture": None, "dessert": "Fruit"},
            }
        })
        result = _parse_menu_json(raw)
        assert "2026-03-18" in result

    def test_raises_on_unparseable_response(self):
        with pytest.raises(ClaudeAPIError, match="No se pudo parsear JSON"):
            _parse_menu_json("Je suis désolé, je ne peux pas extraire les menus.")


class TestGetTodayMenu:
    def test_returns_menu_for_today(self, sample_menu_data):
        today = date(2026, 3, 18)
        result = get_today_menu(sample_menu_data, today)
        assert result is not None
        assert result["dejeuner"]["plat"] == "Poulet rôti"

    def test_returns_none_for_missing_day(self, sample_menu_data):
        today = date(2026, 3, 20)  # Viernes no en los datos
        result = get_today_menu(sample_menu_data, today)
        assert result is None

    def test_returns_none_for_empty_data(self):
        result = get_today_menu({}, date(2026, 3, 18))
        assert result is None


class TestExtractMenus:
    def test_uploads_and_extracts_when_no_file_id(
        self, mock_claude_client, tmp_path
    ):
        """Debe subir el PDF y extraer los menús si no hay file_id."""
        mock_claude_client.extract_from_file.return_value = _VALID_CLAUDE_RESPONSE

        menu_data = {
            "period": "2026-03",
            "source_url": "https://example.com/menu.pdf",
            "claude_file_id": None,
            "days": {},
        }

        with patch("tasks.menu.extractor.download_pdf") as mock_dl:
            mock_dl.return_value = None
            # Simular que se crea el fichero PDF temporal
            result = extract_menus(
                pdf_url="https://example.com/menu.pdf",
                menu_data=menu_data,
                claude_client=mock_claude_client,
                year=2026,
                month=3,
            )

        mock_claude_client.upload_file.assert_called_once()
        mock_claude_client.extract_from_file.assert_called_once()
        assert result["claude_file_id"] == "file_test123"
        assert "2026-03-18" in result["days"]

    def test_reuses_existing_file_id(self, mock_claude_client):
        """Si ya hay file_id, no debe re-subir el PDF."""
        mock_claude_client.extract_from_file.return_value = _VALID_CLAUDE_RESPONSE

        menu_data = {
            "period": "2026-03",
            "claude_file_id": "file_existing",
            "days": {},
        }

        result = extract_menus(
            pdf_url="https://example.com/menu.pdf",
            menu_data=menu_data,
            claude_client=mock_claude_client,
            year=2026,
            month=3,
        )

        mock_claude_client.upload_file.assert_not_called()
        mock_claude_client.extract_from_file.assert_called_once()
        call_args = mock_claude_client.extract_from_file.call_args
        assert call_args[0][0] == "file_existing"
        assert "2026-03-18" in result["days"]
