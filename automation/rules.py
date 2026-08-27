"""
Etapa 2 — regras de "o que vira post".

Decide se um METAR/NOTAM representa impacto real na operação de voos
(pista fechada, visibilidade/teto abaixo de mínimos, vento fora de limite,
fenômeno severo, auxílio de navegação fora de serviço, restrição de espaço
aéreo etc.) — e não apenas uma condição normal, sem consequência prática.

IMPORTANTE sobre os limiares de METAR (visibilidade, teto, vento): os mínimos
operacionais reais variam por aeródromo, pista e categoria de aproximação
(CAT I/II/III, RVR publicado etc.). As constantes abaixo são valores de
referência conservadores (aproximam CAT I/aproximação não-precisão) para
decidir "vale a pena postar" sem precisar de uma base de mínimos por pista —
ajuste-as se depois você tiver os mínimos publicados de cada aeroporto.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fetch_data import MetarResult, NotamItem

# ---- limiares operacionais de referência (ver nota acima) ----
MIN_VISIBILITY_KM = 1.6      # abaixo disso: visibilidade real-baixa, próxima de mínimos de aproximação
MIN_CEILING_FT = 200         # teto (BKN/OVC) abaixo disso: próximo do DH típico de CAT I
STRONG_WIND_KT = 25          # vento médio sustentado a partir daqui já preocupa a maioria das operações
STRONG_GUST_KT = 35          # rajada a partir daqui

# só estes kinds representam risco real de atraso/cancelamento/desvio ("quente") — os
# demais (visibilidade/teto marginal, vento forte mas não severo, auxílio de navegação
# fora do ar) são reais mas geralmente contornáveis ("morno") e, a partir de 2026-08-27
# (pedido do usuário: "não quero mais avisos mornos"), não geram post nenhum — só
# entram na narrativa quando aparecem JUNTO com um motivo quente (ver evaluate_metar/
# evaluate_notam, que já filtram por este conjunto antes de devolver as reasons)
HIGH_SEVERITY_KINDS = {
    "rwy_closed", "twr_closed", "windshear", "thunderstorm", "severe_wx", "freezing", "convective", "obscured",
}

CLOUD_NAMES = {"FEW": "Poucas nuvens", "SCT": "Nuvens esparsas", "BKN": "Nublado", "OVC": "Encoberto"}
WX_PHEN_LABEL = {
    "DZ": "garoa", "RA": "chuva", "SN": "neve", "SG": "grãos de neve", "IC": "cristais de gelo",
    "PL": "grânulos de gelo", "GR": "granizo", "GS": "granizo pequeno", "UP": "precipitação não identificada",
    "BR": "neblina", "FG": "nevoeiro", "FU": "fumaça", "VA": "cinza vulcânica", "DU": "poeira", "SA": "areia",
    "HZ": "neblina seca", "PY": "borrifo", "PO": "redemoinho de poeira/areia", "SQ": "rajada forte (squall)",
    "FC": "tromba d'água/tornado", "SS": "tempestade de areia", "DS": "tempestade de poeira",
}
SEVERE_WX_CODES = {"GR", "FC", "SS", "DS", "SQ"}

_WIND_RE = re.compile(r"^(\d{3}|VRB)(\d{2,3})(G(\d{2,3}))?KT$")
_WIND_VAR_RE = re.compile(r"^(\d{3})V(\d{3})$")
_VIS_RE = re.compile(r"^\d{4}$")
_CLOUD_RE = re.compile(r"^(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?$")
_VV_RE = re.compile(r"^VV(\d{3}|///)$")
_TEMP_RE = re.compile(r"^(M?\d{2})/(M?\d{2})$")
_QNH_RE = re.compile(r"^Q(\d{4})$")
_WX_TOKEN_RE = re.compile(
    r"^(-|\+|VC|RE)?(MI|BC|PR|DR|BL|SH|TS|FZ)?"
    r"((?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS){0,4})$"
)


@dataclass
class WxPhenomenon:
    label: str
    is_thunderstorm: bool
    is_severe: bool
    is_freezing: bool
    has_fog: bool


@dataclass
class CloudLayer:
    kind: str            # FEW/SCT/BKN/OVC
    height_ft: int
    is_convective: bool  # CB ou TCU


@dataclass
class MetarFields:
    raw: str
    wind_kt: int = 0
    gust_kt: int = 0
    visibility_km: float = 10.0
    cloud_layers: list = field(default_factory=list)
    vertical_visibility_ft: int | None = None   # None quando não há grupo VV
    vv_not_measured: bool = False               # VV/// (obscurecido, sem medida)
    phenomena: list = field(default_factory=list)  # list[WxPhenomenon]
    windshear_rwy: str | None = None
    temp_c: float | None = None
    dew_c: float | None = None
    qnh_hpa: int | None = None


def _parse_wx_token(tok: str) -> WxPhenomenon | None:
    m = _WX_TOKEN_RE.match(tok)
    if not m:
        return None
    intensity, descriptor, phen_block = m.groups()
    phen_codes = re.findall("..", phen_block) if phen_block else []
    phen_labels = [WX_PHEN_LABEL[c] for c in phen_codes if c in WX_PHEN_LABEL]
    if not phen_labels and not descriptor:
        return None

    is_recent = intensity == "RE"
    is_thunderstorm = descriptor == "TS" and not is_recent
    is_severe = not is_recent and (
        is_thunderstorm
        or any(c in SEVERE_WX_CODES for c in phen_codes)
        or (intensity == "+" and any(c in ("RA", "SN") for c in phen_codes))
    )
    is_freezing = descriptor == "FZ" and not is_recent
    has_fog = not is_recent and ("BR" in phen_codes or "FG" in phen_codes)
    label = " e ".join(phen_labels) if phen_labels else (descriptor or tok)
    return WxPhenomenon(label=label, is_thunderstorm=is_thunderstorm, is_severe=is_severe,
                         is_freezing=is_freezing, has_fog=has_fog)


def parse_metar(raw: str) -> MetarFields:
    """Extrai os campos relevantes de um texto METAR bruto (ex.: 'METAR SBFL ... =')."""
    clean = raw.replace("=", "").strip()
    tokens = clean.split()
    fields = MetarFields(raw=clean)

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        m = None
        if tok == "WS":
            fields.windshear_rwy = tokens[i + 1] if i + 1 < len(tokens) else "não especificado"
            i += 1
        elif (m := _WIND_RE.match(tok)):
            fields.wind_kt = int(m.group(2))
            fields.gust_kt = int(m.group(4)) if m.group(4) else 0
        elif _WIND_VAR_RE.match(tok):
            pass  # variação de direção do vento — não afeta a decisão de postar
        elif tok == "CAVOK":
            fields.visibility_km = 10.0
        elif _VIS_RE.match(tok) and tok != "0000":
            fields.visibility_km = int(tok) / 1000
        elif tok in ("SKC", "NSC", "CLR"):
            pass
        elif (m := _CLOUD_RE.match(tok)):
            kind, height, suffix = m.group(1), int(m.group(2)) * 100, m.group(3)
            fields.cloud_layers.append(CloudLayer(kind=kind, height_ft=height, is_convective=bool(suffix)))
        elif (m := _VV_RE.match(tok)):
            if m.group(1) == "///":
                fields.vv_not_measured = True
            else:
                fields.vertical_visibility_ft = int(m.group(1)) * 100
        elif (m := _TEMP_RE.match(tok)):
            def to_c(s):
                return -float(s[1:]) if s.startswith("M") else float(s)
            fields.temp_c = to_c(m.group(1))
            fields.dew_c = to_c(m.group(2))
        elif (m := _QNH_RE.match(tok)):
            fields.qnh_hpa = int(m.group(1))
        else:
            wx = _parse_wx_token(tok)
            if wx:
                fields.phenomena.append(wx)
        i += 1

    return fields


@dataclass
class Reason:
    kind: str    # ex.: "low_vis", "strong_wind", "rwy_closed" — usado pra montar o slide (etapa 3)
    text: str    # descrição técnica, usada nos logs/depuração


@dataclass
class Evaluation:
    relevant: bool
    reasons: list  # list[Reason]


def evaluate_metar(fields: MetarFields) -> Evaluation:
    """Aplica os critérios de impacto real de voo sobre os campos já extraídos do METAR."""
    reasons = []

    if fields.visibility_km < MIN_VISIBILITY_KM:
        reasons.append(Reason("low_vis",
            f"visibilidade de {fields.visibility_km:.1f} km, abaixo do mínimo operacional "
            f"de referência ({MIN_VISIBILITY_KM} km)"
        ))

    low_ceilings = [l for l in fields.cloud_layers if l.kind in ("BKN", "OVC") and l.height_ft < MIN_CEILING_FT]
    if low_ceilings:
        lowest = min(l.height_ft for l in low_ceilings)
        reasons.append(Reason("low_ceiling",
            f"teto baixo ({lowest} ft), próximo do mínimo operacional de referência ({MIN_CEILING_FT} ft)"))

    if fields.vv_not_measured:
        reasons.append(Reason("obscured", "céu obscurecido, visibilidade vertical não medida"))
    elif fields.vertical_visibility_ft is not None and fields.vertical_visibility_ft < MIN_CEILING_FT:
        reasons.append(Reason("obscured",
            f"céu obscurecido, visibilidade vertical de {fields.vertical_visibility_ft} ft"))

    if fields.wind_kt >= STRONG_WIND_KT or fields.gust_kt >= STRONG_GUST_KT:
        wind_desc = f"{fields.wind_kt} kt" + (f", rajadas de {fields.gust_kt} kt" if fields.gust_kt else "")
        reasons.append(Reason("strong_wind", f"vento fora do limite operacional de referência ({wind_desc})"))

    if fields.windshear_rwy:
        reasons.append(Reason("windshear",
            f"tesoura de vento (wind shear) reportada — pista {fields.windshear_rwy}"))

    for phen in fields.phenomena:
        if phen.is_thunderstorm:
            reasons.append(Reason("thunderstorm", f"trovoada ({phen.label})"))
        elif phen.is_severe:
            reasons.append(Reason("severe_wx", f"fenômeno meteorológico severo ({phen.label})"))
        elif phen.is_freezing:
            reasons.append(Reason("freezing", f"precipitação congelante ({phen.label}) — risco de formação de gelo"))

    if any(l.is_convective for l in fields.cloud_layers):
        reasons.append(Reason("convective",
            "nuvem convectiva (cumulonimbus/torre de cumulus) — indício de tempestade"))

    return Evaluation(relevant=bool(reasons), reasons=reasons)


# ---- NOTAM: regex sobre o texto do campo E), algumas restritas por categoria ----
# Deliberadamente restrito — o objetivo é "interferência real na operação",
# não qualquer NOTAM administrativo (ex.: minima de procedimento revisada,
# frequência de rádio alterada, taxiway fechada). cats=None = qualquer categoria.
_NAV_AID_RE = re.compile(r"\b(ILS|LOC|GP|VOR/DME|VOR|DME|NDB|PAPI)\b")
_US_RE = re.compile(r"\bU/S\b")

_NOTAM_RULES = [
    (re.compile(r"\bRWY\b.*\bCLSD\b|\bCLSD\b.*\bRWY\b"), None, "rwy_closed", "pista fechada (RWY CLSD)"),
    (re.compile(r"\bTWR\b.*\bCLSD\b|\bCLSD\b.*\bTWR\b"), None, "twr_closed", "torre de controle fechada (TWR CLSD)"),
]


def evaluate_notam(item: NotamItem) -> Evaluation:
    """Aplica os critérios de restrição relevante sobre um NOTAM já parseado.

    Fica de fora, de propósito: taxiway/apron fechado, minima de procedimento
    revisada, frequência de rádio alterada, atividade de drone/paraquedismo —
    tudo isso é rotina operacional que não chega a interferir de forma real
    e perceptível no voo do público em geral.
    """
    text = (item.texto or "").upper()
    reasons = []

    for pattern, cats, kind, label in _NOTAM_RULES:
        if cats is not None and item.categoria not in cats:
            continue
        if pattern.search(text):
            reasons.append(Reason(kind, label))

    if _NAV_AID_RE.search(text) and _US_RE.search(text):
        aid = _NAV_AID_RE.search(text).group(1)
        reasons.append(Reason("navaid_us", f"auxílio de navegação fora de serviço ({aid} U/S)"))

    return Evaluation(relevant=bool(reasons), reasons=reasons)


def _parse_aisweb_datetime(s: str):
    """Converte o formato de data da AISWEB (YYMMDDHHmm, UTC) em datetime; None se vazio/inválido."""
    if not s or len(s) < 10:
        return None
    try:
        return datetime(2000 + int(s[0:2]), int(s[2:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]),
                         tzinfo=timezone.utc)
    except ValueError:
        return None


def is_notam_active(item: NotamItem, now=None) -> bool:
    """Um NOTAM só deve virar post se já estiver em vigor agora — descarta avisos
    futuros (ex.: um SUP AIP que só passa a valer daqui a duas semanas) e avisos
    cuja vigência já encerrou (o endpoint da AISWEB sem filtro de status já devolve
    só os ativos, mas alguns registros trazem datas futuras/passadas mesmo assim)."""
    now = now or datetime.now(timezone.utc)
    valid_from = _parse_aisweb_datetime(item.valid_from)
    if valid_from is not None and now < valid_from:
        return False
    valid_until = _parse_aisweb_datetime(item.valid_until)
    if valid_until is not None and now > valid_until:
        return False
    return True


@dataclass
class NotamHit:
    notam: NotamItem
    reasons: list


@dataclass
class AirportEvaluation:
    icao: str
    should_post: bool
    metar_reasons: list
    notam_hits: list  # list[NotamHit]


def evaluate_airport(icao: str, metar: MetarResult | None, notams: list) -> AirportEvaluation:
    """Só chega aqui (e vira post) quem tem pelo menos 1 motivo em HIGH_SEVERITY_KINDS
    — risco real de atraso/cancelamento/desvio ("quente"). Restrição real mas
    geralmente contornável (visibilidade/teto marginal, vento forte mas não
    severo, auxílio de navegação fora do ar) NÃO vira post sozinha desde
    2026-08-27 (pedido do usuário: "não quero mais avisos mornos") — o filtro
    é aplicado aqui, na origem, pra ninguém rio abaixo (content.py) precisar
    saber lidar com motivo morno nenhum."""
    metar_reasons = []
    if metar is not None:
        metar_reasons = [r for r in evaluate_metar(parse_metar(metar.raw)).reasons if r.kind in HIGH_SEVERITY_KINDS]

    notam_hits = []
    for item in notams:
        if not is_notam_active(item):
            continue
        ev = evaluate_notam(item)
        high_reasons = [r for r in ev.reasons if r.kind in HIGH_SEVERITY_KINDS]
        if high_reasons:
            notam_hits.append(NotamHit(notam=item, reasons=high_reasons))

    return AirportEvaluation(
        icao=icao,
        should_post=bool(metar_reasons) or bool(notam_hits),
        metar_reasons=metar_reasons,
        notam_hits=notam_hits,
    )


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    from airports import AIRPORTS
    from fetch_data import FetchError, fetch_metar, fetch_notam

    any_relevant = False
    for airport in AIRPORTS:
        icao = airport["code"]
        try:
            metar = fetch_metar(icao)
        except FetchError as err:
            print(f"[{icao}] erro ao buscar METAR: {err}")
            metar = None
        try:
            notams = fetch_notam(icao)
        except FetchError as err:
            print(f"[{icao}] erro ao buscar NOTAM: {err}")
            notams = []

        result = evaluate_airport(icao, metar, notams)
        if not result.should_post:
            continue

        any_relevant = True
        print(f"=== {icao} — {airport['city']}/{airport['uf']} — POSTAR ===")
        if metar:
            print(f"  METAR: {metar.raw}")
        for reason in result.metar_reasons:
            print(f"    - {reason.text}")
        for hit in result.notam_hits:
            print(f"  NOTAM {hit.notam.id} ({hit.notam.categoria}): {hit.notam.texto}")
            for reason in hit.reasons:
                print(f"    - {reason.text}")
        print()

    if not any_relevant:
        print("Nenhum aeroporto com impacto real de voo no momento.")
