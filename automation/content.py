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

# texto de "o que isso significa" pro slide explicativo — um por headline_kind.
# Ênfase explícita em VOO (o que muda pro passageiro), não só o fato técnico —
# e "desvio" sempre explicado como pousar em pista/aeroporto diferente do
# planejado (pedido do usuário, 2026-08-24 — antes o texto era genérico
# demais, ex.: "chance real de atraso, reprogramação ou desvio").
_IMPACT_TEXT = {
    "rwy_closed": "Se o seu voo usaria essa pista, ele pode atrasar, ser remarcado para outro horário "
        "ou até pousar numa pista ou aeroporto diferente do planejado (desvio) enquanto essa pista "
        "estiver fechada.",
    "twr_closed": "Sem torre de controle ativa, os voos daquele aeroporto podem atrasar ou ficar "
        "temporariamente suspensos até o serviço ser retomado.",
    "windshear": "Na aproximação, o piloto pode precisar arremeter — abortar o pouso e tentar de novo — "
        "ou esperar a condição melhorar antes de tentar pousar; isso atrasa o seu voo, mas é uma "
        "medida de segurança.",
    "thunderstorm": "Voos que passariam perto do aeroporto agora podem esperar no ar, ser desviados de "
        "rota (pousar em outro aeroporto) ou ter a decolagem atrasada por segurança.",
    "severe_wx": "Fenômeno meteorológico severo costuma atrasar a decolagem, fazer o voo esperar no ar "
        "ou até ser desviado para outro aeroporto por segurança.",
    "convective": "Nuvens de tempestade (cumulonimbus) perto do aeroporto costumam atrasar decolagens, "
        "fazer voos esperarem no ar ou até serem desviados para outro aeroporto até a condição melhorar.",
    "freezing": "Antes de decolar, a aeronave e a pista precisam passar por degelo — um processo que "
        "atrasa o seu voo.",
    "low_vis": "Com visibilidade tão baixa, só aeronaves e pilotos habilitados a pousos por instrumento "
        "em condição severa conseguem operar — os demais voos esperam no ar ou são desviados para "
        "outro aeroporto.",
    "obscured": "Com o céu obscurecido dessa forma, só aeronaves e pilotos habilitados a pousos por "
        "instrumento em condição severa conseguem operar — os demais voos esperam no ar ou são "
        "desviados para outro aeroporto.",
    "low_ceiling": "Nuvens muito baixas dificultam a aproximação visual — alguns voos podem atrasar ou "
        "ser desviados para outro aeroporto até o teto subir.",
    "strong_wind": "Vento forte, especialmente com rajadas, pode forçar o piloto a arremeter (tentar o "
        "pouso de novo) ou atrasar o voo até a condição melhorar.",
    "navaid_us": "Sem esse auxílio, os pilotos dependem de outro tipo de aproximação — geralmente mais "
        "exigente — o que aumenta a chance de atraso ou desvio do seu voo em dias de tempo ruim.",
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
    raw_snippet: str           # texto bruto (METAR ou NOTAM) pro card de rodapé; "" oculta o card (ver fallback_content.py)
    heading_1: str = "O QUE ACONTECEU:"      # sobrescrito pelo fallback_content.py (posts educativos)
    heading_2: str = "O QUE ISSO SIGNIFICA:"
    raw_snippet_label: str = "REGISTRO BRUTO (METAR/NOTAM)"
    contexto: str | None = None  # parágrafo de abertura — situa a notícia e cita a fonte (DECEA)


@dataclass
class PostContent:
    icao: str
    city: str
    uf: str
    headline: str            # ex.: "PISTA FECHADA" (rótulo curto, usado em logs/selo)
    headline_kind: str        # ex.: "rwy_closed" — usado por backgrounds.py pra escolher a foto genérica mais pertinente
    severity: str             # "alto", "atenção" ou "informativo" (posts educativos de fallback — ver fallback_content.py)
    bullets: list             # frases naturais, uma por motivo
    updated_label: str        # ex.: "METAR das 18:00 UTC (15:00 em Brasília)"
    caption: str              # texto completo pra legenda do Instagram
    cover_title: str           # título grande do slide CAPA, ex.: "PISTA FECHADA EM CONGONHAS POR MANUTENÇÃO"
    cover_subtitle: str | None  # linha secundária opcional do slide CAPA (horário/duração)
    background_category: str    # "weather" (fundo = satélite) ou uma chave de ilustração (ver _ILLUSTRATION_BY_KIND)
    needs_explicativo: bool      # True quando um único slide de capa não é suficiente
    explicativo: ExplicativoContent | None
    dedup_key: str            # identifica a condição pra automação não postar a mesma coisa 2x (ver state.py)
    kicker_text: str | None = None  # sobrescreve o kicker padrão "{icao} · {uf}" (usado pelo fallback educativo)


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
                        evaluation: AirportEvaluation) -> list:
    """Monta o(s) post(s) a partir do resultado já filtrado pela etapa 2 — um
    aeroporto pode gerar MAIS DE UM post ao mesmo tempo quando há motivos
    distintos e não relacionados (ex.: uma pista fechada e, à parte, uma
    trovoada) — cada notícia relevante tem seu próprio card, em vez de
    misturar tudo num post só (decisão do usuário, 2026-08-23). Retorna lista
    vazia se não houver o que postar (should_post=False)."""
    if not evaluation.should_post:
        return []

    posts = []

    # --- post do clima: todos os motivos de METAR do momento juntos (é UMA
    # situação meteorológica só, não notícias separadas) ---
    if evaluation.metar_reasons:
        fields = parse_metar(metar.raw)
        kinds = [r.kind for r in evaluation.metar_reasons]
        bullets = [_metar_sentence(k, fields) for k in kinds]
        hoje = (datetime.now(timezone.utc) + BRT_OFFSET).strftime("%Y-%m-%d")
        headline_kind = next(k for k in _HEADLINE_PRIORITY if k in kinds)
        dedup_key = f"{icao}|weather|{headline_kind}|{hoje}"
        posts.append(_build_one_post(
            icao, airport, metar, bullets, headline_kind, dedup_key,
            causa=_causa_clause(headline_kind, fields, None),
            cover_subtitle=f"Atualizado {metar_local_time_short(metar)}" if metar else None,
            duracao_prevista="Reavaliado a cada novo boletim METAR (de hora em hora)",
            raw_snippet=metar.raw,
        ))

    # --- um post por NOTAM relevante: cada NOTAM é a sua própria notícia,
    # mesmo que aconteça no mesmo aeroporto e no mesmo momento que outra ---
    for hit in evaluation.notam_hits:
        if not hit.reasons:
            continue
        kinds = [r.kind for r in hit.reasons]
        bullets = []
        for k in kinds:
            sentence = _notam_sentence(k, hit.notam)
            validity = _format_notam_validity(hit.notam)
            if validity and k in ("rwy_closed", "twr_closed"):
                sentence += f" ({validity})"
            bullets.append(sentence)
        headline_kind = next(k for k in _HEADLINE_PRIORITY if k in kinds)
        dedup_key = f"{icao}|notam|{hit.notam.id}"
        posts.append(_build_one_post(
            icao, airport, metar, bullets, headline_kind, dedup_key,
            causa=_causa_clause(headline_kind, None, hit),
            cover_subtitle=_format_notam_validity(hit.notam),
            duracao_prevista=_format_notam_validity(hit.notam),
            raw_snippet=hit.notam.texto,
        ))

    return posts


