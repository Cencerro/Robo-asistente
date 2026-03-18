"""
Tests para lib/telegram_client.py.
Los tests unitarios mockean httpx. El test de integración envía un mensaje real.
"""
import pytest
from unittest.mock import MagicMock, patch

import httpx

from lib.telegram_client import TelegramClient
from lib.exceptions import TelegramError


class TestTelegramClient:
    def _client(self):
        return TelegramClient(bot_token="123:FAKE", chat_id="-100000")

    def test_send_message_ok(self):
        client = self._client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}

        with patch("lib.telegram_client.httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response
            client.send_message("Hola")

        mock_httpx.return_value.__enter__.return_value.post.assert_called_once()

    def test_send_message_raises_on_api_error(self):
        client = self._client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "description": "Bad Request"}

        with patch("lib.telegram_client.httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response
            with pytest.raises(TelegramError, match="Bad Request"):
                client.send_message("Hola")

    def test_send_message_raises_on_http_error(self):
        client = self._client()

        with patch("lib.telegram_client.httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.side_effect = (
                httpx.ConnectError("timeout")
            )
            with pytest.raises(TelegramError, match="Error HTTP"):
                client.send_message("Hola")

    def test_payload_contiene_chat_id_y_texto(self):
        client = TelegramClient(bot_token="123:FAKE", chat_id="-999")
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}

        with patch("lib.telegram_client.httpx.Client") as mock_httpx:
            mock_post = mock_httpx.return_value.__enter__.return_value.post
            mock_post.return_value = mock_response
            client.send_message("Mensaje de prueba")

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["chat_id"] == "-999"
        assert kwargs["json"]["text"] == "Mensaje de prueba"
        assert kwargs["json"]["parse_mode"] == "HTML"


@pytest.mark.integration
def test_envia_mensaje_real():
    """Envía un mensaje real por Telegram. Requiere .env con credenciales válidas."""
    from lib.config import get_settings
    settings = get_settings()

    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    # Si no hay credenciales reales, no tiene sentido ejecutar este test.
    if "..." in token or token.startswith("123") or chat_id in {"-100000", "-1000000000", "123"}:
        pytest.skip("Credenciales de Telegram no configuradas o son placeholders")

    client = TelegramClient(
        bot_token=token,
        chat_id=chat_id,
    )
    client.send_message("Test de Robo Asistente")
