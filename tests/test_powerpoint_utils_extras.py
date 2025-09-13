from src.document_processor.processors.powerpoint_processor import PowerPointProcessor
from src.document_processor.config import ConverterConfig


def test_get_image_extension_magic_bytes():
    p = PowerPointProcessor(ConverterConfig())
    assert p.get_image_extension(b"\xFF\xD8rest") == ".jpg"
    assert p.get_image_extension(b"\x89PNG\r\n\x1A\nrest") == ".png"
    assert p.get_image_extension(b"GIF89a rest") == ".gif"
    assert p.get_image_extension(b"RIFFxxxxWEBPrest") == ".webp"
    assert p.get_image_extension(b"unknown-bytes") == ".png"

