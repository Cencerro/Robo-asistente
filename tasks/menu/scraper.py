"""
Scraper para obtener la URL del PDF del menú mensual.
Target: https://www.maisonslaffitte.fr/restauration-scolaire/10166/
"""
import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.exceptions import ScrapingError

logger = logging.getLogger(__name__)

# Timeout para peticiones HTTP
_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 30.0

# Patrón para identificar enlaces a PDFs de menú
_PDF_PATTERN = re.compile(r"menu|repas|restauration", re.IGNORECASE)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch_page(url: str) -> str:
    """Descarga el HTML de la página con reintentos."""
    logger.debug("GET %s", url)
    try:
        with httpx.Client(
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; robo-assistente/1.0)"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        raise ScrapingError(
            f"HTTP {e.response.status_code} al obtener {url}"
        ) from e
    except httpx.HTTPError as e:
        raise ScrapingError(f"Error HTTP al obtener {url}: {e}") from e


def find_pdf_url(source_url: str) -> str:
    """
    Descarga la página y busca el enlace al PDF del menú mensual.
    Devuelve la URL absoluta del PDF.
    Lanza ScrapingError si no encuentra ningún PDF.
    """
    logger.info("Buscando PDF de menú en: %s", source_url)

    html = _fetch_page(source_url)
    soup = BeautifulSoup(html, "lxml")

    # Buscar todos los enlaces a PDF
    pdf_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            pdf_links.append((a, href))

    if not pdf_links:
        raise ScrapingError(f"No se encontraron enlaces a PDF en {source_url}")

    logger.debug("PDFs encontrados: %d", len(pdf_links))

    # Preferir PDFs que mencionen "menu", "repas" o "restauration"
    for a, href in pdf_links:
        text = (a.get_text() + href).lower()
        if _PDF_PATTERN.search(text):
            pdf_url = urljoin(source_url, href)
            logger.info("PDF de menú encontrado: %s", pdf_url)
            return pdf_url

    # Si ninguno coincide con el patrón, usar el primero
    _, href = pdf_links[0]
    pdf_url = urljoin(source_url, href)
    logger.warning(
        "Ningún PDF coincide con patrón de menú, usando el primero: %s", pdf_url
    )
    return pdf_url


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def download_pdf(pdf_url: str, dest_path: "Path") -> None:  # noqa: F821
    """
    Descarga el PDF a dest_path con reintentos.
    """
    from pathlib import Path

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Descargando PDF: %s → %s", pdf_url, dest_path)
    try:
        with httpx.Client(
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=60.0),
            follow_redirects=True,
        ) as client:
            with client.stream("GET", pdf_url) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        size_kb = dest_path.stat().st_size // 1024
        logger.info("PDF descargado (%d KB): %s", size_kb, dest_path)

    except httpx.HTTPStatusError as e:
        raise ScrapingError(
            f"HTTP {e.response.status_code} al descargar PDF {pdf_url}"
        ) from e
    except httpx.HTTPError as e:
        raise ScrapingError(f"Error HTTP al descargar PDF {pdf_url}: {e}") from e
