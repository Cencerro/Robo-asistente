"""
Tests para tasks/menu/scraper.py.
Usa respx para interceptar peticiones HTTP sin acceso real a la red.
"""
import pytest
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
    def test_finds_menu_pdf(self, monkeypatch):
        source_url = "https://www.maisonslaffitte.fr/restauration-scolaire/10166/"
        monkeypatch.setattr(
            "tasks.menu.scraper._fetch_page",
            lambda url: _HTML_WITH_MENU_PDF,
        )

        url = find_pdf_url(source_url)
        assert url == "https://www.maisonslaffitte.fr/uploads/menu-mars-2026.pdf"

    def test_falls_back_to_first_pdf_if_no_pattern_match(self, monkeypatch):
        source_url = "https://example.com/page/"
        monkeypatch.setattr(
            "tasks.menu.scraper._fetch_page",
            lambda url: _HTML_WITH_PDF_NO_PATTERN,
        )

        url = find_pdf_url(source_url)
        assert url == "https://example.com/uploads/document.pdf"

    def test_raises_if_no_pdf_found(self, monkeypatch):
        source_url = "https://example.com/page/"
        monkeypatch.setattr(
            "tasks.menu.scraper._fetch_page",
            lambda url: _HTML_NO_PDF,
        )

        with pytest.raises(ScrapingError, match="No se encontraron enlaces a PDF"):
            find_pdf_url(source_url)

    def test_raises_on_http_error(self, monkeypatch):
        source_url = "https://example.com/page/"

        def raise_404(url):
            raise ScrapingError("HTTP 404 al obtener " + url)

        monkeypatch.setattr("tasks.menu.scraper._fetch_page", raise_404)

        with pytest.raises(ScrapingError, match="HTTP 404"):
            find_pdf_url(source_url)

    def test_prefers_newest_menu_pdf(self, monkeypatch):
        """Debe preferir el PDF más reciente cuando hay varios enlaces de menú."""
        source_url = "https://example.com/page/"
        html = """
        <html><body>
          <a href="/menu-enero-2026.pdf">Menu enero 2026</a>
          <a href="/menu-febrero-2026.pdf">Menu febrero 2026</a>
        </body></html>
        """
        monkeypatch.setattr(
            "tasks.menu.scraper._fetch_page",
            lambda url: html,
        )

        url = find_pdf_url(source_url)
        assert url.endswith("/menu-febrero-2026.pdf")


class TestDownloadPdf:
    def _patch_httpx_client(self, monkeypatch, pdf_url: str, status_code: int, content: bytes):
        import contextlib

        request = httpx.Request("GET", pdf_url)
        response = httpx.Response(status_code, content=content, request=request)

        class DummyClient:
            def __init__(self, *args, **kwargs):
                self._response = response

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def stream(self, method, url):
                @contextlib.contextmanager
                def _cm():
                    yield self._response

                return _cm()

        monkeypatch.setattr("tasks.menu.scraper.httpx.Client", DummyClient)

    def test_downloads_pdf_to_path(self, tmp_path, monkeypatch):
        pdf_content = b"%PDF-1.4 fake pdf content"
        pdf_url = "https://example.com/menu.pdf"
        dest = tmp_path / "menu.pdf"

        self._patch_httpx_client(monkeypatch, pdf_url, 200, pdf_content)
        download_pdf(pdf_url, dest)

        assert dest.exists()
        assert dest.read_bytes() == pdf_content

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        pdf_url = "https://example.com/menu.pdf"
        dest = tmp_path / "deep" / "nested" / "menu.pdf"

        self._patch_httpx_client(monkeypatch, pdf_url, 200, b"%PDF")
        download_pdf(pdf_url, dest)

        assert dest.exists()

    def test_raises_on_http_error(self, tmp_path, monkeypatch):
        pdf_url = "https://example.com/notfound.pdf"
        self._patch_httpx_client(monkeypatch, pdf_url, 404, b"")

        with pytest.raises(ScrapingError, match="HTTP 404"):
            download_pdf(pdf_url, tmp_path / "menu.pdf")
