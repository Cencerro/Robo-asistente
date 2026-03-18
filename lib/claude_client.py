"""
Wrapper para Claude API + Files API.
Gestiona la subida de ficheros y la extracción de contenido estructurado.
"""
import logging
from pathlib import Path

import httpx

from lib.exceptions import ClaudeAPIError

logger = logging.getLogger(__name__)

# Endpoint base de la API de Anthropic
_BASE_URL = "https://api.anthropic.com"
_API_VERSION = "2023-06-01"
_FILES_BETA = "files-2025-04-14"
_MODEL = "claude-sonnet-4-6"


class ClaudeClient:
    """Cliente para Claude API con soporte de Files API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
        }

    def upload_file(self, file_path: Path, mime_type: str = "application/pdf") -> str:
        """
        Sube un fichero a la Files API de Claude.
        Devuelve el file_id para usarlo en posteriores llamadas.
        """
        logger.info("Subiendo fichero a Claude Files API: %s", file_path)

        headers = {
            **self._headers,
            "anthropic-beta": _FILES_BETA,
        }

        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{_BASE_URL}/v1/files",
                    headers=headers,
                    files={"file": (file_path.name, file_content, mime_type)},
                )

            if response.status_code != 200:
                raise ClaudeAPIError(
                    f"Error subiendo fichero: HTTP {response.status_code} — {response.text}"
                )

            data = response.json()
            file_id = data.get("id")
            if not file_id:
                raise ClaudeAPIError(
                    f"Respuesta inesperada de Files API (sin 'id'): {data}"
                )

            logger.info("Fichero subido con éxito. file_id=%s", file_id)
            return file_id

        except httpx.HTTPError as e:
            raise ClaudeAPIError(f"Error HTTP al subir fichero: {e}") from e

    def extract_from_file(self, file_id: str, prompt: str) -> str:
        """
        Envía una petición a Claude usando un file_id previamente subido.
        Devuelve el texto de la respuesta.
        """
        logger.info("Extrayendo contenido de file_id=%s", file_id)

        headers = {
            **self._headers,
            "anthropic-beta": _FILES_BETA,
            "content-type": "application/json",
        }

        payload = {
            "model": _MODEL,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "file",
                                "file_id": file_id,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{_BASE_URL}/v1/messages",
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                raise ClaudeAPIError(
                    f"Error en Messages API: HTTP {response.status_code} — {response.text}"
                )

            data = response.json()
            content = data.get("content", [])
            if not content or content[0].get("type") != "text":
                raise ClaudeAPIError(
                    f"Respuesta inesperada de Messages API: {data}"
                )

            text = content[0]["text"]
            logger.info("Extracción completada (%d caracteres)", len(text))
            return text

        except httpx.HTTPError as e:
            raise ClaudeAPIError(f"Error HTTP en Messages API: {e}") from e
