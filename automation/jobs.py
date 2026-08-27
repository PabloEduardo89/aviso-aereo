"""
Vagas reais de aviação — busca ao vivo (não é conteúdo estático) na hora de
gerar o post educativo de carreira (fallback_content.py), via RSS público do
JSfirm.com (gratuito, sem chave, sem autenticação). Pedido do usuário
(2026-08-27): "sempre que possível anunciando vagas de trabalho e/ou
oportunidades reais na área", pros 3 perfis (piloto, mecânico, comissário).

Cobertura hoje: mecânico e comissário confirmados funcionando (categorias
"maintenancerss"/"flightattendantrss" do JSfirm têm vagas reais e recentes).
Não achamos uma categoria de PILOTO que funcionasse nesse mesmo serviço
(testamos vários nomes prováveis de categoria, todos vazios) — por isso
`carreira_piloto`, em fallback_content.py, continua sem vaga ao vivo; tem só
um slide indicando onde procurar (LinkedIn, JSfirm, sites das companhias).
Se algum dia acharmos uma fonte de vagas de piloto que funcione (JSfirm
mesmo, com a categoria certa, ou outro serviço), adicionar aqui em
JOB_FEEDS e declarar `job_categories` no Topic correspondente.

O JSfirm é americano/internacional (vagas em inglês, geralmente fora do
Brasil) — por isso os slides que usam isso enquadram como "oportunidade
internacional", não vaga no Brasil (não achamos, até agora, uma fonte de
vagas de aviação brasileira com feed público e estável pra automatizar —
Tripulantes Brasil, por exemplo, é um site em Next.js sem RSS/API pública
acessível sem login).
"""
import random
import re
from xml.etree import ElementTree

import requests

REQUEST_TIMEOUT = 15

JOB_FEEDS = {
    "mechanic": "https://www.jsfirm.com/integration/rss/maintenancerss",
    "flight_attendant": "https://www.jsfirm.com/integration/rss/flightattendantrss",
}

_COMPANY_RE = re.compile(r"About\s+([A-Z][\w&.,'\- ]{1,60}?)(?:</strong>|<br|\n)", re.I)
# o link de cada vaga do JSfirm traz .../Cidade/Estado/id no final — usa isso
# pra extrair um local legível sem depender de um campo <location> que não existe
_LOCATION_RE = re.compile(r"/([A-Za-z\-]+)/([A-Za-z\-]+)/\d+/?$")


def fetch_real_job(category: str) -> dict | None:
    """Busca 1 vaga real e recente de aviação (ver JOB_FEEDS). Devolve
    {"title", "company", "location", "link"} ou None se a categoria não
    existe, a busca falhar ou não houver nenhuma vaga no feed no momento —
    quem chama trata como "sem vaga real agora" e segue sem esse slide, nunca
    quebra a geração do post por causa disso."""
    url = JOB_FEEDS.get(category)
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
    except (requests.RequestException, ElementTree.ParseError):
        return None

    items = root.findall(".//item")
    if not items:
        return None

    item = random.choice(items[:8])  # entre as mais recentes, pra variar a cada execução
    title = (item.findtext("title") or "").strip() or "Vaga em aviação"
    link = (item.findtext("link") or "").strip()
    description = item.findtext("description") or ""

    company_match = _COMPANY_RE.search(description)
    company = company_match.group(1).strip() if company_match else None

    location = None
    loc_match = _LOCATION_RE.search(link)
    if loc_match:
        city = loc_match.group(1).replace("-", " ")
        state = loc_match.group(2).replace("-", " ")
        location = f"{city}, {state}"

    return {"title": title, "company": company, "location": location, "link": link}
