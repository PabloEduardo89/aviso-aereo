"""
Etapa 3 (parte 1) — tradução do resultado da etapa 2 (rules.py) em português
natural, pronto pra virar slide/legenda de post. Não faz nenhuma chamada de
rede: recebe os dados já buscados (fetch_data) e avaliados (rules).
"""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fetch_data import MetarResult, NotamItem
from rules import AirportEvaluation, MetarFields, parse_metar

BRT_OFFSET = timedelta(hours=-3)  # Brasília não observa horário de verão desde 2019

# ordem de prioridade pra escolher o destaque principal do slide quando há vários motivos
_HEADLINE_PRIORITY = [
    "rwy_closed", "twr_closed", "windshear", "thunderstorm", "severe_wx",
    "freezing", "convective", "obscured", "low_vis", "low_ceiling",
    "strong_wind", "navaid_us",
]
_HEADLINE_LABEL = {
    "rwy_closed": "PISTA FECHADA",
    "twr_closed": "TORRE FECHADA",
    "windshear": "TESOURA DE VENTO",
    "thunderstorm": "TROVOADA",
    "severe_wx": "TEMPO SEVERO",
    "freezing": "CHUVA CONGELANTE",
    "convective": "RISCO DE TEMPESTADE",
    "obscured": "CÉU OBSCURECIDO",
    "low_vis": "VISIBILIDADE BAIXA",
    "low_ceiling": "TETO BAIXO",
    "strong_wind": "VENTO FORTE",
    "navaid_us": "AUXÍLIO DE NAVEGAÇÃO INATIVO",
}
# versão em frase normal do mesmo rótulo — usada no título grande do slide CAPA
# (estilo manchete de jornal); a versão em CAIXA ALTA vira a etiqueta pequena/kicker
_HEADLINE_LABEL_SENTENCE = {
    "rwy_closed": "Pista fechada",
    "twr_closed": "Torre fechada",
    "windshear": "Tesoura de vento",
    "thunderstorm": "Trovoada",
    "severe_wx": "Tempo severo",
    "freezing": "Chuva congelante",
    "convective": "Risco de tempestade",
    "obscured": "Céu obscurecido",
    "low_vis": "Visibilidade baixa",
    "low_ceiling": "Teto baixo",
    "strong_wind": "Vento forte",
    "navaid_us": "Auxílio de navegação inativo",
}
# "alto" = risco de cancelamento/desvio; "atencao" = restrição real mas geralmente contornável
_HIGH_SEVERITY_KINDS = {
    "rwy_closed", "twr_closed", "windshear", "thunderstorm", "severe_wx", "freezing", "convective", "obscured",
}

# kinds cuja causa vem do clima (fundo de capa = satélite) vs. da operação do aeródromo (fundo = ilustração)
WEATHER_KINDS = {
    "low_vis", "low_ceiling", "obscured", "strong_wind", "windshear",
    "thunderstorm", "severe_wx", "freezing", "convective",
}
# ilustração a usar em backgrounds.py pra cada kind não-meteorológico
_ILLUSTRATION_BY_KIND = {
    "rwy_closed": "runway",
    "twr_closed": "tower",
    "navaid_us": "navaid",
}

