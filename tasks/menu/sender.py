"""
Formatea y envía el menú del día por Telegram.
Los mensajes se envían en francés.
"""
import logging
from datetime import date
from typing import Any

from lib.telegram_client import TelegramClient

logger = logging.getLogger(__name__)

# Nombres de días en francés
_JOURS = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}

# Nombres de meses en francés
_MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def format_menu(menu: dict[str, Any], today: date | None = None) -> str:
    """
    Formatea el menú del día como texto HTML para Telegram.
    """
    if today is None:
        today = date.today()

    jour = _JOURS[today.weekday()]
    mois = _MOIS[today.month]
    date_str = f"{jour} {today.day} {mois} {today.year}"

    lines = [f"<b>🍽 Menu du {date_str}</b>", ""]

    # Déjeuner
    dejeuner = menu.get("dejeuner", {})
    if dejeuner:
        lines.append("<b>🥗 Déjeuner</b>")
        if dejeuner.get("entree"):
            lines.append(f"  Entrée : {dejeuner['entree']}")
        if dejeuner.get("plat"):
            lines.append(f"  Plat : {dejeuner['plat']}")
        if dejeuner.get("garniture"):
            lines.append(f"  Garniture : {dejeuner['garniture']}")
        if dejeuner.get("dessert"):
            lines.append(f"  Dessert : {dejeuner['dessert']}")
        lines.append("")

    # Goûter
    gouter = menu.get("gouter", {})
    if gouter and gouter.get("composantes"):
        lines.append("<b>🍪 Goûter</b>")
        composantes = " · ".join(gouter["composantes"])
        lines.append(f"  {composantes}")

    return "\n".join(lines).strip()


def send_menu(
    menu: dict[str, Any],
    telegram_client: TelegramClient,
    today: date | None = None,
) -> None:
    """
    Formatea y envía el menú del día por Telegram.
    """
    if today is None:
        today = date.today()

    text = format_menu(menu, today)
    logger.info("Enviando menú del %s por Telegram", today.isoformat())
    telegram_client.send_message(text)


def send_no_menu(
    telegram_client: TelegramClient,
    today: date | None = None,
) -> None:
    """
    Envía un mensaje indicando que no hay menú para hoy.
    """
    if today is None:
        today = date.today()

    jour = _JOURS[today.weekday()]
    mois = _MOIS[today.month]
    date_str = f"{jour} {today.day} {mois} {today.year}"

    text = f"ℹ️ Pas de menu pour le {date_str} (jour férié ou vacances scolaires)."
    logger.info("No hay menú para %s, notificando", today.isoformat())
    telegram_client.send_message(text)
