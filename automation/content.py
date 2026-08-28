"""
Etapa 3 (parte 1) — tradução do resultado da etapa 2 (rules.py) em português
natural, pronto pra virar slide/legenda de post. Não faz nenhuma chamada de
rede: recebe os dados já buscados (fetch_data) e avaliados (rules).
"""
import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fetch_data import MetarResult, NotamItem
from rules import HIGH_SEVERITY_KINDS, AirportEvaluation, MetarFields, parse_metar

BRT_OFFSET = timedelta(hours=-3)  # Brasília não observa horário de verão desde 2019

# dia da semana + data + período do dia no título de capa dos posts de alerta —
# pedido do usuário (2026-08-27): "Aeroporto de Guarulhos pode ter voos
# cancelados NESTA TARDE DE QUINTA-FEIRA, 27 DE AGOSTO" — o título precisa
# deixar explícito QUANDO a interferência ocorre, não só o quê. Ver _when_phrase.
_WEEKDAY_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]
_MONTH_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _period_of_day(hour: int) -> str:
    if 0 <= hour < 6:
        return "madrugada"
    if 6 <= hour < 12:
        return "manhã"
    if 12 <= hour < 18:
        return "tarde"
    return "noite"


def _clock_phrase(local: datetime) -> str:
    """'19h' / '19h45' — horário de Brasília, sem zero à esquerda na hora."""
    return f"{local.hour}h{local.minute:02d}" if local.minute else f"{local.hour}h"


def _when_phrase(dt_utc: datetime, now: datetime | None = None) -> str:
    """Frase de QUANDO pro título de capa, escolhida pelo caráter do evento:

    - **evento que ainda vai COMEÇAR** (NOTAM com início de vigência no futuro):
      a hora é a informação mais útil → 'a partir das 19h desta noite de sexta-feira'
      (prospecção — o leitor precisa saber a que horas se preparar).
    - **condição já em curso / leitura ao vivo** (METAR agora, NOTAM já ativo):
      tom de "isto está acontecendo" → 'nesta tarde de quinta-feira, 28 de agosto'
      (o período do dia basta; a hora exata muda a cada boletim e não ajuda).

    `dt_utc` e `now` em UTC; converte pra Brasília antes de calcular dia/período,
    porque é a partir daí que o dia vira pro público-alvo do post."""
    local = dt_utc + BRT_OFFSET
    period = _period_of_day(local.hour)
    weekday = _WEEKDAY_PT[local.weekday()]
    now = now or datetime.now(timezone.utc)
    if dt_utc > now + timedelta(minutes=20):   # margem: só conta como "futuro" se de fato mais pra frente
        # weekday (não período) pra não induzir erro quando o NOTAM começa daqui
        # a dias; a hora já dá o "quando" fino
        return f"a partir das {_clock_phrase(local)} de {weekday}"
    month = _MONTH_PT[local.month - 1]
    return f"nesta {period} de {weekday}, {local.day} de {month}"


def _when_phrase_short(dt_utc: datetime, now: datetime | None = None) -> str:
    """Versão curta de `_when_phrase` pros títulos que já carregam a consequência
    em CAIXA ALTA (longos): só 'nesta tarde' / 'a partir das 22h', sem dia da
    semana nem data — senão o título estoura as 2 linhas do slide."""
    local = dt_utc + BRT_OFFSET
    now = now or datetime.now(timezone.utc)
    if dt_utc > now + timedelta(minutes=20):
        return f"a partir das {_clock_phrase(local)}"
    return f"nesta {_period_of_day(local.hour)}"

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

# versão CURTA do mesmo impacto acima — vira o título do 2º slide do carrossel (a
# legenda continua usando o texto completo de _IMPACT_TEXT). Regra do usuário
# (2026-08-27): "pouca escrita" nos slides — título de até 2 linhas, não parágrafo.
_IMPACT_TITLE = {
    "rwy_closed": "Seu voo pode atrasar, remarcar ou desviar",
    "twr_closed": "Voos podem atrasar ou ficar suspensos",
    "windshear": "Piloto pode precisar arremeter e tentar de novo",
    "thunderstorm": "Voos podem esperar no ar ou ser desviados",
    "severe_wx": "Decolagem pode atrasar ou o voo desviar",
    "convective": "Risco real de atraso, espera no ar ou desvio",
    "freezing": "Degelo da aeronave atrasa o seu embarque",
    "low_vis": "Só pousos por instrumento avançado funcionam agora",
    "obscured": "Só pousos por instrumento avançado funcionam agora",
    "low_ceiling": "Aproximação visual fica mais difícil",
    "strong_wind": "Piloto pode arremeter ou o voo atrasar",
    "navaid_us": "Aproximação fica mais exigente — mais chance de atraso",
}