def _build_one_post(icao, airport, metar, bullets, headline_kind, dedup_key,
                     causa, cover_subtitle, duracao_prevista, raw_snippet) -> PostContent:
    """Monta um único PostContent (um card de notícia) a partir de um grupo de
    motivos que já foi decidido como pertencendo à mesma notícia — ou o grupo de
    condições de METAR do momento, ou um NOTAM específico. Ver build_post_content."""
    headline = _HEADLINE_LABEL[headline_kind]
    severity = "alto" if headline_kind in _HIGH_SEVERITY_KINDS else "atenção"
    updated_label = _metar_updated_label(metar) if metar else "Aviso NOTAM ativo"

    # título de capa: sempre com "Aeroporto de {cidade}" e terminando na
    # consequência prática ("...pode atrasar ou alterar voos") — as duas
    # palavras-chave que geram urgência pra quem vê o post parar pra ler
    # (pedido explícito do usuário, 2026-08-24; exemplo dado: "Aeroporto de
    # Natal: Risco de Tempestade pode atrasar / alterar voos").
    problema = _HEADLINE_LABEL_SENTENCE[headline_kind][0].lower() + _HEADLINE_LABEL_SENTENCE[headline_kind][1:]
    if causa:
        problema += f" {causa}"
    cover_title = f"Aeroporto de {airport['city']}: {problema} pode atrasar ou alterar voos"

    background_category = "weather" if headline_kind in WEATHER_KINDS else _ILLUSTRATION_BY_KIND[headline_kind]

    contexto = (
        f"A AvisoAereo acompanha em tempo real os boletins oficiais do DECEA (REDEMET/AISWEB) "
        f"nos principais aeroportos do Brasil. Agora é a vez do Aeroporto de {airport['city']} ({icao}):"
    )

    explicativo = ExplicativoContent(
        subtitulo=f"{airport['city']} — {icao}",
        o_que_aconteceu=" ".join(bullets),
        o_que_significa=_IMPACT_TEXT.get(headline_kind, ""),
        duracao_prevista=duracao_prevista,
        raw_snippet=raw_snippet,
        contexto=contexto,
    )

    # o "o que isso significa" sempre aparece — na legenda, e também no slide
    # explicativo — pra quem não entende de aviação conseguir dimensionar o
    # impacto prático (não só o jargão técnico dos bullets acima)
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
        needs_explicativo=True,
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
        for post in build_post_content(icao, airport, metar, evaluation):
            print(f"=== {post.headline} — {post.severity.upper()} — {post.city}/{post.uf} ({post.icao}) — {post.dedup_key} ===")
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
