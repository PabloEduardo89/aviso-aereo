"""
Sistema de variação determinística do molde "clássico" (pedido do usuário,
2026-08-28) — um SEGUNDO molde visual pros posts de alerta real, que convive
com o molde único fotográfico atual (slide.render_photo_slide, apelidado
"moderno" aqui) sem substituí-lo. Os dois moldes alternam entre si de post
em post (ver next_mold) — "uma mini linha de edição", não uma escolha única.

Toda variação AQUI DENTRO — categoria de imagem, intensidade do vermelho,
selo de categoria, quantidade de slides, formato do título, abertura da
legenda — é uma regra determinística amarrada aos dados reais do evento
(tipo, gravidade, horário, riqueza de contexto), nunca um sorteio livre.
O que evita repetir a mesma escolha duas vezes seguidas é um índice cíclico
persistido em format_state.py (incrementado a cada uso), não random.

Não mexe no molde "moderno" nem nos posts educativos de fallback — este
módulo só entra em jogo quando o post real escolhido é do molde "clássico".
"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from content import BRT_OFFSET, PostContent, _HEADLINE_LABEL_SENTENCE, _IMPACT_TITLE, _period_of_day

MOLDS = ["moderno", "classico"]


# --- molde: alternância estrita post a post, nunca repete o anterior ------
def next_mold(state: dict) -> str:
    nxt = "classico" if state.get("last_mold", "moderno") != "classico" else "moderno"
    state["last_mold"] = nxt
    return nxt


# --- 1) categoria de imagem de fundo, condicional ao tipo de evento -------
_IMAGE_CATEGORY_BY_KIND = {
    "low_vis": "neblina", "obscured": "neblina", "low_ceiling": "neblina",
    "thunderstorm": "tempestade", "severe_wx": "tempestade", "convective": "tempestade",
    "windshear": "tempestade",
    "rwy_closed": "pista_generica", "twr_closed": "pista_generica",
    "freezing": "pista_generica", "strong_wind": "pista_generica",
    "navaid_us": "pista_generica",
}
# 2-3 palavras-chave por categoria (inglês — ver lição em CLAUDE.md: Pexels
# responde muito melhor em inglês) — giradas ciclicamente (ver pick_image_query),
# nunca a mesma repetida duas vezes seguidas dentro da MESMA categoria.
IMAGE_BANK = {
    "neblina": [
        "foggy airport runway morning",
        "airport control tower fog",
        "misty airplane tarmac",
    ],
    "tempestade": [
        "storm clouds over airport runway",
        "lightning sky airplane tarmac",
        "dark storm clouds aviation",
    ],
    "pista_generica": [
        "empty airport runway asphalt",
        "airport tarmac wide angle",
        "runway asphalt markings aerial",
    ],
}


def pick_image_query(headline_kind: str, state: dict) -> str:
    category = _IMAGE_CATEGORY_BY_KIND.get(headline_kind, "pista_generica")
    bank = IMAGE_BANK[category]
    idx_map = state.setdefault("image_bank_index", {})
    next_idx = (idx_map.get(category, -1) + 1) % len(bank)
    idx_map[category] = next_idx
    return bank[next_idx]


# --- 2) intensidade do vermelho, condicional à gravidade -------------------
# 3 níveis, mesma família de vermelho (paleta da marca) — só variam
# saturação/luminosidade, nunca o matiz: mais escuro/saturado pra crítico,
# mais claro/suave pra impacto menor.
_SEVERITY_TIER_BY_KIND = {
    "rwy_closed": "alta", "twr_closed": "alta", "windshear": "alta",
    "thunderstorm": "media", "severe_wx": "media", "convective": "media",
    "freezing": "media", "obscured": "media", "low_vis": "media",
    "low_ceiling": "media", "strong_wind": "media",
    "navaid_us": "baixa",
}
RED_BY_TIER = {
    "alta": "#C41E0F",    # pista/torre fechada, tesoura de vento — crítico
    "media": "#E9543F",   # clima adverso (o vermelho padrão da marca)
    "baixa": "#F07A68",   # aux. de navegação inativo — impacto mais brando
}


def severity_tier(headline_kind: str) -> str:
    return _SEVERITY_TIER_BY_KIND.get(headline_kind, "media")


# --- 3) selo de categoria no canto (reaproveita o slot de kicker) ---------
_CATEGORY_BADGE = {
    "rwy_closed": "PISTA", "twr_closed": "TORRE",
    "windshear": "VENTO", "strong_wind": "VENTO",
    "thunderstorm": "TEMPESTADE", "convective": "TEMPESTADE",
    "severe_wx": "TEMPO SEVERO", "freezing": "GELO",
    "obscured": "VISIBILIDADE", "low_vis": "VISIBILIDADE", "low_ceiling": "TETO BAIXO",
    "navaid_us": "NOTAM",
}


def category_badge(headline_kind: str) -> str:
    return _CATEGORY_BADGE.get(headline_kind, "AVISO")


# --- 4) quantidade de slides, condicional à riqueza de contexto -----------
_AIRCRAFT_RE = re.compile(r"\b(P[PRSTU]-[A-Z0-9]{3})\b")
_RESPONSE_RE = re.compile(r"\b(SALVAMENTO|BOMBEIR\w*|EMERG\w*|SAR|CB)\b", re.IGNORECASE)
# captura a negação junto ("SEM FERIDOS") quando ela vem logo antes — sem
# isso, "SEM FERIDOS" virava só "Feridos" no slide, informação de segurança
# invertida (lição descoberta testando com o NOTAM real do incidente de
# 2026-08-27 em SBRJ, que trazia exatamente esse texto)
_CASUALTY_RE = re.compile(r"\b((?:SEM\s+)?(?:FERIDOS?|V[ÍI]TIMAS?|[ÓO]BITOS?))\b", re.IGNORECASE)


@dataclass
class EventContext:
    aircraft_id: str | None = None
    casualties_info: str | None = None
    response_action: str | None = None
    duration_text: str | None = None

    def richness(self) -> int:
        return sum(1 for f in (self.aircraft_id, self.casualties_info,
                                self.response_action, self.duration_text) if f)


def extract_event_context(post: PostContent) -> EventContext:
    """Conta quantos campos de contexto estão preenchidos — critério objetivo
    pra decidir o 2º slide (ver wants_explicativo_slide). `duration_text` já
    vem pronto de content.py (validade real do NOTAM); os demais são
    detectados no texto bruto do METAR/NOTAM (post.raw_snippet)."""
    text = post.raw_snippet or ""
    aircraft = _AIRCRAFT_RE.search(text)
    response = _RESPONSE_RE.search(text)
    casualty = _CASUALTY_RE.search(text)
    return EventContext(
        aircraft_id=aircraft.group(1) if aircraft else None,
        casualties_info=casualty.group(0).capitalize() if casualty else None,
        response_action=response.group(0).capitalize() if response else None,
        duration_text=post.duration_text,
    )


def wants_explicativo_slide(ctx: EventContext, threshold: int = 2) -> bool:
    return ctx.richness() >= threshold


# --- horário noturno (composição mais escura) ------------------------------
def is_nighttime(when_dt: datetime) -> bool:
    local = when_dt + BRT_OFFSET
    return _period_of_day(local.hour) in ("noite", "madrugada")


# --- 5) formato da frase-título, sem repetir o anterior --------------------
_TITLE_FORMATS = ["A", "B", "C"]


def next_title_format(state: dict) -> str:
    idx = (state.get("title_format_index", -1) + 1) % len(_TITLE_FORMATS)
    state["title_format_index"] = idx
    return _TITLE_FORMATS[idx]


def title_format_classico(fmt: str, city: str, headline_kind: str, when_dt: datetime) -> str:
    problema_label = _HEADLINE_LABEL_SENTENCE.get(headline_kind, "Aviso ativo")
    problema_lower = problema_label[0].lower() + problema_label[1:]
    consequencia = _IMPACT_TITLE.get(headline_kind, "Seu voo pode ser afetado")
    local = when_dt + BRT_OFFSET
    horario = f"{local.hour:02d}:{local.minute:02d}"
    if fmt == "A":
        return f"{city}: {problema_label}"
    if fmt == "B":
        return f"{consequencia} em {city}"
    return f"Desde {horario}, {problema_lower} em {city}"


# --- 6) abertura da legenda, sem repetir a anterior ------------------------
_CAPTION_OPENINGS = ["pergunta", "fato", "urgencia"]


def next_caption_opening(state: dict) -> str:
    idx = (state.get("caption_opening_index", -1) + 1) % len(_CAPTION_OPENINGS)
    state["caption_opening_index"] = idx
    return _CAPTION_OPENINGS[idx]


def caption_opening(style_name: str, city: str, icao: str, headline_kind: str, when_dt: datetime) -> str:
    headline_sentence = _HEADLINE_LABEL_SENTENCE.get(headline_kind, "Aviso ativo")
    local = when_dt + BRT_OFFSET
    horario = f"{local.hour:02d}:{local.minute:02d}"
    if style_name == "pergunta":
        return f"Sabia que o aeroporto de {city} está com {headline_sentence.lower()} agora?"
    if style_name == "fato":
        return f"Desde as {horario} (Brasília), {headline_sentence.lower()} em {city} ({icao})."
    return f"🚨 Atenção: {headline_sentence} em {city} ({icao})"


def apply_caption_opening(post: PostContent, state: dict) -> str:
    """Troca só a linha de abertura da legenda já montada por content.py
    (mantém bullets, impacto, fonte e hashtags intactos) pela abertura
    rotacionada (ver caption_opening/next_caption_opening)."""
    style_name = next_caption_opening(state)
    when_dt = post.when_dt or datetime.now(timezone.utc)
    new_opening = caption_opening(style_name, post.city, post.icao, post.headline_kind, when_dt)
    old_opening = f"⚠️ {post.headline} em {post.city} ({post.icao})"
    if post.caption.startswith(old_opening):
        return new_opening + post.caption[len(old_opening):]
    return new_opening + "\n\n" + post.caption