# palavra-chave (em INGLÊS — o Pexels responde muito melhor a buscas em inglês
# do que em português, testado empiricamente em 2026-08-27: a mesma consulta em
# português ocasionalmente traz foto sem nenhuma relação com o tema) pra buscar
# a foto do 2º slide (impacto) no Pexels — reforça visualmente o que aquele
# headline_kind representa (ver slide.py/backgrounds.py)
_IMPACT_IMAGE_QUERY = {
    "rwy_closed": "closed runway airport",
    "twr_closed": "airport control tower",
    "windshear": "storm strong wind airplane",
    "thunderstorm": "thunderstorm lightning",
    "severe_wx": "severe weather heavy rain",
    "convective": "dark storm clouds",
    "freezing": "ice frost winter",
    "low_vis": "fog mist road",
    "obscured": "dense fog city",
    "low_ceiling": "low clouds gray sky",
    "strong_wind": "strong wind tree",
    "navaid_us": "radar antenna technology",
}
# palavra-chave (inglês) pra buscar a foto do 3º slide (previsão/duração), quando existe
_DURATION_IMAGE_QUERY = "clock waiting airport"

# títulos de capa variados — "aeroporto", "atraso", "cancelamento" etc. são
# EXEMPLOS de palavra-chave, não uma regra fixa por post (pedido do usuário,
# 2026-08-24, depois de notar um "título padrão" repetido demais no feed). Um
# template é sorteado por post; "aeroporto" aparece em parte deles (pode ser
# mais frequente que as outras palavras-chave), mas não em todos. Ver
# `_pick_cover_title`.
#
# Encurtados em 2026-08-27 (regra "pouca escrita" nos slides — antes eram
# frases longas o bastante pra estourar as 2 linhas do novo slide enxuto,
# mesmo no menor tamanho de fonte aceito por _fit_title) e, na mesma data
# (2ª passada), com {when} acrescentado — dia da semana, data e período do
# dia por extenso, sempre presentes (ver _when_phrase), pedido explícito do
# usuário depois de ver o título sem nenhuma indicação de QUANDO a
# interferência ocorre.
# Alguns templates trazem {consequencia_caps} — 1-2 palavras em CAIXA ALTA que
# nomeiam o impacto prático ("ATRASOS e CANCELAMENTOS") pra fisgar o leitor.
# Não entra em TODO post: `_pick_cover_title` só libera esses templates pros
# eventos de maior disrupção (`_LOUD_TITLE_KINDS`) — pista/torre fechada,
# tesoura de vento, trovoada/severo/convectivo. Alerta real porém menos
# disruptivo (vento forte, visibilidade/teto, congelante) fica só com os
# templates sóbrios, sem caixa alta gritada — evita o feed inteiro parecer
# manchete sensacionalista (a mesma preocupação de "título padrão repetido"
# que motivou a variação de templates em 2026-08-24).
_TITLE_TEMPLATES = {
    "alto": [
        # --- sóbrios (qualquer evento) — usam o {when} completo (dia + data + período) ---
        "{Problema} em {city} {when}",
        "{city}: {problema} {when}",
        "Alerta em {city} {when} — {problema}",
        "{Problema} pode afetar voos em {city} {when}",
        "Vai voar para {city} {when}? {Problema}",
        "{city} sob {problema} {when}",
        "Passageiros de {city}: {problema} {when}",
        # --- consequência em CAIXA ALTA (só pros eventos de maior disrupção) ---
        # usam {when_short} ('nesta tarde' / 'a partir das 22h') — sem isso o
        # título estoura 2 linhas mesmo na menor fonte (testado com as cidades
        # de nome mais longo, ex.: "Santos Dumont (Rio de Janeiro)")
        "Aeroporto de {city} pode ter {consequencia_caps} {when_short}",
        "{city}, {when_short}: risco de {consequencia_caps}",
        "{consequencia_caps} em {city} {when_short}",
        "{city} pode ter {consequencia_caps} {when_short}",
    ],
    "atenção": [
        "Aeroporto de {city}: {problema} pode atrasar ou alterar voos",
        "{Problema} em {city} pode atrasar seu voo",
        "Voos para {city} podem atrasar: {problema}",
        "Fique de olho: {problema} afeta o aeroporto de {city}",
        "{city}: {problema} pode mudar o horário do seu voo",
        "Aeroporto de {city} sob {problema} — possível atraso nos voos",
        "Passageiro de {city}, atenção: {problema} pode alterar seu voo",
    ],
}

