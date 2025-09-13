import os
import io
import json
from typing import Any

import pytest

from src.document_processor.processors.excel_csv_processor import ExcelCsvProcessor
from src.document_processor.config import ConverterConfig


@pytest.fixture
def processor() -> ExcelCsvProcessor:
    # Minimal config; defaults for max_rows/columns come from processor
    return ExcelCsvProcessor(ConverterConfig())


def test_supported_extensions_and_can_process_flags():
    exts = ExcelCsvProcessor.get_supported_extensions()
    assert set(exts) == {".csv", ".xlsx", ".xls", ".tsv"}

    # Typical supported files
    assert ExcelCsvProcessor.can_process("report.csv") is True
    assert ExcelCsvProcessor.can_process("table.tsv") is True
    assert ExcelCsvProcessor.can_process("workbook.xlsx") is True

    # Temp Excel file should be ignored
    assert ExcelCsvProcessor.can_process("~$temp.xlsx") is False


def test_csv_semicolon_detection(processor: ExcelCsvProcessor, tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("a;b\n1;2\n", encoding="utf-8")

    content, meta = processor.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parser"] == "pandas_csv"
    assert meta["file_type"] == "CSV"
    assert meta["separator"] == ";"
    import re
    assert content is not None
    assert re.search(r"\|\s*a\s*\|\s*b\s*\|", content)
    assert re.search(r"\|\s*1\s*\|\s*2\s*\|", content)


def test_csv_comma_detection(processor: ExcelCsvProcessor, tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")

    content, meta = processor.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parser"] == "pandas_csv"
    assert meta["separator"] == ","
    import re
    assert content is not None
    assert re.search(r"\|\s*a\s*\|\s*b\s*\|", content)
    assert re.search(r"\|\s*1\s*\|\s*2\s*\|", content)


def test_csv_empty_file(processor: ExcelCsvProcessor, tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")

    content, meta = processor.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    # For fully empty files, processor returns an error via exception path
    assert content is None
    assert meta["parser"] == "excel_csv_parser"
    assert "Unable to parse CSV" in meta["error"]


def test_tsv_basic(processor: ExcelCsvProcessor, tmp_path):
    p = tmp_path / "data.tsv"
    p.write_text("a\tb\n1\t2\n", encoding="utf-8")

    content, meta = processor.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parser"] == "pandas_tsv"
    assert meta["file_type"] == "TSV"
    import re
    assert content is not None
    assert re.search(r"\|\s*a\s*\|\s*b\s*\|", content)
    assert re.search(r"\|\s*1\s*\|\s*2\s*\|", content)


def test_bundle_csv_detection_and_processing(processor: ExcelCsvProcessor, tmp_path):
    p = tmp_path / "bundle.csv"
    # First line indicates bundle file; include quotes and commas
    p.write_text(
        "bundle,\"key\",en,pl\nmain,\"GREETING\",\"Hello\",\"Cześć\"\n",
        encoding="utf-8",
    )

    content, meta = processor.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parser"] == "pandas_bundle_csv"
    assert meta["file_type"] == "Translation Bundle"
    assert set(meta["languages"]) == {"en", "pl"}
    assert content is not None
    assert "## Translation Data" in content
    # Table header should reflect columns (spacing in to_markdown can vary)
    import re
    assert re.search(r"\|\s*bundle\s*\|\s*key\s*\|\s*en\s*\|\s*pl\s*\|", content)


def test_excel_basic(processor: ExcelCsvProcessor, tmp_path):
    pandas = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")

    df = pandas.DataFrame({"a": [1, 2], "b": [3, 4]})
    xlsx = tmp_path / "book.xlsx"
    df.to_excel(os.fspath(xlsx), index=False)

    content, meta = processor.process(os.fspath(xlsx), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parser"] == "pandas_excel"
    assert meta["file_type"] == "Excel"
    assert meta["sheet_count"] >= 1
    # Ensure first sheet table exists (spacing can vary)
    import re
    assert content is not None
    assert re.search(r"\|\s*a\s*\|\s*b\s*\|", content)


def test_csv_fallback_skip_bad_lines(tmp_path, monkeypatch):
    pandas = pytest.importorskip("pandas")
    from pandas import DataFrame

    calls = {"stage": []}

    def fake_read_csv(path, *args, **kwargs):
        # Scoring stage: has nrows specified
        if kwargs.get("nrows") is not None:
            return DataFrame({"a": [1], "b": [2]})
        # Strict stage (no on_bad_lines/engine): fail
        if "on_bad_lines" not in kwargs and "engine" not in kwargs:
            calls["stage"].append("strict")
            raise ValueError("strict fail")
        # Skip bad lines stage
        if kwargs.get("on_bad_lines") == "skip" and "engine" not in kwargs:
            calls["stage"].append("skip")
            return DataFrame({"a": [1], "b": [2]})
        raise AssertionError(f"Unexpected kwargs: {kwargs}")

    monkeypatch.setattr(pandas, "read_csv", fake_read_csv)

    p = tmp_path / "data.csv"
    p.write_text("badline\na,b\n1,2\n", encoding="utf-8")

    from src.document_processor.processors.excel_csv_processor import ExcelCsvProcessor
    proc = ExcelCsvProcessor(ConverterConfig())
    content, meta = proc.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parsing_strategy"] == "skip_bad_lines"
    assert "**Parsing Strategy:** skip_bad_lines" in content


def test_csv_fallback_python_engine(tmp_path, monkeypatch):
    pandas = pytest.importorskip("pandas")
    from pandas import DataFrame

    calls = {"stage": []}

    def fake_read_csv(path, *args, **kwargs):
        if kwargs.get("nrows") is not None:
            return DataFrame({"a": [1], "b": [2]})
        if "on_bad_lines" not in kwargs and "engine" not in kwargs:
            calls["stage"].append("strict")
            raise ValueError("strict fail")
        if kwargs.get("on_bad_lines") == "skip" and "engine" not in kwargs:
            calls["stage"].append("skip")
            raise ValueError("skip fail")
        if kwargs.get("engine") == "python":
            calls["stage"].append("python")
            return DataFrame({"a": [1], "b": [2]})
        raise AssertionError(f"Unexpected kwargs: {kwargs}")

    monkeypatch.setattr(pandas, "read_csv", fake_read_csv)

    p = tmp_path / "data.csv"
    p.write_text("bad\na,b\n1,2\n", encoding="utf-8")

    from src.document_processor.processors.excel_csv_processor import ExcelCsvProcessor
    proc = ExcelCsvProcessor(ConverterConfig())
    content, meta = proc.process(os.fspath(p), os.fspath(tmp_path), os.fspath(tmp_path / "media"))

    assert meta["parsing_strategy"] == "python_engine"
    assert "**Parsing Strategy:** python_engine" in content


def test_format_bundle_table_fallback(monkeypatch):
    pandas = pytest.importorskip("pandas")
    df = pandas.DataFrame({"bundle": ["main"], "key": ["HELLO"], "en": ["Hello"]})

    # Force ImportError within to_markdown so fallback path is used
    monkeypatch.setattr(type(df), "to_markdown", lambda self, **kw: (_ for _ in ()).throw(ImportError("no tabulate")))

    from src.document_processor.processors.excel_csv_processor import ExcelCsvProcessor
    proc = ExcelCsvProcessor(ConverterConfig())
    table = proc._format_bundle_table(df)
    assert table.startswith("| bundle | key | en |")
