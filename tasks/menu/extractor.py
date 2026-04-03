"""
Extractor de menús desde PDF usando Claude Files API.
Sube el PDF, extrae los menús estructurados y los almacena en JSON.
"""
import json
import logging
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from lib.claude_client import ClaudeClient
from lib.exceptions import ClaudeAPIError
from tasks.menu.scraper import download_pdf

logger = logging.getLogger(__name__)

# Prompt de extracción: instruye a Claude para devolver JSON estructurado
_EXTRACTION_PROMPT = """
Ce document est le menu mensuel de la restauration scolaire. Les jours sont divisés en 5 colonnes, et pas tous les jours il y a le même nombre de plats.
Extrais tous les menus jour par jour et renvoie UNIQUEMENT un objet JSON valide
(sans markdown, sans explication, sans texte avant ou après).

Structure exacte à respecter :
{
  "days": {
    "YYYY-MM-DD": {
      "dejeuner": {
        "entree": "..." ou null,
        "plat": "...",
        "garniture": "..." ou null,
        "dessert": "..."
      },
      "gouter": {
        "composantes": ["...", "..."]
      }
    }
  }
}

Règles :
- Les dates doivent être au format ISO 8601 (YYYY-MM-DD)
- Respecte exactement le texte en français tel qu'il apparaît dans le PDF
- Si un champ est absent, utilise null
- Si le goûter est absent pour un jour, omets la clé "gouter"
- N'inclus que les jours où il y a effectivement un menu (pas les week-ends ni jours fériés)
""".strip()


def extract_menus(
    pdf_url: str,
    menu_data: dict[str, Any],
    claude_client: ClaudeClient,
    year: int,
    month: int,
) -> dict[str, Any]:
    """
    Extrae los menús del PDF y los añade a menu_data.
    Reutiliza el file_id si ya existe en menu_data (evita re-subir).
    Devuelve menu_data actualizado con los menús del mes.
    """
    file_id = menu_data.get("claude_file_id")

    if not file_id:
        # Descargar PDF y subirlo a Claude Files API
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / f"menu_{year:04d}_{month:02d}.pdf"
            download_pdf(pdf_url, pdf_path)
            file_id = claude_client.upload_file(pdf_path)

        menu_data["claude_file_id"] = file_id
        logger.info("PDF subido a Claude Files API: file_id=%s", file_id)
    else:
        logger.info("Reutilizando file_id existente: %s", file_id)

    # Extraer menús con Claude
    logger.info("Extrayendo menús con Claude...")
    raw_response = claude_client.extract_from_file(file_id, _EXTRACTION_PROMPT)

    # Parsear JSON de la respuesta
    days = _parse_menu_json(raw_response)
    logger.info("Menús extraídos: %d días", len(days))

    menu_data["days"] = days
    return menu_data


def _parse_menu_json(raw: str) -> dict[str, Any]:
    """
    Parsea la respuesta de Claude y extrae el diccionario de días.
    Maneja casos donde Claude incluye texto antes o después del JSON.
    """
    # Intentar parsear directamente
    try:
        data = json.loads(raw)
        return data.get("days", data)
    except json.JSONDecodeError:
        pass

    # Buscar bloque JSON en la respuesta (Claude a veces añade texto)
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            data = json.loads(match.group())
            return data.get("days", data)
        except json.JSONDecodeError:
            pass

    raise ClaudeAPIError(
        f"No se pudo parsear JSON de la respuesta de Claude. "
        f"Primeros 200 chars: {raw[:200]}"
    )


def split_days_by_month(days: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Agrupa los días extraídos por mes.
    Devuelve {YYYY-MM: {YYYY-MM-DD: menu, ...}, ...}
    """
    by_month: dict[str, dict[str, Any]] = {}
    for date_str, menu in days.items():
        month_key = date_str[:7]  # YYYY-MM
        by_month.setdefault(month_key, {})[date_str] = menu
    return by_month


def get_today_menu(menu_data: dict[str, Any], today: date | None = None) -> dict[str, Any] | None:
    """
    Obtiene el menú del día de hoy desde el JSON de menús.
    Devuelve None si no hay menú para hoy (día festivo, fin de semana, etc.).
    """
    if today is None:
        today = date.today()

    today_key = today.isoformat()
    days = menu_data.get("days", {})
    menu = days.get(today_key)

    if menu is None:
        logger.info("No hay menú para %s", today_key)
    else:
        logger.info("Menú encontrado para %s", today_key)

    return menu
