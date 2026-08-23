"""
Lista de aeroportos cobertos pela automação (METAR/NOTAM).

Mesma lista de capitais/hubs já cadastrada no index.html do site (aba
"Mapa ao Vivo"), para manter a automação e o site falando dos mesmos
aeroportos.
"""

AIRPORTS = [
    {"code": "SBFL", "city": "Florianópolis", "uf": "SC"},
    {"code": "SBGR", "city": "Guarulhos (São Paulo)", "uf": "SP"},
    {"code": "SBRJ", "city": "Santos Dumont (Rio de Janeiro)", "uf": "RJ"},
    {"code": "SBBR", "city": "Brasília", "uf": "DF"},
    {"code": "SBCF", "city": "Confins (Belo Horizonte)", "uf": "MG"},
    {"code": "SBRB", "city": "Rio Branco", "uf": "AC"},
    {"code": "SBMO", "city": "Maceió", "uf": "AL"},
    {"code": "SBMQ", "city": "Macapá", "uf": "AP"},
    {"code": "SBEG", "city": "Manaus", "uf": "AM"},
    {"code": "SBSV", "city": "Salvador", "uf": "BA"},
    {"code": "SBFZ", "city": "Fortaleza", "uf": "CE"},
    {"code": "SBVT", "city": "Vitória", "uf": "ES"},
    {"code": "SBGO", "city": "Goiânia", "uf": "GO"},
    {"code": "SBSL", "city": "São Luís", "uf": "MA"},
    {"code": "SBCY", "city": "Cuiabá", "uf": "MT"},
    {"code": "SBCG", "city": "Campo Grande", "uf": "MS"},
    {"code": "SBBE", "city": "Belém", "uf": "PA"},
    {"code": "SBJP", "city": "João Pessoa", "uf": "PB"},
    {"code": "SBCT", "city": "Curitiba", "uf": "PR"},
    {"code": "SBRF", "city": "Recife", "uf": "PE"},
    {"code": "SBTE", "city": "Teresina", "uf": "PI"},
    {"code": "SBGL", "city": "Galeão (Rio de Janeiro)", "uf": "RJ"},
    {"code": "SBSG", "city": "Natal", "uf": "RN"},
    {"code": "SBPA", "city": "Porto Alegre", "uf": "RS"},
    {"code": "SBPV", "city": "Porto Velho", "uf": "RO"},
    {"code": "SBBV", "city": "Boa Vista", "uf": "RR"},
    {"code": "SBSP", "city": "Congonhas (São Paulo)", "uf": "SP"},
    {"code": "SBAR", "city": "Aracaju", "uf": "SE"},
    {"code": "SBPJ", "city": "Palmas", "uf": "TO"},
    {"code": "SBKP", "city": "Viracopos (Campinas)", "uf": "SP"},
]

AIRPORT_CODES = [a["code"] for a in AIRPORTS]
