"""
Jerarquía de excepciones del sistema.
Todas heredan de RoboAssistenteError para facilitar el manejo en automata.py.
"""


class RoboAssistenteError(Exception):
    """Excepción base del sistema."""


class ConfigError(RoboAssistenteError):
    """Error en la configuración o variables de entorno."""


class ScrapingError(RoboAssistenteError):
    """Error al obtener o parsear contenido web."""


class ClaudeAPIError(RoboAssistenteError):
    """Error en la comunicación con la API de Claude."""


class MistralAPIError(RoboAssistenteError):
    """Error en la comunicación con la API de Mistral."""


class TelegramError(RoboAssistenteError):
    """Error al enviar mensajes por Telegram."""


class StorageError(RoboAssistenteError):
    """Error al leer o escribir datos en disco."""