# texto de "o que isso significa" pro slide explicativo — um por headline_kind
_IMPACT_TEXT = {
    "rwy_closed": "Voos que pousariam ou decolariam por essa pista precisam usar uma pista alternativa "
        "ou aeroportos próximos — há chance real de atraso, reprogramação ou desvio.",
    "twr_closed": "Sem torre de controle ativa, a operação do aeroporto pode ficar mais lenta ou ser "
        "suspensa temporariamente.",
    "windshear": "Mudança brusca de vento perto do solo é um dos riscos mais sérios na aproximação — "
        "pilotos podem arremeter (ir para uma segunda volta) ou esperar a condição melhorar.",
    "thunderstorm": "Trovoada perto do aeroporto costuma causar espera no ar, desvio de rota ou atraso "
        "na decolagem por segurança.",
    "severe_wx": "Fenômeno meteorológico severo costuma causar espera no ar, desvio de rota ou atraso "
        "na decolagem por segurança.",
    "convective": "Nuvens de tempestade (cumulonimbus) perto do aeroporto costumam causar espera no ar, "
        "desvio de rota ou atraso na decolagem por segurança.",
    "freezing": "Chuva congelante exige degelo da aeronave e da pista antes da operação — um processo "
        "que atrasa pousos e decolagens.",
    "low_vis": "Com visibilidade tão baixa, só aeronaves e pilotos habilitados a pousos por instrumento "
        "em condição severa conseguem operar — os demais voos esperam ou desviam.",
    "obscured": "Com o céu obscurecido dessa forma, só aeronaves e pilotos habilitados a pousos por "
        "instrumento em condição severa conseguem operar — os demais voos esperam ou desviam.",
    "low_ceiling": "Nuvens muito baixas dificultam a aproximação visual — pilotos dependem mais dos "
        "instrumentos, e alguns voos podem atrasar ou desviar.",
    "strong_wind": "Vento forte, especialmente com rajadas, pode forçar arremetidas (segunda volta) ou "
        "atrasos até a condição melhorar.",
    "navaid_us": "Sem esse auxílio, pilotos dependem de outro tipo de aproximação — geralmente com "
        "mínimos mais altos — o que pode causar mais atrasos e desvios que o normal em dias de tempo ruim.",
}

_NAV_AID_NAME = {
    "ILS": "O ILS (sistema de pouso por instrumentos)",
    "LOC": "O localizador (LOC) do ILS",
    "GP": "A rampa de descida (glide path) do ILS",
    "VOR/DME": "O VOR/DME",
    "VOR": "O VOR",
    "DME": "O DME",
    "NDB": "O NDB",
    "PAPI": "O PAPI (indicador visual de rampa de descida)",
}
_RWY_RE = re.compile(r"\bRWY\s*(\d{2}[LRC]?(?:/\d{2}[LRC]?)?)")
_NAV_AID_RE = re.compile(r"\b(ILS|LOC|GP|VOR/DME|VOR|DME|NDB|PAPI)\b")


def _fmt_km(km: float) -> str:
    return f"{km:.1f}".replace(".", ",") + " km"


def _metar_sentence(kind: str, fields: MetarFields) -> str:
    if kind == "low_vis":
        return f"Visibilidade de apenas {_fmt_km(fields.visibility_km)} — abaixo do mínimo para pouso e decolagem."
    if kind == "low_ceiling":
        lowest = min(l.height_ft for l in fields.cloud_layers if l.kind in ("BKN", "OVC") and l.height_ft < 200)
        return f"Teto baixo, nuvens carregadas a partir de {lowest} pés — dificulta a aproximação."
    if kind == "obscured":
        if fields.vv_not_measured:
            return "Céu encoberto, sem visibilidade vertical medida — situação de baixíssima visibilidade."
        return f"Céu obscurecido, visibilidade vertical de apenas {fields.vertical_visibility_ft} pés."
    if kind == "strong_wind":
        base = f"Vento de {fields.wind_kt} kt"
        if fields.gust_kt:
            base += f", com rajadas de até {fields.gust_kt} kt"
        return base + " — acima do limite operacional usual para pouso e decolagem."
    if kind == "windshear":
        rwy = fields.windshear_rwy
        onde = f"na pista {rwy}" if rwy and rwy not in ("ALL", "não especificado") else "no aeródromo"
        return f"Tesoura de vento (wind shear) reportada {onde} — risco de mudança brusca de vento na aproximação."
    if kind == "thunderstorm":
        phen = next((p for p in fields.phenomena if p.is_thunderstorm), None)
        extra = f" com {phen.label}" if phen and phen.label and phen.label != "TS" else ""
        return f"Trovoada em andamento{extra} — pode causar atrasos, desvios ou espera no ar."
    if kind == "severe_wx":
        phen = next((p for p in fields.phenomena if p.is_severe), None)
        return f"Fenômeno meteorológico severo: {phen.label if phen else 'condição adversa'}."
    if kind == "freezing":
        phen = next((p for p in fields.phenomena if p.is_freezing), None)
        return f"Precipitação congelante ({phen.label if phen else 'chuva/garoa'}) — risco de formação de gelo nas aeronaves e na pista."
    if kind == "convective":
        return "Nuvens de tempestade (cumulonimbus) sobre o aeródromo — indício de instabilidade."
    return ""


