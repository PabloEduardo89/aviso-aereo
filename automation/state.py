"""
Rastreamento de "já postei isso" — evita que a automação totalmente
automática (run_cycle.py) publique o mesmo aviso de novo a cada execução
agendada. Sem isso, um NOTAM de pista fechada por 3 dias viraria um post novo
a cada checagem (de hora em hora) enquanto ele seguisse em vigor.

O arquivo de estado (state/posted.json) é comitado de volta no repositório a
cada execução do GitHub Actions — é o jeito mais simples de persistir estado
entre execuções de um runner que começa do zero toda vez.
"""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "state", "posted.json")


def load_state() -> dict:
    if not os.path.isfile(STATE_PATH):
        return {}
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def is_posted(state: dict, key: str) -> bool:
    return key in state


def mark_posted(state: dict, key: str, media_id: str, timestamp: str) -> None:
    state[key] = {"media_id": media_id, "posted_at": timestamp}


# chave "_meta" guarda controle da automação (não é uma condição postada) — usada
# pelo fallback educativo (run_cycle.py) pra saber há quanto tempo não sai post
# nenhum e qual o próximo tópico da rotação (fallback_content.py)
def get_meta(state: dict, key: str, default=None):
    return state.get("_meta", {}).get(key, default)


def set_meta(state: dict, key: str, value) -> None:
    state.setdefault("_meta", {})[key] = value
