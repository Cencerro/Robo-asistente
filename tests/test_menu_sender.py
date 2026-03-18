"""
Tests para tasks/menu/sender.py.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock

from tasks.menu.sender import format_menu, send_menu, send_no_menu


_MENU_COMPLETO = {
    "dejeuner": {
        "entree": "Salade de carottes",
        "plat": "Poulet rôti",
        "garniture": "Purée de pommes de terre",
        "dessert": "Yaourt",
    },
    "gouter": {
        "composantes": ["Pain", "Beurre", "Pomme"],
    },
}

_MENU_SIN_ENTREE = {
    "dejeuner": {
        "entree": None,
        "plat": "Poisson pané",
        "garniture": "Riz",
        "dessert": "Compote",
    },
}

_MENU_SIN_GARNITURE = {
    "dejeuner": {
        "entree": "Soupe",
        "plat": "Bœuf bourguignon",
        "garniture": None,
        "dessert": "Fruit",
    },
}


_MENU_SIN_GOUTER = {
    "dejeuner": {
        "entree": "Soupe",
        "plat": "Bœuf bourguignon",
        "garniture": "Purée",
        "dessert": "Fruit",
    },
}


class TestFormatMenu:
    def test_incluye_fecha_en_frances(self):
        today = date(2026, 3, 18)  # Miércoles
        text = format_menu(_MENU_COMPLETO, today)
        assert "Mercredi" in text
        assert "18" in text
        assert "mars" in text
        assert "2026" in text

    def test_incluye_todos_los_campos_dejeuner(self):
        text = format_menu(_MENU_COMPLETO, date(2026, 3, 18))
        assert "Salade de carottes" in text
        assert "Poulet rôti" in text
        assert "Purée de pommes de terre" in text
        assert "Yaourt" in text

    def test_omite_entree_si_es_none(self):
        text = format_menu(_MENU_SIN_ENTREE, date(2026, 3, 18))
        assert "Entrée" not in text
        assert "Poisson pané" in text

    def test_incluye_gouter(self):
        text = format_menu(_MENU_COMPLETO, date(2026, 3, 18))
        assert "Goûter" in text
        assert "Pain" in text
        assert "Pomme" in text

    def test_omite_gouter_si_ausente(self):
        text = format_menu(_MENU_SIN_GOUTER, date(2026, 3, 18))
        assert "Goûter" not in text

    def test_omite_garniture_si_es_none(self):
        text = format_menu(_MENU_SIN_GARNITURE, date(2026, 3, 18))
        assert "Garniture" not in text

    def test_formato_html_telegram(self):
        text = format_menu(_MENU_COMPLETO, date(2026, 3, 18))
        assert "<b>" in text


class TestSendMenu:
    def test_llama_send_message(self):
        client = MagicMock()
        send_menu(_MENU_COMPLETO, client, date(2026, 3, 18))
        client.send_message.assert_called_once()

    def test_mensaje_contiene_plat(self):
        client = MagicMock()
        send_menu(_MENU_COMPLETO, client, date(2026, 3, 18))
        texto = client.send_message.call_args[0][0]
        assert "Poulet rôti" in texto


class TestSendNoMenu:
    def test_llama_send_message(self):
        client = MagicMock()
        send_no_menu(client, date(2026, 3, 18))
        client.send_message.assert_called_once()

    def test_mensaje_indica_sin_menu(self):
        client = MagicMock()
        send_no_menu(client, date(2026, 3, 18))
        texto = client.send_message.call_args[0][0]
        assert "Pas de menu" in texto
        assert "18" in texto
