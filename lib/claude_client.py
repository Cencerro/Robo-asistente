"""
Wrapper para Claude API + Files API.
Gestiona la subida de ficheros y la extracción de contenido estructurado.
"""
import json
import logging
import subprocess
from pathlib import Path

import httpx

from lib.exceptions import ClaudeAPIError

logger = logging.getLogger(__name__)

# Endpoint base de la API de Anthropic
_BASE_URL = "https://api.anthropic.com"
_API_VERSION = "2023-06-01"
_FILES_BETA = "files-api-2025-04-14"
#_MODEL = "claude-sonnet-4-6"
_MODEL = "claude-haiku-4-5"  # Más rápido y barato, pero menos preciso (ideal para pruebas)



class ClaudeClient:
    """Cliente para Claude API con soporte de Files API."""

    def __init__(self, api_key: str, anthropic_beta: str | None = None) -> None:
        self._api_key = api_key
        self._headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
        }
        if anthropic_beta:
            self._headers["anthropic-beta"] = anthropic_beta

    def upload_file(self, file_path: Path, mime_type: str = "application/pdf") -> str:
        """
        Sube un fichero a la Files API de Claude usando curl.
        Devuelve el file_id para usarlo en posteriores llamadas.
        """
        logger.info("Subiendo fichero a Claude Files API: %s", file_path)

        # File upload uses multipart/form-data — curl sets Content-Type with boundary automatically.
        # Do NOT include Content-Type header here; it must not be set to application/json.
        cmd = [
            "curl", "-s", "-X", "POST",
            f"{_BASE_URL}/v1/files",
            "-H", f"x-api-key: {self._api_key}",
            "-H", f"anthropic-version: {_API_VERSION}",
            "-H", f"anthropic-beta: {_FILES_BETA}",
            "-F", f"file=@{file_path};type={mime_type}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired as e:
            raise ClaudeAPIError("Timeout al subir fichero con curl") from e
        except FileNotFoundError as e:
            raise ClaudeAPIError("curl no encontrado en el sistema") from e

        if result.returncode != 0:
            raise ClaudeAPIError(
                f"curl falló (código {result.returncode}): {result.stderr}"
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ClaudeAPIError(
                f"Respuesta no válida de Files API: {result.stdout!r}"
            ) from e

        if "error" in data:
            raise ClaudeAPIError(f"Error de Files API: {data['error']}")

        file_id = data.get("id")
        if not file_id:
            raise ClaudeAPIError(
                f"Respuesta inesperada de Files API (sin 'id'): {data}"
            )

        logger.info("Fichero subido con éxito. file_id=%s", file_id)
        return file_id

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
            "max_tokens": 8192,
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
