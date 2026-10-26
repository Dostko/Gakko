from __future__ import annotations

from pathlib import Path


NORMAL_MODEL = "normal"
NORMAL_CONTEXT_SIZE = 131072

YUKSEK_MODEL = "yuksek"
YUKSEK_CONTEXT_SIZE = 131072

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

PROJECT_ROOT = Path(__file__).resolve().parents[4]
QWEN_MD_PATH = PROJECT_ROOT / ".qwen" / "QWEN.md"

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOOL_ROUNDS = 20
MAX_WEB_TOOL_CALLS = 10

_STOP = object()
_CANCELLED = object()