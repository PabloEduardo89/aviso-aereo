"""
Busca de dados reais de METAR (API-REDEMET) e NOTAM (API-AISWEB).

Reaproveita os mesmos endpoints, parâmetros e chaves já validados em
produção no index.html do site (aba "Mapa ao Vivo" > METAR / NOTAM),
só que em Python para uso pela automação de posts.
"""
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

REDEMET_API_KEY = os.getenv("REDEMET_API_KEY")
REDEMET_BASE = "https://api-redemet.decea.mil.br"

AISWEB_API_KEY = os.getenv("AISWEB_API_KEY")
AISWEB_API_PASS = os.getenv("AISWEB_API_PASS")
AISWEB_BASE = "https://aisweb.decea.mil.br/api"

REQUEST_TIMEOUT = 15


@dataclass
class MetarResult:
    icao: str
    raw: str            # texto bruto do METAR, ex.: "METAR SBFL 231800Z ..."
    received_at: str     # timestamp UTC "YYYY-MM-DD HH:MM:SS" como devolvido pela REDEMET


@dataclass
class NotamItem:
    id: str
    tipo: str            # ex.: NOTAMN, NOTAMC
    categoria: str       # ex.: AGA, CNS, NAV, OTR, MET, ATM
    local: str           # ICAO do aeródromo do aviso
    valid_from: str      # bruto AISWEB, formato YYMMDDHHmm (UTC)
    valid_until: str     # idem; vazio quando não há data de término definida
    texto: str           # campo E) do NOTAM, texto original (abreviado, maiúsculo)
    geo_url: str | None


class FetchError(Exception):
    """Erro ao buscar ou interpretar dados da REDEMET/AISWEB."""


def _require_redemet_key():
    if not REDEMET_API_KEY:
        raise FetchError("REDEMET_API_KEY não configurada no .env")


def _require_aisweb_keys():
    if not AISWEB_API_KEY or not AISWEB_API_PASS:
        raise FetchError("AISWEB_API_KEY / AISWEB_API_PASS não configuradas no .env")


def _utc_hour_string(offset_hours: float = 0) -> str:
    d = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    return d.strftime("%Y%m%d%H")


def fetch_metar(icao: str, hours_back: int = 6) -> MetarResult | None:
    """Busca a mensagem METAR mais recente dentro das últimas `hours_back` horas.

    Retorna None se a API responder sem nenhuma mensagem no período (situação
    normal para aeródromos sem estação automática relatando no momento).
    Levanta FetchError em caso de falha de rede/HTTP ou resposta inesperada.
    """
    _require_redemet_key()
    data_fim = _utc_hour_string(0)
    data_ini = _utc_hour_string(-hours_back)
    # api_key vai na URL (não como header) — a API do DECEA rejeita headers
    # custom com 403 API_KEY_MISSING (mesmo comportamento observado no site).
    url = (
        f"{REDEMET_BASE}/mensagens/metar/{icao}"
        f"?data_ini={data_ini}&data_fim={data_fim}&api_key={REDEMET_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as err:
        raise FetchError(f"Falha de rede ao buscar METAR de {icao}: {err}") from err
    except ValueError as err:
        raise FetchError(f"Resposta inválida (não-JSON) da REDEMET para {icao}: {err}") from err

    messages = ((payload.get("data") or {}).get("data")) or []
    if not messages:
        return None

    latest = messages[-1]
    return MetarResult(icao=icao, raw=latest["mens"], received_at=latest["recebimento"])


def fetch_notam(icao: str) -> list[NotamItem]:
    """Busca os NOTAM atualmente ativos (sem filtro de status) para um ICAO.

    Retorna lista vazia se não houver NOTAM ativo. Levanta FetchError em caso
    de falha de rede/HTTP ou XML inválido.
    """
    _require_aisweb_keys()
    url = (
        f"{AISWEB_BASE}/?apiKey={AISWEB_API_KEY}&apiPass={AISWEB_API_PASS}"
        f"&area=notam&icaoCode={icao}"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as err:
        raise FetchError(f"Falha de rede ao buscar NOTAM de {icao}: {err}") from err

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as err:
        raise FetchError(f"XML inválido da AISWEB para {icao}: {err}") from err

    def field(item, tag):
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    items = []
    for item in root.findall("./notam/item"):
        items.append(NotamItem(
            id=field(item, "id"),
            tipo=field(item, "tp"),
            categoria=field(item, "cat"),
            local=field(item, "loc"),
            valid_from=field(item, "b"),
            valid_until=field(item, "c"),
            texto=field(item, "e"),
            geo_url=field(item, "geo_url") or None,
        ))
    return items


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    from airports import AIRPORTS

    for airport in AIRPORTS:
        icao = airport["code"]
        try:
            metar = fetch_metar(icao)
        except FetchError as err:
            print(f"[{icao}] METAR: erro — {err}")
        else:
            print(f"[{icao}] METAR: {metar.raw if metar else '(sem mensagem recente)'}")

        try:
            notams = fetch_notam(icao)
        except FetchError as err:
            print(f"[{icao}] NOTAM: erro — {err}")
        else:
            print(f"[{icao}] NOTAM: {len(notams)} aviso(s) ativo(s)")
        print()
