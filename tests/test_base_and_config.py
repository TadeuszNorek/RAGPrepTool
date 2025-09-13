import os
from typing import List

from src.document_processor.processors.base_processor import BaseDocumentProcessor
from src.document_processor.config import ConverterConfig


class DummyProc(BaseDocumentProcessor):
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        return [".abc", ".xyz"]


def test_is_common_temp_file_patterns():
    assert BaseDocumentProcessor._is_common_temp_file("~$file.docx") is True
    assert BaseDocumentProcessor._is_common_temp_file(".~lock") is True
    assert BaseDocumentProcessor._is_common_temp_file("note.tmp") is True
    assert BaseDocumentProcessor._is_common_temp_file("backup.bak") is True
    assert BaseDocumentProcessor._is_common_temp_file("Thumbs.db") is True
    assert BaseDocumentProcessor._is_common_temp_file("desktop.ini") is True
    assert BaseDocumentProcessor._is_common_temp_file(".DS_Store") is True
    assert BaseDocumentProcessor._is_common_temp_file("regular.txt") is False


def test_can_process_uses_extensions_and_skips_temp():
    assert DummyProc.can_process("file.abc") is True
    assert DummyProc.can_process("FILE.XYZ") is True
    assert DummyProc.can_process("~$temp.abc") is False
    assert DummyProc.can_process("file.unsupported") is False


def test_converter_config_defaults_and_overrides():
    cfg = ConverterConfig({"apply_max_res": True, "pandoc_toc": True})
    d = cfg.to_dict()
    assert d["apply_max_res"] is True
    assert d["pandoc_toc"] is True
    # Defaults present
    assert "max_rows_display" in d and "max_columns_display" in d
    # get() fallback
    assert cfg.get("nonexistent", 123) == 123

