"""
Wrapper para Mistral API.
Reservado para tareas simples (clasificación, resúmenes breves).
"""
import logging

import httpx

from lib.exceptions import MistralAPIError

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.mistral.ai"
_MODEL = "mistral-small-latest"


class MistralClient:
    """Cliente básico para Mistral API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, prompt: str, system: str | None = None) -> str:
        """
        Envía un mensaje a Mistral y devuelve la respuesta en texto.
        """
        logger.info("Enviando petición a Mistral (%d chars)", len(prompt))

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": _MODEL,
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{_BASE_URL}/v1/chat/completions",
                    headers=self._headers,
                    json=payload,
                )

            if response.status_code != 200:
                raise MistralAPIError(
                    f"Error Mistral API: HTTP {response.status_code} — {response.text}"
                )

            data = response.json()
            text = data["choices"][0]["message"]["content"]
            logger.info("Respuesta Mistral recibida (%d chars)", len(text))
            return text

        except httpx.HTTPError as e:
            raise MistralAPIError(f"Error HTTP con Mistral: {e}") from e
        except (KeyError, IndexError) as e:
            raise MistralAPIError(f"Respuesta inesperada de Mistral: {e}") from e
