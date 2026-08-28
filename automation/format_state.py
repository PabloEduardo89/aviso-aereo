"""
Estado de "formato usado por último" — controla as rotações determinísticas
do molde alternativo "clássico" (ver style.py): qual molde saiu no post real
anterior, qual formato de título, qual abertura de legenda e qual foto de
cada categoria — pra nunca repetir a mesma escolha duas vezes seguidas, sem
depender de sorteio aleatório (pedido do usuário, 2026-08-28).

Assim como state/posted.json, esse arquivo é comitado de volta no
repositório a cada execução do GitHub Actions (ver commit_state.py) — sem
isso, cada execução do runner (que começa do zero) perderia a memória da
última escolha e não teria como garantir "nunca duas vezes seguidas".
"""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "state", "last_post_format.json")

_DEFAULTS = {
    "last_mold": "moderno",
    "title_format_index": -1,
    "caption_opening_index": -1,
    "image_bank_index": {},
}


def load() -> dict:
    if not os.path.isfile(STATE_PATH):
        return {**_DEFAULTS, "image_bank_index": {}}
    with open(STATE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {**_DEFAULTS, **data}


def save(data: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
