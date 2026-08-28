"""
Busca de fotos REAIS de notícia pro slide de capa, quando o evento é
genuinamente noticioso (ver style.wants_real_news_photo) — pedido do
usuário, 2026-08-28: "sempre imagens reais da notícia... sempre que
aplicável... senão use pexels/fontes que já estão sendo usadas hoje".

**Por que não usa Google News / Bing News (RSS de resultado de busca)**:
testado e descartado — os dois trazem, no próprio feed, uma cláusula de
copyright que PROÍBE EXPLICITAMENTE uso fora de "um leitor de RSS pessoal,
não comercial" ("qualquer outro uso exige permissão por escrito" — Google e
Microsoft, respectivamente). Como @avisoaereo é uma conta comercial, usar
esses feeds violaria os termos do próprio agregador. Em vez disso, este
módulo lê os feeds RSS OFICIAIS de veículos brasileiros (G1, CNN Brasil) —
publicados pelos próprios veículos pra sindicação de manchetes, sem essa
restrição — filtra por palavra-chave + janela de tempo recente, e extrai a
foto de capa do artigo (meta `og:image`).

Continua existindo o risco de direito autoral sobre a FOTO em si (pertence
ao veículo de imprensa) — o mesmo risco já discutido e aceito explicitamente
pelo usuário pro carrossel manual do incidente de SBRJ (2026-08-27). Este
módulo só evita infringir os TERMOS DO FEED AGREGADOR, que é um problema
separado e adicional que apareceria em qualquer post automático que usasse
Google/Bing News RSS.

Se nada bater (feed fora do ar, sem item recente com as palavras-chave, ou
sem og:image extraível/grande o bastante), devolve None — quem chama cai
pro pipeline de sempre (Pexels / foto curada / satélite / ilustração), sem
quebrar a geração do post.
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from xml.etree import ElementTree

import requests
from PIL import Image

from backgrounds import cover_resize
from fetch_data import REQUEST_TIMEOUT

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AvisoAereoBot/1.0)"}

# feeds RSS OFICIAIS de veículos brasileiros (não agregadores de busca) —
# publicados pelos próprios veículos pra sindicação das próprias manchetes.
NEWS_FEEDS = [
    "https://g1.globo.com/rss/g1/",
    "https://www.cnnbrasil.com.br/feed/",
]

MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 300

_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _matches(text: str, anchor_terms: list, topic_terms: list) -> bool:
    """`anchor_terms` — basta UM bater (ex.: "Santos Dumont" OU "Rio de
    Janeiro" — o nome do aeroporto e o nome da cidade raramente aparecem
    juntos, literalmente, na mesma manchete). `topic_terms` — basta UM
    também (termos genéricos de aviação)."""
    norm = _normalize(text)
    if anchor_terms and not any(_normalize(kw) in norm for kw in anchor_terms):
        return False
    if topic_terms and not any(_normalize(kw) in norm for kw in topic_terms):
        return False
    return True


def _parse_pubdate(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_og_image(article_url: str) -> str | None:
    resp = requests.get(article_url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
    resp.raise_for_status()
    match = _OG_IMAGE_RE.search(resp.text)
    if not match:
        return None
    return match.group(1).replace("&amp;", "&")


def _download_image(image_url: str):
    resp = requests.get(image_url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    if img.width < MIN_IMAGE_WIDTH or img.height < MIN_IMAGE_HEIGHT:
        return None
    return img


def search_news_photo(anchor_terms: list, topic_terms: list, when_dt: datetime,
                       max_age_hours: int = 18) -> tuple | None:
    """`anchor_terms` (nome do aeroporto/cidade) e `topic_terms` (termos
    genéricos de aviação) — basta UM de cada grupo aparecer no
    título+descrição do item (ver _matches), casamento simples, sem acento,
    case-insensitive. Só olha itens publicados dentro de `max_age_hours` de
    `when_dt`. Devolve (imagem já cortada pro slide, crédito, url_do_artigo)
    do primeiro item que bater e tiver uma foto extraível grande o
    bastante; None se nada servir."""
    cutoff = when_dt - timedelta(hours=max_age_hours)
    for feed_url in NEWS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
            resp.raise_for_status()
            root = ElementTree.fromstring(resp.content)
        except (requests.RequestException, ElementTree.ParseError):
            continue

        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            description = item.findtext("description") or ""
            pub_dt = _parse_pubdate(item.findtext("pubDate"))
            if pub_dt is not None and pub_dt < cutoff:
                continue
            if not _matches(f"{title} {description}", anchor_terms, topic_terms):
                continue
            link = item.findtext("link")
            if not link:
                continue
            try:
                image_url = _extract_og_image(link)
                if not image_url:
                    continue
                img = _download_image(image_url)
                if img is None:
                    continue
            except requests.RequestException:
                continue

            domain = link.split("/")[2].replace("www.", "")
            return cover_resize(img), f"Reprodução/{domain}", link

    return None