# impacto prático em 1-2 palavras MAIÚSCULAS, por headline_kind — preenche
# {consequencia_caps} nos templates que têm o slot
_CONSEQUENCE_CAPS = {
    "rwy_closed": "ATRASOS e CANCELAMENTOS",
    "twr_closed": "ATRASOS e CANCELAMENTOS",
    "windshear": "ATRASOS e ARREMETIDAS",
    "thunderstorm": "ATRASOS e DESVIOS",
    "severe_wx": "ATRASOS e DESVIOS",
    "convective": "ATRASOS e DESVIOS",
    "freezing": "ATRASOS NO EMBARQUE",
    "strong_wind": "ATRASOS e ARREMETIDAS",
    "low_vis": "ATRASOS e DESVIOS",
    "obscured": "ATRASOS e DESVIOS",
    "low_ceiling": "ATRASOS e DESVIOS",
    "navaid_us": "ATRASOS",
}
# eventos que justificam o título mais alarmista (consequência em CAIXA ALTA) —
# os de maior chance real de cancelamento/desvio
_LOUD_TITLE_KINDS = {
    "rwy_closed", "twr_closed", "windshear", "thunderstorm", "severe_wx", "convective",
}


def _pick_cover_title(city: str, problema: str, severity: str, headline_kind: str,
                       when_dt: datetime, now: datetime | None = None) -> str:
    templates = _TITLE_TEMPLATES[severity]
    if headline_kind not in _LOUD_TITLE_KINDS:
        # evento real mas menos disruptivo: só os templates sóbrios
        templates = [t for t in templates if "{consequencia_caps}" not in t]
    template = random.choice(templates)
    problema_cap = problema[0].upper() + problema[1:]
    return template.format(
        city=city, problema=problema, Problema=problema_cap,
        when=_when_phrase(when_dt, now), when_short=_when_phrase_short(when_dt, now),
        consequencia_caps=_CONSEQUENCE_CAPS.get(headline_kind, "ATRASOS"),
    )


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


