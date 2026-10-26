from __future__ import annotations

from .qwen_ayarlar import _CANCELLED
from .strada import (
    strata_chat,
    strata_modelini_hazirla,
    strata_motorunu_durdur,
)


# BLOK BAŞLIĞI: MODEL GEÇİŞ KAPISI - BAŞLANGIÇ

def modeli_hazirla(session, model):
    return strata_modelini_hazirla(
        session,
        model,
    )


def model_chat(session, **chat_arguments):
    return strata_chat(
        session,
        **chat_arguments,
    )


def model_motorunu_durdur(session):
    return strata_motorunu_durdur(
        session
    )


def uzman_model_cagir(
    session,
    model,
    **chat_arguments,
):
    ready = modeli_hazirla(
        session,
        model,
    )

    if ready is _CANCELLED:
        return _CANCELLED

    return model_chat(
        session,
        **chat_arguments,
    )

# BLOK BAŞLIĞI: MODEL GEÇİŞ KAPISI - BİTİŞ
