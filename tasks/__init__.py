"""
Registro de tareas disponibles en el sistema.
Cada entrada mapea un nombre de tarea al módulo que implementa run().
"""
import importlib
import logging

from lib.exceptions import RoboAssistenteError

logger = logging.getLogger(__name__)

# Registro explícito de tareas: nombre → módulo
TASK_REGISTRY: dict[str, str] = {
    "menu": "tasks.menu.task",
    # "weather": "tasks.weather.task",
}


def run_task(name: str) -> None:
    """Despacha y ejecuta la tarea con el nombre dado."""
    if name not in TASK_REGISTRY:
        available = ", ".join(TASK_REGISTRY.keys())
        raise RoboAssistenteError(
            f"Tarea desconocida: '{name}'. Disponibles: {available}"
        )

    module_path = TASK_REGISTRY[name]
    logger.info("Despachando tarea '%s' desde módulo '%s'", name, module_path)

    module = importlib.import_module(module_path)
    module.run()