def _notam_sentence(kind: str, item: NotamItem) -> str:
    text = item.texto or ""
    rwy_match = _RWY_RE.search(text.upper())
    rwy = rwy_match.group(1) if rwy_match else None
    motivo = "manutenção" if re.search(r"\bMAINT\b", text, re.I) else \
             "obras" if re.search(r"\bOBRAS\b", text, re.I) else None

    if kind == "rwy_closed":
        base = f"Pista {rwy} fechada" if rwy else "Pista fechada"
        if motivo:
            base += f" para {motivo}"
        return base + "."
    if kind == "twr_closed":
        base = "Torre de controle fechada"
        if motivo:
            base += f" para {motivo}"
        return base + " — pode afetar o serviço de controle de tráfego aéreo."
    if kind == "navaid_us":
        m = _NAV_AID_RE.search(text.upper())
        aid = m.group(1) if m else None
        nome = _NAV_AID_NAME.get(aid, "Um auxílio de navegação")
        onde = f" da pista {rwy}" if rwy else ""
        return f"{nome}{onde} está fora de serviço."
    return ""


def _notam_motivo(text: str) -> str | None:
    if re.search(r"\bMAINT\b", text, re.I):
        return "manutenção"
    if re.search(r"\bOBRAS\b", text, re.I):
        return "obras"
    return None


def _causa_clause(headline_kind: str, fields: MetarFields | None, notam_hit) -> str | None:
    """Frase curta 'por X' pra compor o título de capa — só faz sentido quando acrescenta
    informação que o próprio rótulo do headline ainda não diz (ex.: 'por manutenção',
    'por neblina'). Pra headlines que já SÃO a causa (trovoada, vento forte, teto baixo
    etc.), a causa fica redundante e é deixada de fora."""
    if headline_kind in ("rwy_closed", "twr_closed"):
        motivo = _notam_motivo(notam_hit.notam.texto or "") if notam_hit else None
        return f"por {motivo}" if motivo else None
    if headline_kind == "low_vis":
        has_fog = fields is not None and any(p.has_fog for p in fields.phenomena)
        return "por neblina" if has_fog else None
    return None


