from __future__ import annotations

from pathlib import Path


STRATA_HOST = "http://127.0.0.1:8080"
STRATA_CHAT_URL = f"{STRATA_HOST}/v1/chat/completions"
STRATA_HEALTH_URL = f"{STRATA_HOST}/health"
STRATA_API_MODEL = "strata"

DAILY_MODEL = "gunluk"
DAILY_CONTEXT_SIZE = 131072

CODER_MODEL = "kodcu"
CODER_CONTEXT_SIZE = 131072

STRATA_MODELS = {
    DAILY_MODEL: {
        "family": "swift",
        "model": "IQ2_XS",
        "context": DAILY_CONTEXT_SIZE,
    },
    CODER_MODEL: {
        "family": "swift",
        "model": "IQ3_S",
        "context": CODER_CONTEXT_SIZE,
    },
}

VISION_MODEL = DAILY_MODEL
VISION_CONTEXT_SIZE = DAILY_CONTEXT_SIZE

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

PROJECT_ROOT = Path(__file__).resolve().parents[4]
QWEN_MD_PATH = PROJECT_ROOT / ".qwen" / "QWEN.md"

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOOL_ROUNDS = 20
MAX_WEB_TOOL_CALLS = 10

_STOP = object()
_CANCELLED = object()