def _parse_notam_field(s: str | None) -> datetime | None:
    """Converte um campo B)/C) da AISWEB (YYMMDDHHmm, UTC) num datetime; None se vazio/inválido."""
    if not s or len(s) < 10:
        return None
    try:
        return datetime(2000 + int(s[0:2]), int(s[2:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), tzinfo=timezone.utc)
    except ValueError:
        return None


def _format_notam_validity(item: NotamItem) -> str | None:
    """'até dd/mm HH:MM (horário de Brasília)' ou 'sem previsão de término', a partir do campo C)."""
    until = _parse_notam_field(item.valid_until)
    if until is None:
        return None
    local = until + BRT_OFFSET
    return f"previsão de liberação: {local.day:02d}/{local.month:02d} às {local.hour:02d}:{local.minute:02d} (horário de Brasília)"


def _notam_when_dt(item: NotamItem, now: datetime) -> datetime:
    """Data/hora que deve aparecer no título de capa (ver _when_phrase): o
    início da vigência (campo B), quando esse início ainda está no futuro —
    um aviso pra algo que vai COMEÇAR; senão "agora", já que o aviso já está
    em vigor no momento em que o post sai."""
    valid_from = _parse_notam_field(item.valid_from)
    if valid_from is not None and valid_from > now:
        return valid_from
    return now


@dataclass
class SlideSpec:
    """Conteúdo de UM slide do carrossel — todo slide segue o mesmo molde visual
    (foto + degradê + kicker + título curto, ver slide.render_photo_slide), desde
    a mudança de 2026-08-27 que aboliu o layout separado de "explicativo" (fundo
    branco/serifado)."""
    kicker_text: str          # etiqueta curta acima do título (categoria/contexto)
    title: str                 # texto curto do slide — regra "pouca escrita": no máximo 2 linhas
    subtitle: str | None = None      # linha secundária opcional (dado complementar curto)
    image_query: str | None = None   # None = usa o fundo "oficial" do post (foto curada do aeroporto/
    # satélite/ilustração — reservado pro 1º slide); uma string busca uma foto REAL no Pexels por essa
    # palavra-chave — cada slide usa a palavra-chave que combina com o QUE ELE DIZ, nunca repete a
    # mesma foto de outro slide do mesmo carrossel (regra do usuário, 2026-08-27)


@dataclass
class PostContent:
    icao: str
    city: str
    uf: str
    headline: str            # ex.: "PISTA FECHADA" (rótulo curto, usado em logs/selo)
    headline_kind: str        # ex.: "rwy_closed" — usado por backgrounds.py pra escolher a foto genérica mais pertinente
    severity: str             # "alto" ou "informativo" (posts educativos de fallback — ver fallback_content.py).
    # "atenção" não é mais alcançável em post real desde 2026-08-27: rules.py só deixa passar reasons de
    # HIGH_SEVERITY_KINDS (só avisos "quentes", nunca mais "mornos" — pedido explícito do usuário).
    caption: str              # texto completo pra legenda do Instagram (mantém o detalhe técnico/impacto
    # completo, mesmo os slides sendo enxutos — quem quiser o "porquê" completo lê a legenda)
    slides: list              # list[SlideSpec] — conteúdo de CADA slide de verdade do carrossel, sem contar
    # o slide de Call-to-Action final, que slide.render_post_slides sempre acrescenta por conta própria
    background_category: str    # fundo do slide[0] — "weather" (satélite) ou uma chave de ilustração
    # (ver _ILLUSTRATION_BY_KIND); só usado quando slides[0].image_query é None
    dedup_key: str            # identifica a condição pra automação não postar a mesma coisa 2x (ver state.py)
    # campos abaixo existem só pro molde alternativo "clássico" (ver style.py) —
    # o molde único fotográfico ("moderno", slide.render_post_slides) não usa nenhum deles.
    when_dt: datetime | None = None      # momento da condição (quando começou/está em vigor) em UTC
    duration_text: str | None = None     # validade formatada do NOTAM, quando há data real de término (senão None)
    raw_snippet: str | None = None       # texto bruto do METAR/NOTAM de origem — usado pra detectar aeronave/resposta/vítimas


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
    now = datetime.now(timezone.utc)

    # --- post do clima: todos os motivos de METAR do momento juntos (é UMA
    # situação meteorológica só, não notícias separadas) ---
    if evaluation.metar_reasons:
        fields = parse_metar(metar.raw)
        kinds = [r.kind for r in evaluation.metar_reasons]
        bullets = [_metar_sentence(k, fields) for k in kinds]
        hoje = (now + BRT_OFFSET).strftime("%Y-%m-%d")
        headline_kind = next(k for k in _HEADLINE_PRIORITY if k in kinds)
        dedup_key = f"{icao}|weather|{headline_kind}|{hoje}"
        posts.append(_build_one_post(
            icao, airport, metar, bullets, headline_kind, dedup_key,
            causa=_causa_clause(headline_kind, fields, None),
            cover_subtitle=f"Atualizado {metar_local_time_short(metar)}" if metar else None,
            # o METAR é reavaliado a cada boletim (de hora em hora) — não tem uma
            # data de término fixa como um NOTAM, então não vira slide de previsão
            duracao_slide=None,
            updated_label_override=None,
            raw_snippet=metar.raw,
            when_dt=now,  # condição meteorológica é sempre "agora" — não tem início futuro
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
            duracao_slide=_format_notam_validity(hit.notam),
            updated_label_override="Aviso NOTAM ativo",
            raw_snippet=hit.notam.texto,
            when_dt=_notam_when_dt(hit.notam, now),  # início da vigência, se ainda no futuro; senão "agora"
        ))

    return posts


def _build_one_post(icao, airport, metar, bullets, headline_kind, dedup_key,
                     causa, cover_subtitle, duracao_slide, updated_label_override, raw_snippet,
                     when_dt) -> PostContent:
    """Monta um único PostContent (um card de notícia) a partir de um grupo de
    motivos que já foi decidido como pertencendo à mesma notícia — ou o grupo de
    condições de METAR do momento, ou um NOTAM específico. Ver build_post_content.

    Desde 2026-08-27 (pedido do usuário), o carrossel não tem mais um slide
    "explicativo" de layout diferente — são 2 ou 3 slides curtos, todos no
    mesmo molde CAPA: (1) manchete, (2) o que isso significa na prática, e (3)
    previsão/duração, só quando há uma data real de término (NOTAM com campo
    C preenchido) — o METAR não tem essa data, então fica só com 2 slides.

    `when_dt` (UTC) é o momento que aparece no título — "nesta tarde de
    quinta-feira, 27 de agosto" — pedido do usuário (2ª passada no mesmo dia):
    o título precisa deixar explícito QUANDO a interferência ocorre, não só
    o quê (ver _when_phrase e build_post_content, que decide esse datetime:
    "agora" pra METAR, início da vigência futura ou "agora" pra NOTAM)."""
    headline = _HEADLINE_LABEL[headline_kind]
    severity = "alto" if headline_kind in HIGH_SEVERITY_KINDS else "atenção"
    updated_label = updated_label_override or (_metar_updated_label(metar) if metar else "Aviso NOTAM ativo")

    # título de capa: sorteado entre vários formatos (ver _TITLE_TEMPLATES) pra
    # não repetir sempre a mesma estrutura — só a consequência prática
    # (atraso/cancelamento/alteração de voo), a cidade e o QUANDO são
    # garantidos; a palavra "aeroporto" aparece em parte dos templates, não em
    # todos (pedido explícito do usuário, 2026-08-24, depois de notar um
    # "título padrão" repetido demais no feed real).
    problema = _HEADLINE_LABEL_SENTENCE[headline_kind][0].lower() + _HEADLINE_LABEL_SENTENCE[headline_kind][1:]
    if causa:
        problema += f" {causa}"
    cover_title = _pick_cover_title(airport['city'], problema, severity, headline_kind, when_dt)

    background_category = "weather" if headline_kind in WEATHER_KINDS else _ILLUSTRATION_BY_KIND[headline_kind]

    slides = [
        SlideSpec(
            kicker_text=f"{icao} · {airport['uf']}",
            title=cover_title,
            subtitle=cover_subtitle,
            image_query=None,  # usa o fundo "oficial" do post — foto curada do aeroporto/satélite/ilustração
        ),
        SlideSpec(
            kicker_text="O QUE ISSO SIGNIFICA",
            title=_IMPACT_TITLE.get(headline_kind, "Seu voo pode ser afetado"),
            image_query=_IMPACT_IMAGE_QUERY.get(headline_kind, "aeroporto avião pista"),
        ),
    ]
    if duracao_slide:
        slides.append(SlideSpec(
            kicker_text="PREVISÃO",
            title=duracao_slide[0].upper() + duracao_slide[1:],
            image_query=_DURATION_IMAGE_QUERY,
        ))

    # a legenda continua trazendo o detalhe técnico completo (bullets + impacto
    # por extenso) — os slides ficam enxutos, mas quem quiser o "porquê" lê a
    # legenda (regra "sempre explicar o impacto prático" segue valendo, só que
    # agora prioritariamente na legenda em vez de num slide de texto corrido)
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
        caption="\n".join(caption_lines),
        slides=slides,
        background_category=background_category,
        dedup_key=dedup_key,
        when_dt=when_dt,
        duration_text=duracao_slide,
        raw_snippet=raw_snippet,
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
            print(f"fundo do 1º slide: {post.background_category}")
            for i, s in enumerate(post.slides, start=1):
                print(f"  slide {i}: [{s.kicker_text}] {s.title}"
                      f"{' | ' + s.subtitle if s.subtitle else ''}"
                      f" (foto: {s.image_query or 'oficial do post'})")
            print("--- legenda ---")
            print(post.caption)
            print()
