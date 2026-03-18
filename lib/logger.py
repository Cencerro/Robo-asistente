"""
Logger centralizado del sistema.
RotatingFileHandler para logs/automata.log + StreamHandler a stderr.
Timestamps en UTC para consistencia entre entornos.
"""
import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Configura el logging global del sistema.
    Debe llamarse una sola vez al inicio de automata.py.
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "automata.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)
    # Timestamps en UTC
    formatter.converter = __import__("time").gmtime

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # Rotación: 5MB × 3 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # stderr para MAILTO de cron
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)

    # Evitar duplicar handlers si se llama más de una vez
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(stderr_handler)