def _format_notam_validity(item: NotamItem) -> str | None:
    """'até dd/mm HH:MM (horário de Brasília)' ou 'sem previsão de término', a partir do campo C)."""
    def parse(s):
        if not s or len(s) < 10:
            return None
        try:
            return datetime(2000 + int(s[0:2]), int(s[2:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), tzinfo=timezone.utc)
        except ValueError:
            return None

    until = parse(item.valid_until)
    if until is None:
        return None
    local = until + BRT_OFFSET
    return f"previsão de liberação: {local.day:02d}/{local.month:02d} às {local.hour:02d}:{local.minute:02d} (horário de Brasília)"


@dataclass
class ExplicativoContent:
    subtitulo: str            # aeroporto — ex.: "Confins (Belo Horizonte) — SBCF"
    o_que_aconteceu: str       # prosa corrida juntando os motivos
    o_que_significa: str       # texto de impacto (ver _IMPACT_TEXT)
    duracao_prevista: str | None
    raw_snippet: str           # texto bruto (METAR ou NOTAM) pro card de rodapé


@dataclass
class PostContent:
    icao: str
    city: str
    uf: str
    headline: str            # ex.: "PISTA FECHADA" (rótulo curto, usado em logs/selo)
    headline_kind: str        # ex.: "rwy_closed" — usado por backgrounds.py pra escolher a foto genérica mais pertinente
    severity: str             # "alto" ou "atenção"
    bullets: list             # frases naturais, uma por motivo
    updated_label: str        # ex.: "METAR das 18:00 UTC (15:00 em Brasília)"
    caption: str              # texto completo pra legenda do Instagram
    cover_title: str           # título grande do slide CAPA, ex.: "PISTA FECHADA EM CONGONHAS POR MANUTENÇÃO"
    cover_subtitle: str | None  # linha secundária opcional do slide CAPA (horário/duração)
    background_category: str    # "weather" (fundo = satélite) ou uma chave de ilustração (ver _ILLUSTRATION_BY_KIND)
    needs_explicativo: bool      # True quando um único slide de capa não é suficiente
    explicativo: ExplicativoContent | None
    dedup_key: str            # identifica a condição pra automação não postar a mesma coisa 2x (ver state.py)


def _metar_updated_label(metar: MetarResult) -> str:
    try:
        received = datetime.strptime(metar.received_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return "Boletim mais recente"
    local = received + BRT_OFFSET
    return f"METAR das {received.hour:02d}:{received.minute:02d} UTC ({local.hour:02d}:{local.minute:02d} em Brasília)"


def metar_local_time_short(metar: MetarResult) -> str:
    try:
        received = datetime.strptime(metar.received_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return "recentemente"
    local = received + BRT_OFFSET
    return f"às {local.hour:02d}:{local.minute:02d} (Brasília)"


def build_post_content(icao: str, airport: dict, metar: MetarResult | None,
                        evaluation: AirportEvaluation) -> PostContent | None:
    """Monta o conteúdo do post a partir do resultado já filtrado pela etapa 2.
    Retorna None se não houver o que postar (should_post=False)."""
    if not evaluation.should_post:
        return None

    bullets = []
    kinds_present = []
    source_by_kind = {}  # kind -> MetarFields (motivo METAR) ou NotamHit (motivo NOTAM)
    fields = None

    if evaluation.metar_reasons:
        fields = parse_metar(metar.raw)
        for reason in evaluation.metar_reasons:
            bullets.append(_metar_sentence(reason.kind, fields))
            kinds_present.append(reason.kind)
            source_by_kind[reason.kind] = fields

    for hit in evaluation.notam_hits:
        for reason in hit.reasons:
            sentence = _notam_sentence(reason.kind, hit.notam)
            validity = _format_notam_validity(hit.notam)
            if validity and reason.kind in ("rwy_closed", "twr_closed"):
                sentence += f" ({validity})"
            bullets.append(sentence)
            kinds_present.append(reason.kind)
            source_by_kind[reason.kind] = hit

    headline_kind = next((k for k in _HEADLINE_PRIORITY if k in kinds_present), kinds_present[0])
    headline = _HEADLINE_LABEL[headline_kind]
    severity = "alto" if any(k in _HIGH_SEVERITY_KINDS for k in kinds_present) else "atenção"

    updated_label = _metar_updated_label(metar) if metar else "Aviso NOTAM ativo"

    # --- slide CAPA: título + linha secundária opcional ---
    source = source_by_kind[headline_kind]
    is_notam_headline = headline_kind in _ILLUSTRATION_BY_KIND
    causa = _causa_clause(headline_kind, fields, source if is_notam_headline else None)
    cover_title = f"{_HEADLINE_LABEL_SENTENCE[headline_kind]} em {airport['city']}"
    if causa:
        cover_title += f" {causa}"

    if is_notam_headline:
        cover_subtitle = _format_notam_validity(source.notam)
    else:
        cover_subtitle = f"Atualizado {metar_local_time_short(metar)}" if metar else None

    background_category = "weather" if headline_kind in WEATHER_KINDS else _ILLUSTRATION_BY_KIND[headline_kind]

    # --- dedup_key: identifica a condição pra automação não postar 2x (state.py) ---
    # NOTAM tem id próprio e único — um mesmo NOTAM em vigor por dias não gera post
    # repetido. Clima não tem id, então a chave é por dia (Brasília): uma trovoada
    # que continua no dia seguinte é tratada como um aviso "novo" (atualização diária).
    if is_notam_headline:
        dedup_key = f"{icao}|notam|{source.notam.id}"
    else:
        hoje = (datetime.now(timezone.utc) + BRT_OFFSET).strftime("%Y-%m-%d")
        dedup_key = f"{icao}|weather|{headline_kind}|{hoje}"

    # --- slide EXPLICATIVO: sempre gerado (regra fixa 2026-08-23 — todo post é
    # carrossel de no mínimo 2 slides: capa + explicativo) ---
    needs_explicativo = True
    explicativo = None
    if needs_explicativo:
        duracao = _format_notam_validity(source.notam) if is_notam_headline else None
        if duracao is None and metar:
            duracao = "Reavaliado a cada novo boletim METAR (de hora em hora)"
        if is_notam_headline:
            raw_snippet = source.notam.texto
        else:
            raw_snippet = metar.raw if metar else (evaluation.notam_hits[0].notam.texto if evaluation.notam_hits else "")
        explicativo = ExplicativoContent(
            subtitulo=f"{airport['city']} — {icao}",
            o_que_aconteceu=" ".join(bullets),
            o_que_significa=_IMPACT_TEXT.get(headline_kind, ""),
            duracao_prevista=duracao,
            raw_snippet=raw_snippet,
        )

    # o "o que isso significa" sempre aparece — na legenda, e também no slide
    # explicativo quando ele existe — pra quem não entende de aviação conseguir
    # dimensionar o impacto prático (não só o jargão técnico dos bullets acima)
    impacto = _IMPACT_TEXT.get(headline_kind, "")

    caption_lines = [
        f"⚠️ {headline} em {airport['city']} ({icao})",
        "",
        *[f"• {b}" for b in bullets],
        "",
        f"O que isso significa na prática: {impacto}" if impacto else None,
        "",
        f"{updated_label}.",
        "",
        "Fonte: REDEMET / AISWEB (DECEA). Conteúdo informativo — consulte sempre a companhia aérea "
        "para status do seu voo.",
        "",
        "#AvisoAereo #METAR #NOTAM #Aviação #" + icao,
    ]
    caption_lines = [line for line in caption_lines if line is not None]

    return PostContent(
        icao=icao,
        city=airport["city"],
        uf=airport["uf"],
        headline=headline,
        headline_kind=headline_kind,
        severity=severity,
        bullets=bullets,
        updated_label=updated_label,
        caption="\n".join(caption_lines),
        cover_title=cover_title,
        cover_subtitle=cover_subtitle,
        background_category=background_category,
        needs_explicativo=needs_explicativo,
        explicativo=explicativo,
        dedup_key=dedup_key,
    )


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    from airports import AIRPORTS
    from fetch_data import FetchError, fetch_metar, fetch_notam
    from rules import evaluate_airport

    by_code = {a["code"]: a for a in AIRPORTS}
    for icao, airport in by_code.items():
        try:
            metar = fetch_metar(icao)
        except FetchError:
            metar = None
        try:
            notams = fetch_notam(icao)
        except FetchError:
            notams = []

        evaluation = evaluate_airport(icao, metar, notams)
        post = build_post_content(icao, airport, metar, evaluation)
        if post is None:
            continue

        print(f"=== {post.headline} — {post.severity.upper()} — {post.city}/{post.uf} ({post.icao}) ===")
        print(f"CAPA titulo: {post.cover_title}")
        print(f"CAPA subtitulo: {post.cover_subtitle}")
        print(f"fundo: {post.background_category} | explicativo? {post.needs_explicativo}")
        if post.explicativo:
            e = post.explicativo
            print(f"  [explicativo] {e.subtitulo}")
            print(f"  o que aconteceu: {e.o_que_aconteceu}")
            print(f"  o que significa: {e.o_que_significa}")
            print(f"  duracao prevista: {e.duracao_prevista}")
            print(f"  raw: {e.raw_snippet}")
        print("--- legenda ---")
        print(post.caption)
        print()
