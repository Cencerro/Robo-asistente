"""
Tests para lib/storage.py.
"""
import json
import pytest
from pathlib import Path

from lib.storage import read_json, write_json, menu_path
from lib.exceptions import StorageError


class TestReadJson:
    def test_returns_empty_dict_if_not_exists(self, tmp_path):
        result = read_json(tmp_path / "nonexistent.json")
        assert result == {}

    def test_reads_valid_json(self, tmp_path):
        data = {"key": "value", "number": 42}
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data), encoding="utf-8")

        result = read_json(f)
        assert result == data

    def test_raises_on_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(StorageError, match="JSON inválido"):
            read_json(f)

    def test_reads_unicode(self, tmp_path):
        data = {"plat": "Poulet rôti", "dessert": "Crème brûlée"}
        f = tmp_path / "unicode.json"
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = read_json(f)
        assert result["plat"] == "Poulet rôti"
        assert result["dessert"] == "Crème brûlée"


class TestWriteJson:
    def test_writes_and_reads_back(self, tmp_path):
        data = {"days": {"2026-03-18": {"plat": "Poulet"}}}
        path = tmp_path / "output.json"

        write_json(path, data)

        result = read_json(path)
        assert result == data

    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "file.json"
        write_json(path, {"test": True})
        assert path.exists()

    def test_overwrites_existing_file(self, tmp_path):
        path = tmp_path / "file.json"
        write_json(path, {"v": 1})
        write_json(path, {"v": 2})

        result = read_json(path)
        assert result["v"] == 2

    def test_preserves_unicode(self, tmp_path):
        data = {"plat": "Poulet rôti", "dessert": "Crème brûlée"}
        path = tmp_path / "unicode.json"
        write_json(path, data)

        result = read_json(path)
        assert result["plat"] == "Poulet rôti"

    def test_atomic_write_leaves_no_tmp_files(self, tmp_path):
        path = tmp_path / "atomic.json"
        write_json(path, {"ok": True})

        # No debe quedar ningún fichero temporal
        tmp_files = list(tmp_path.glob(".tmp_*.json"))
        assert tmp_files == []


class TestMenuPath:
    def test_returns_correct_path(self):
        path = menu_path("data", 2026, 3)
        assert str(path) == "data/menus/menu_2026_03.json"

    def test_zero_pads_month(self):
        path = menu_path("data", 2026, 1)
        assert "menu_2026_01.json" in str(path)

    def test_custom_data_dir(self):
        path = menu_path("/custom/dir", 2025, 12)
        assert "menu_2025_12.json" in str(path)
