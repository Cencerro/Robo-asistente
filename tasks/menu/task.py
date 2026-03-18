"""
Orquestador de la tarea 'menu'.
Coordina scraper → extractor → sender con gestión de caché mensual.
"""
import logging
from datetime import date, timezone, datetime

from lib.claude_client import ClaudeClient
from lib.config import get_settings
from lib.storage import menu_path, read_json, write_json
from lib.telegram_client import TelegramClient
from tasks.menu.extractor import extract_menus, get_today_menu
from tasks.menu.scraper import find_pdf_url
from tasks.menu.sender import send_menu, send_no_menu

logger = logging.getLogger(__name__)


def run() -> None:
    """
    Punto de entrada de la tarea 'menu'.
    Flujo:
    1. Comprobar si ya existe el menú de hoy en caché → enviar directamente
    2. Si no: scrape URL del PDF → extraer menús → guardar en JSON → enviar
    """
    settings = get_settings()
    today = date.today()

    logger.info("=== Tarea 'menu' iniciada para %s ===", today.isoformat())

    # Ruta del fichero JSON mensual
    json_path = menu_path(settings.data_dir, today.year, today.month)
    menu_data = read_json(json_path)

    # Inicializar estructura base si es un fichero nuevo
    if not menu_data:
        menu_data = {
            "period": today.strftime("%Y-%m"),
            "source_url": settings.menu_source_url,
            "claude_file_id": None,
            "fetched_at": None,
            "days": {},
        }

    # Comprobar si ya tenemos el menú de hoy en caché
    today_menu = get_today_menu(menu_data, today)

    if today_menu is not None:
        logger.info("Menú de hoy encontrado en caché, saltando extracción")
    else:
        # Necesitamos obtener/actualizar los menús del mes
        logger.info("Menú de hoy no en caché, iniciando extracción")

        # Scrape: obtener URL del PDF
        pdf_url = find_pdf_url(settings.menu_source_url)

        # Actualizar source_url si cambió (URL cambia cada mes)
        if menu_data.get("source_url") != pdf_url:
            logger.info("URL del PDF actualizada: %s", pdf_url)

        # Extraer menús con Claude
        claude_client = ClaudeClient(settings.anthropic_api_key)
        menu_data = extract_menus(
            pdf_url=pdf_url,
            menu_data=menu_data,
            claude_client=claude_client,
            year=today.year,
            month=today.month,
        )

        # Registrar timestamp de la extracción
        menu_data["fetched_at"] = datetime.now(timezone.utc).isoformat()

        # Guardar JSON actualizado
        write_json(json_path, menu_data)
        logger.info("JSON de menús guardado en %s", json_path)

        # Obtener menú de hoy del JSON recién extraído
        today_menu = get_today_menu(menu_data, today)

    # Enviar por Telegram
    telegram_client = TelegramClient(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )

    if today_menu is not None:
        send_menu(today_menu, telegram_client, today)
    else:
        send_no_menu(telegram_client, today)

    logger.info("=== Tarea 'menu' completada ===")
