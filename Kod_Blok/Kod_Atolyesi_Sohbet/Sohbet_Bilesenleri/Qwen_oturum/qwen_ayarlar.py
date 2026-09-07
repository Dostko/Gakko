from __future__ import annotations

from pathlib import Path


OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gakko-qwen38-64k-gpu:latest"
OLLAMA_CONTEXT_SIZE = 65536

VISION_MODEL = "qwen3-vl:8b"
VISION_CONTEXT_SIZE = 32768

IMAGE_EXTENSIONS = frozenset({
    ".jpeg",
    ".jpg",
    ".tif",
    ".tiff",
    ".png",
    ".svg",
    ".webp",
})

PDF_EXTENSIONS = frozenset({".pdf"})

MIN_PDF_TEXT_CHARS = 80
MAX_PDF_TEXT_CHARS = 50000
MAX_PDF_VISION_PAGES = 20
PDF_RENDER_WIDTH = 1600
PDF_RENDER_MAX_HEIGHT = 2400

PROJECT_ROOT = Path(r"D:\Gakko")
QWEN_MD_PATH = PROJECT_ROOT / ".qwen" / "QWEN.md"

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOOL_ROUNDS = 12

_STOP = object()
_CANCELLED = object()