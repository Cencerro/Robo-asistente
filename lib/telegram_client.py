"""
Wrapper para Telegram Bot API.
Envía mensajes de texto con soporte de Markdown.
"""
import logging

import httpx

from lib.exceptions import TelegramError

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.telegram.org"


class TelegramClient:
    """Cliente para enviar mensajes por Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._base = f"{_BASE_URL}/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> None:
        """
        Envía un mensaje de texto al chat configurado.
        parse_mode: "HTML" o "MarkdownV2" (por defecto HTML, más robusto).
        """
        logger.info(
            "Enviando mensaje Telegram (%d chars) al chat %s",
            len(text),
            self._chat_id,
        )

        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self._base}/sendMessage",
                    json=payload,
                )

            data = response.json()
            if not data.get("ok"):
                raise TelegramError(
                    f"Telegram API devolvió error: {data.get('description', data)}"
                )

            logger.info("Mensaje enviado con éxito por Telegram")

        except httpx.HTTPError as e:
            raise TelegramError(f"Error HTTP con Telegram: {e}") from e
