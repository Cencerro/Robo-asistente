"""
Entry point del sistema robo-assistente.
Llamado por cron con el nombre de la tarea como argumento:
    python automata.py menu
"""
import sys
import logging

from lib.config import get_settings
from lib.exceptions import RoboAssistenteError, ConfigError
from lib.logger import setup_logging


def main() -> int:
    """Punto de entrada principal. Devuelve el código de salida."""
    if len(sys.argv) < 2:
        # No hay logging configurado aún; stderr directamente
        print(
            "Uso: python automata.py <tarea>\n"
            "Tareas disponibles: menu",
            file=sys.stderr,
        )
        return 1

    task_name = sys.argv[1].strip()

    # Configurar logging (antes de cualquier otra operación)
    try:
        settings = get_settings()
        setup_logging(log_level=settings.log_level)
    except Exception as e:
        # Si la config falla, loguear a stderr sin formato y salir
        print(f"[ERROR] Fallo en configuración: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    logger = logging.getLogger(__name__)
    logger.info("robo-assistente iniciado. Tarea: '%s'", task_name)

    try:
        # Importar aquí para que el logging ya esté configurado
        from tasks import run_task
        run_task(task_name)
        return 0

    except ConfigError as e:
        logger.critical("Error de configuración: %s", e)
        return 1
    except RoboAssistenteError as e:
        logger.error("Error en tarea '%s': %s", task_name, e)
        return 1
    except Exception as e:
        logger.exception("Error inesperado en tarea '%s': %s", task_name, e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
