"""
Tests para tasks/menu/scraper.py.
Usa respx para interceptar peticiones HTTP sin acceso real a la red.
"""
import pytest
import respx
import httpx
from pathlib import Path

from tasks.menu.scraper import find_pdf_url, download_pdf
from lib.exceptions import ScrapingError


# HTML de ejemplo que simula la página de Maisons-Laffitte
_HTML_WITH_MENU_PDF = """
<html>
<body>
  <h1>Restauration scolaire</h1>
  <ul>
    <li><a href="/uploads/menu-mars-2026.pdf">Menu mars 2026</a></li>
    <li><a href="/uploads/autre-doc.pdf">Autre document</a></li>
  </ul>
</body>
</html>
"""

_HTML_WITH_PDF_NO_PATTERN = """
<html>
<body>
  <a href="/uploads/document.pdf">Télécharger</a>
</body>
</html>
"""

_HTML_NO_PDF = """
<html>
<body>
  <p>Aucun fichier disponible</p>
</body>
</html>
"""


class TestFindPdfUrl:
    @respx.mock
    def test_finds_menu_pdf(self):
        source_url = "https://www.maisonslaffitte.fr/restauration-scolaire/10166/"
        respx.get(source_url).mock(
            return_value=httpx.Response(200, text=_HTML_WITH_MENU_PDF)
        )

        url = find_pdf_url(source_url)
        assert url == "https://www.maisonslaffitte.fr/uploads/menu-mars-2026.pdf"

    @respx.mock
    def test_falls_back_to_first_pdf_if_no_pattern_match(self):
        source_url = "https://example.com/page/"
        respx.get(source_url).mock(
            return_value=httpx.Response(200, text=_HTML_WITH_PDF_NO_PATTERN)
        )

        url = find_pdf_url(source_url)
        assert url == "https://example.com/uploads/document.pdf"

    @respx.mock
    def test_raises_if_no_pdf_found(self):
        source_url = "https://example.com/page/"
        respx.get(source_url).mock(
            return_value=httpx.Response(200, text=_HTML_NO_PDF)
        )

        with pytest.raises(ScrapingError, match="No se encontraron enlaces a PDF"):
            find_pdf_url(source_url)

    @respx.mock
    def test_raises_on_http_error(self):
        source_url = "https://example.com/page/"
        respx.get(source_url).mock(return_value=httpx.Response(404))

        with pytest.raises(ScrapingError, match="HTTP 404"):
            find_pdf_url(source_url)

    @respx.mock
    def test_prefers_menu_pdf_over_others(self):
        """Debe preferir el PDF que contiene 'menu' en la URL o texto."""
        source_url = "https://example.com/page/"
        html = """
        <html><body>
          <a href="/primero.pdf">Otro documento</a>
          <a href="/menu-avril-2026.pdf">Menu avril</a>
        </body></html>
        """
        respx.get(source_url).mock(
            return_value=httpx.Response(200, text=html)
        )

        url = find_pdf_url(source_url)
        assert "menu" in url


class TestDownloadPdf:
    @respx.mock
    def test_downloads_pdf_to_path(self, tmp_path):
        pdf_content = b"%PDF-1.4 fake pdf content"
        pdf_url = "https://example.com/menu.pdf"
        respx.get(pdf_url).mock(
            return_value=httpx.Response(200, content=pdf_content)
        )

        dest = tmp_path / "menu.pdf"
        download_pdf(pdf_url, dest)

        assert dest.exists()
        assert dest.read_bytes() == pdf_content

    @respx.mock
    def test_creates_parent_dirs(self, tmp_path):
        pdf_url = "https://example.com/menu.pdf"
        respx.get(pdf_url).mock(
            return_value=httpx.Response(200, content=b"%PDF")
        )

        dest = tmp_path / "deep" / "nested" / "menu.pdf"
        download_pdf(pdf_url, dest)

        assert dest.exists()

    @respx.mock
    def test_raises_on_http_error(self, tmp_path):
        pdf_url = "https://example.com/notfound.pdf"
        respx.get(pdf_url).mock(return_value=httpx.Response(404))

        with pytest.raises(ScrapingError, match="HTTP 404"):
            download_pdf(pdf_url, tmp_path / "menu.pdf")
