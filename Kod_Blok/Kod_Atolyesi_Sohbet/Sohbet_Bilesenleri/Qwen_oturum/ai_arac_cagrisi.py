from __future__ import annotations

from .qwen_ayarlar import NORMAL_MODEL, YUKSEK_MODEL


def model_rolu_sec(model_mode, text=None):
    mode = str(model_mode or "normal").strip().casefold()

    if mode == "yuksek":
        return YUKSEK_MODEL

    return NORMAL_MODEL