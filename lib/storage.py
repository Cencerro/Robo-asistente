"""
Helpers para persistencia JSON con escritura atómica.
La escritura atómica evita ficheros corruptos si el proceso se interrumpe.
"""
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from lib.exceptions import StorageError

logger = logging.getLogger(__name__)


def read_json(path: Path) -> dict[str, Any]:
    """
    Lee un fichero JSON. Devuelve dict vacío si no existe.
    Lanza StorageError si el fichero existe pero no es JSON válido.
    """
    if not path.exists():
        logger.debug("Fichero no encontrado, devolviendo dict vacío: %s", path)
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Leídos %d bytes desde %s", path.stat().st_size, path)
        return data
    except json.JSONDecodeError as e:
        raise StorageError(f"JSON inválido en {path}: {e}") from e
    except OSError as e:
        raise StorageError(f"Error leyendo {path}: {e}") from e


def write_json(path: Path, data: dict[str, Any]) -> None:
    """
    Escribe datos como JSON con escritura atómica (write + rename).
    Crea los directorios intermedios si no existen.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Escribir en fichero temporal en el mismo directorio para que rename
        # sea atómico (mismo filesystem)
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=".tmp_", suffix=".json"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
            logger.debug("Escrito JSON en %s", path)
        except Exception:
            # Limpiar temporal si algo falla
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as e:
        raise StorageError(f"Error escribiendo {path}: {e}") from e


def menu_path(data_dir: str, year: int, month: int) -> Path:
    """Devuelve la ruta canónica del fichero JSON mensual de menús."""
    return Path(data_dir) / "menus" / f"menu_{year:04d}_{month:02d}.json"
