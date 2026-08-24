"""
Conteúdo educativo de fallback — carrossel curto que run_cycle.py publica só
quando NÃO há nenhum aviso real ativo em nenhum aeroporto monitorado E já faz
tempo (MIN_FALLBACK_INTERVAL_SECONDS) desde o último post, pra conta nunca
ficar muda por muitas horas seguidas mesmo em dias calmos.

Não é uma notícia/alerta — é conteúdo educativo rotativo sobre regras, códigos
e curiosidades da aviação (aprovado pelo usuário em 2026-08-23), com visual
propositalmente diferente (azul, severity="informativo" — ver slide.py) do
vermelho/âmbar dos alertas reais, pra nunca ser confundido com um aviso de
verdade.

Os tópicos giram em ordem fixa (ver `fallback_topic_index` em state.py via
get_meta/set_meta), passando por todos antes de repetir qualquer um.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from content import ExplicativoContent, PostContent


@dataclass
class Topic:
    slug: str            # identificador único, usado no dedup_key
    kind: str             # chave de categoria educativa — ver _GENERIC_CATEGORY_BY_KIND em backgrounds.py
    kicker_text: str
    cover_title: str
    heading_1: str
    body_1: str
    heading_2: str
    body_2: str
    hashtags: str
    raw_snippet: str = ""
    raw_snippet_label: str = "EXEMPLO REAL"


TOPICS = [
    # --- regras, leis e regulamentos da aviação (geral e comercial) ---
    Topic(
        slug="direitos_passageiro", kind="edu_rules", kicker_text="VOCÊ SABIA?",
        cover_title="Seu voo atrasou? Veja o que a lei garante",
        heading_1="A REGRA:",
        body_1="Pela Resolução 400 da ANAC, atraso de mais de 4 horas ou cancelamento dá direito a "
               "reacomodação em outro voo, reembolso integral ou execução do serviço por outra "
               "modalidade de transporte, à escolha do passageiro.",
        heading_2="NA PRÁTICA:",
        body_2="A companhia também deve oferecer assistência material — como comunicação, alimentação "
               "e, se necessário, hospedagem — proporcional ao tempo de espera, mesmo antes de "
               "completar as 4 horas.",
        hashtags="#AvisoAereo #DireitosDoPassageiro #ANAC #Aviação",
    ),
    Topic(
        slug="overbooking", kind="edu_rules", kicker_text="VOCÊ SABIA?",
        cover_title="Por que companhias vendem mais passagens do que assentos",
        heading_1="O QUE É:",
        body_1="Overbooking é a prática, autorizada pela ANAC, de vender mais bilhetes do que assentos "
               "disponíveis — as companhias apostam que uma parte dos passageiros não vai comparecer "
               "ao voo.",
        heading_2="SE DER ERRADO:",
        body_2="Quando todos comparecem e sobra gente, a empresa deve primeiro pedir voluntários (com "
               "compensação) antes de recusar embarque à força — quem é preterido sem querer tem "
               "direito a indenização, reacomodação e assistência.",
        hashtags="#AvisoAereo #Overbooking #ANAC #Aviação",
    ),
    Topic(
        slug="bagagem", kind="edu_rules", kicker_text="VOCÊ SABIA?",
        cover_title="Quanta bagagem você tem direito de graça no voo doméstico",
        heading_1="A REGRA:",
        body_1="Em voos domésticos no Brasil, toda passagem aérea dá direito a pelo menos uma bagagem "
               "despachada gratuita, com peso mínimo de 23 kg — independente da tarifa ou da promoção.",
        heading_2="ATENÇÃO:",
        body_2="Isso vale só pra bagagem despachada; a bagagem de mão tem limite próprio de peso e "
               "dimensão, que varia um pouco de companhia pra companhia.",
        hashtags="#AvisoAereo #Bagagem #ANAC #Aviação",
    ),
    # --- significado dos códigos de aeroporto ---
    Topic(
        slug="iata_icao", kind="edu_codes", kicker_text="CURIOSIDADE",
        cover_title="IATA ou ICAO? Os dois códigos de todo aeroporto",
        heading_1="A DIFERENÇA:",
        body_1="Todo aeroporto tem dois códigos: o IATA, de 3 letras (o que aparece na etiqueta da sua "
               "mala e na passagem, como GRU para Guarulhos), e o ICAO, de 4 letras, usado tecnicamente "
               "pelo controle de tráfego aéreo e nos boletins METAR/NOTAM (como SBGR, também Guarulhos).",
        heading_2="POR QUE EXISTEM DOIS:",
        body_2="O IATA é voltado pro público e pro comércio (bilhetes, malas), enquanto o ICAO segue um "
               "padrão internacional mais rígido, com a primeira letra indicando a região do mundo — no "
               "Brasil, quase todos começam com 'SB'.",
        raw_snippet="GRU (IATA) = SBGR (ICAO) — Aeroporto de Guarulhos, SP",
        hashtags="#AvisoAereo #CódigosDeAeroporto #IATA #ICAO",
    ),
    Topic(
        slug="numero_pista", kind="edu_codes", kicker_text="CURIOSIDADE",
        cover_title="O que os números das pistas dos aeroportos significam",
        heading_1="A LÓGICA:",
        body_1="O número de uma pista vem do rumo magnético dela, arredondado e dividido por 10 — uma "
               "pista '09' aponta aproximadamente para 090° (leste), e a mesma pista, no sentido "
               "contrário, vira a pista '27' (270°, oeste).",
        heading_2="QUANDO TEM LETRA:",
        body_2="Aeroportos com pistas paralelas usam L (esquerda), C (centro) ou R (direita) depois do "
               "número — como em Guarulhos, que tem as pistas 09L/27R e 09R/27L.",
        hashtags="#AvisoAereo #Pistas #Aviação #Curiosidade",
    ),
    # --- o que significam NOTAM e METAR ---
    Topic(
        slug="o_que_e_metar", kind="edu_notam_metar", kicker_text="BASTIDORES",
        cover_title="O que é METAR, o boletim que a AvisoAereo lê toda hora",
        heading_1="O QUE É:",
        body_1="METAR é o boletim meteorológico oficial de um aeroporto, emitido normalmente de hora em "
               "hora (ou antes, se o tempo mudar rápido) — traz vento, visibilidade, nuvens, "
               "temperatura e pressão no formato que pilotos e controladores usam no mundo inteiro.",
        heading_2="POR QUE É CODIFICADO:",
        body_2="O formato é padronizado internacionalmente pra caber em poucas letras e números e ser "
               "lido igual em qualquer país — é essa mesma fonte que a AvisoAereo usa pra saber quando "
               "o tempo está fora dos limites normais de operação.",
        raw_snippet="24015KT 1000 RA BKN008 18/17 Q1012 = vento 240°/15kt, visibilidade 1000m, chuva, "
                    "nuvens baixas a 800 pés",
        raw_snippet_label="COMO LER",
        hashtags="#AvisoAereo #METAR #Meteorologia #Aviação",
    ),
    Topic(
        slug="o_que_e_notam", kind="edu_notam_metar", kicker_text="BASTIDORES",
        cover_title="O que é um NOTAM, o outro aviso que a gente acompanha",
        heading_1="O QUE É:",
        body_1="NOTAM (Notice to Airmen) é um aviso oficial aos pilotos sobre qualquer mudança "
               "temporária ou permanente que afete a segurança do voo — pista fechada, equipamento de "
               "navegação fora do ar, obstáculo novo perto do aeroporto, entre outros.",
        heading_2="DIFERENÇA PRO METAR:",
        body_2="Enquanto o METAR é sobre o tempo (e muda de hora em hora), o NOTAM é sobre a "
               "infraestrutura e as regras do aeroporto naquele momento — e pode ficar em vigor por "
               "horas, dias ou semanas, até ser cancelado.",
        hashtags="#AvisoAereo #NOTAM #Aviação #Curiosidade",
    ),
    # --- códigos e matrículas de aeronaves ---
    Topic(
        slug="matricula_aeronave", kind="edu_registration", kicker_text="CURIOSIDADE",
        cover_title="A 'placa' de todo avião: como funciona a matrícula",
        heading_1="O QUE É:",
        body_1="Toda aeronave registrada no Brasil tem uma matrícula única, pintada na fuselagem, "
               "começando com PP, PR, PS ou PT seguido de 3 letras — funciona como uma placa de carro, "
               "identificando aquele avião específico junto à ANAC.",
        heading_2="PRA QUE SERVE:",
        body_2="É por essa matrícula (e pelo indicativo de chamada/callsign do voo) que sites e "
               "aplicativos de rastreamento de voos mostram, em tempo real, qual aeronave exata está "
               "fazendo cada trajeto.",
        raw_snippet="PR-XYZ — o 'PR' indica registro brasileiro; as 3 letras seguintes identificam a "
                    "aeronave",
        raw_snippet_label="COMO FUNCIONA",
        hashtags="#AvisoAereo #MatrículaDeAeronave #Aviação #Curiosidade",
    ),
    Topic(
        slug="rastreamento_voos", kind="edu_registration", kicker_text="CURIOSIDADE",
        cover_title="Como é possível acompanhar um voo em tempo real",
        heading_1="COMO FUNCIONA:",
        body_1="Aviões comerciais transmitem sua posição, altitude e velocidade continuamente por um "
               "sistema chamado ADS-B — sites e aplicativos de rastreamento captam esse sinal e mostram "
               "o trajeto no mapa em tempo real.",
        heading_2="O QUE DÁ PRA VER:",
        body_2="Além da posição, dá pra ver a matrícula da aeronave, o modelo, a rota prevista e até o "
               "histórico de voos daquele avião específico nos dias anteriores.",
        hashtags="#AvisoAereo #ADSB #RastreamentoDeVoos #Aviação",
    ),
    # --- aviação executiva / jatinhos ---
    Topic(
        slug="categorias_jatinhos", kind="edu_jets", kicker_text="AVIAÇÃO EXECUTIVA",
        cover_title="Jato leve, médio ou grande: qual a diferença",
        heading_1="A CLASSIFICAÇÃO:",
        body_1="Jatos executivos costumam ser divididos em leves, médios e grandes (ou 'de longo "
               "alcance') — a diferença principal está no alcance, na velocidade de cruzeiro (em geral "
               "entre 750 e 900 km/h) e no número de passageiros, de 4-8 nos leves a mais de 12 nos "
               "maiores.",
        heading_2="ALCANCE:",
        body_2="Um jato leve costuma voar trechos de até 2-3 mil km sem escala, enquanto um jato de "
               "longo alcance consegue cruzar oceanos inteiros sem parar — é essa diferença que define "
               "o preço e o tipo de missão de cada categoria.",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
    ),
    Topic(
        slug="custo_jatinho", kind="edu_jets", kicker_text="AVIAÇÃO EXECUTIVA",
        cover_title="Quanto custa (de verdade) voar de jato executivo",
        heading_1="O CUSTO POR HORA:",
        body_1="Um jato executivo consome, dependendo do porte, algumas centenas de litros de "
               "combustível por hora de voo — some manutenção, tripulação, seguro e taxas de hangar, e "
               "o custo-hora total costuma ficar bem acima do de um voo comercial equivalente.",
        heading_2="POR QUE AINDA COMPENSA PRA ALGUNS:",
        body_2="Pra viagens corporativas com pouca flexibilidade de agenda, o jato executivo elimina "
               "escalas, conexões e tempo de espera em aeroporto — é essa economia de tempo, não o "
               "preço do bilhete, que costuma justificar o custo.",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
    ),
    Topic(
        slug="instalacoes_jatinho", kind="edu_jets", kicker_text="AVIAÇÃO EXECUTIVA",
        cover_title="O que tem dentro de um jato executivo maior",
        heading_1="ALÉM DOS ASSENTOS:",
        body_1="Jatos executivos de maior porte podem ter cabine dividida em ambientes (sala de estar, "
               "área de trabalho, quarto), cozinha completa e, em alguns modelos de longo alcance, até "
               "um pequeno banheiro com chuveiro.",
        heading_2="POR QUE ISSO EXISTE:",
        body_2="Voos muito longos sem escala podem durar mais de 12 horas — o espaço extra e o conforto "
               "compensam justamente pela ausência de qualquer parada no meio do trajeto.",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
    ),
]


def build_fallback_post(topic: Topic) -> PostContent:
    """Monta o PostContent de um tópico educativo — mesma estrutura de carrossel
    (capa + explicativo) dos posts de aviso real, mas com severity="informativo"
    (cor azul, ver slide.py) pra nunca ser confundido com um alerta de verdade."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    explicativo = ExplicativoContent(
        subtitulo=topic.kicker_text.capitalize(),
        o_que_aconteceu=topic.body_1,
        o_que_significa=topic.body_2,
        duracao_prevista=None,
        raw_snippet=topic.raw_snippet,
        heading_1=topic.heading_1,
        heading_2=topic.heading_2,
        raw_snippet_label=topic.raw_snippet_label,
    )

    caption_lines = [
        f"✈️ {topic.cover_title}",
        "",
        topic.body_1,
        "",
        topic.body_2,
        "",
        "Sem nenhum aviso ativo nos aeroportos monitorados agora — aproveitamos pra trazer essa "
        "curiosidade.",
        "",
        topic.hashtags,
    ]

    return PostContent(
        icao="_FALLBACK",
        city="",
        uf="",
        headline="CURIOSIDADE",
        headline_kind=topic.kind,
        severity="informativo",
        bullets=[topic.body_1],
        updated_label="Conteúdo educativo",
        caption="\n".join(caption_lines),
        cover_title=topic.cover_title,
        cover_subtitle=None,
        background_category="navaid",  # só usado se não houver foto genérica da categoria (ver backgrounds.py)
        needs_explicativo=True,
        explicativo=explicativo,
        dedup_key=f"fallback|{topic.slug}|{hoje}",
        kicker_text=topic.kicker_text,
    )


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    for topic in TOPICS:
        post = build_fallback_post(topic)
        print(f"=== {topic.slug} ({post.dedup_key}) ===")
        print(f"CAPA titulo: {post.cover_title}")
        print("--- legenda ---")
        print(post.caption)
        print()
