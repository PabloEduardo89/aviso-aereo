"""
Conteúdo educativo de fallback — carrossel com 6-7 slides de conteúdo (+1 CTA
final, acrescentado por slide.py) que run_cycle.py publica quando não sai
nenhum post informativo real dentro de MIN_FALLBACK_INTERVAL_SECONDS (6h —
regra atualizada em 2026-08-27, ver run_cycle.py).

Reescrito em 2026-08-27 (pedido do usuário): antes eram só 3 slides (capa + 2
blocos grandes de texto corrido, em layout de fundo branco). Agora cada tópico
vira uma sequência de 6-7 slides curtos, todos no MESMO molde visual dos posts
de alerta (foto real + degradê + kicker + título curto, ver slide.py) — sem
mais nenhuma distinção de layout entre "informativo real" e "educativo". Cada
slide tem sua PRÓPRIA palavra-chave de busca de imagem (Pexels), pra nunca
repetir foto dentro do carrossel nem entre posts.

Não é uma notícia/alerta — é conteúdo educativo rotativo sobre regras, códigos
e curiosidades da aviação (aprovado pelo usuário em 2026-08-23), com visual
propositalmente diferente (azul, severity="informativo" — ver slide.py) do
vermelho dos alertas reais, pra nunca ser confundido com um aviso de verdade.

Os tópicos giram em ordem fixa (ver `fallback_topic_index` em state.py via
get_meta/set_meta), passando por todos antes de repetir qualquer um.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from content import PostContent, SlideSpec


@dataclass
class EduSlide:
    kicker_text: str
    title: str            # curto — no máximo 2 linhas no slide (mesma regra dos posts de alerta)
    subtitle: str | None = None
    image_query: str = "aviação aeroporto"  # toda foto de slide educativo vem do Pexels — não há
    # "foto oficial do aeroporto" pra reaproveitar aqui como nos posts de alerta (ver slide.py)


@dataclass
class Topic:
    slug: str            # identificador único, usado no dedup_key
    kind: str             # chave de categoria educativa — ver _GENERIC_CATEGORY_BY_KIND em backgrounds.py
    hashtags: str
    caption_summary: str  # 2-3 frases corridas pra legenda do Instagram, resumindo o tópico inteiro
    slides: list           # list[EduSlide] — 6 ou 7 itens (a distinção fica a critério de quem escreve
    # o tópico nesse arquivo, conforme pede mais ou menos slides pra caber bem)


TOPICS = [
    # --- regras, leis e regulamentos da aviação (geral e comercial) ---
    Topic(
        slug="direitos_passageiro", kind="edu_rules",
        hashtags="#AvisoAereo #DireitosDoPassageiro #ANAC #Aviação",
        caption_summary="Atraso de mais de 4 horas ou cancelamento dá direito a reacomodação, reembolso "
                         "integral ou outra modalidade de transporte, à sua escolha. E a companhia deve "
                         "oferecer assistência (comunicação, alimentação, hospedagem) proporcional ao "
                         "tempo de espera, mesmo antes das 4 horas.",
        slides=[
            EduSlide("VOCÊ SABIA?", "Seu voo atrasou? Veja seus direitos",
                     image_query="atraso voo aeroporto espera"),
            EduSlide("A REGRA", "Mais de 4h de atraso? Você escolhe",
                     "Reacomodação, reembolso ou outro transporte — a escolha é sua.",
                     "balcão atendimento aeroporto"),
            EduSlide("ASSISTÊNCIA", "Direito a comunicação, comida e hospedagem",
                     "Mesmo antes de completar as 4 horas de espera.",
                     "passageiro esperando aeroporto"),
            EduSlide("CANCELAMENTO", "Cancelou o voo? As regras são as mesmas",
                     image_query="painel voos cancelados aeroporto"),
            EduSlide("QUEM DECIDE", "A ANAC regula, mas a empresa deve cumprir",
                     image_query="regulação aviação documentos"),
            EduSlide("NA PRÁTICA", "Guarde o comprovante do atraso, sempre",
                     "Ele é sua prova pra cobrar os direitos depois.",
                     "documento comprovante viagem"),
        ],
    ),
    Topic(
        slug="overbooking", kind="edu_rules",
        hashtags="#AvisoAereo #Overbooking #ANAC #Aviação",
        caption_summary="Overbooking é a prática, autorizada pela ANAC, de vender mais bilhetes do que "
                         "assentos disponíveis. Quando sobra gente, a empresa deve primeiro pedir "
                         "voluntários com compensação, antes de recusar embarque à força — quem é "
                         "preterido sem querer tem direito a indenização, reacomodação e assistência.",
        slides=[
            EduSlide("VOCÊ SABIA?", "Por que venderam mais passagens que assentos?",
                     image_query="fila embarque aeroporto lotado"),
            EduSlide("O QUE É", "Overbooking é aposta calculada da empresa",
                     "Vende a mais apostando que alguém não vai aparecer.",
                     "balcão check-in companhia aérea"),
            EduSlide("SE SOBRAR GENTE", "Primeiro, a empresa pede voluntários",
                     "Com compensação — dinheiro, milhas ou outro benefício.",
                     "passageiros fila aeroporto"),
            EduSlide("SE NINGUÉM TOPAR", "Recusa forçada dá direito a indenização",
                     image_query="avião portão embarque"),
            EduSlide("VALE SABER", "Você pode negociar sua própria compensação",
                     image_query="aperto de mãos acordo"),
            EduSlide("NA PRÁTICA", "Chegue cedo — reduz o risco de ficar de fora",
                     image_query="relógio aeroporto check-in"),
        ],
    ),
    Topic(
        slug="bagagem", kind="edu_rules",
        hashtags="#AvisoAereo #Bagagem #ANAC #Aviação",
        caption_summary="Em voos domésticos no Brasil, toda passagem dá direito a pelo menos uma bagagem "
                         "despachada gratuita, com peso mínimo de 23 kg, independente da tarifa. Isso vale "
                         "só pra despachada — a de mão tem limite próprio, que varia por companhia.",
        slides=[
            EduSlide("VOCÊ SABIA?", "Quanta bagagem grátis você tem direito",
                     image_query="mala aeroporto esteira"),
            EduSlide("A REGRA", "23kg despachados de graça, sempre",
                     "Vale pra qualquer tarifa, mesmo a promocional.",
                     "balança bagagem aeroporto"),
            EduSlide("BAGAGEM DE MÃO", "Tem limite próprio, e varia por empresa",
                     image_query="mala de mão avião"),
            EduSlide("EXCEDEU O PESO?", "A empresa pode cobrar taxa extra",
                     image_query="etiqueta bagagem aeroporto"),
            EduSlide("ITENS PROIBIDOS", "Líquidos, baterias soltas e cortantes ficam de fora",
                     image_query="segurança aeroporto raio-x"),
            EduSlide("DICA", "Pese a mala em casa antes de sair",
                     image_query="balança doméstica mala"),
        ],
    ),
    # --- significado dos códigos de aeroporto ---
    Topic(
        slug="iata_icao", kind="edu_codes",
        hashtags="#AvisoAereo #CódigosDeAeroporto #IATA #ICAO",
        caption_summary="Todo aeroporto tem dois códigos: o IATA, de 3 letras (o que aparece na etiqueta "
                         "da mala, como GRU), e o ICAO, de 4 letras, usado tecnicamente pelo controle de "
                         "tráfego aéreo e nos boletins METAR/NOTAM (como SBGR, o mesmo Guarulhos).",
        slides=[
            EduSlide("CURIOSIDADE", "IATA ou ICAO? Todo aeroporto tem os dois",
                     image_query="placa aeroporto código"),
            EduSlide("O CÓDIGO IATA", "3 letras que você vê na etiqueta da mala",
                     "Ex.: GRU é Guarulhos.", "etiqueta mala aeroporto"),
            EduSlide("O CÓDIGO ICAO", "4 letras usadas por pilotos e controladores",
                     "Ex.: SBGR, o mesmo Guarulhos.", "torre controle aeroporto"),
            EduSlide("POR QUE 'SB' NO BRASIL", "A 1ª letra indica a região do mundo",
                     image_query="mapa mundi aviação"),
            EduSlide("NEM SEMPRE BATEM", "Às vezes as duas siglas nem se parecem",
                     image_query="letreiro aeroporto internacional"),
            EduSlide("TESTE VOCÊ", "Sabe o código do aeroporto mais perto de você?",
                     image_query="aeroporto pista avião"),
        ],
    ),
    Topic(
        slug="numero_pista", kind="edu_codes",
        hashtags="#AvisoAereo #Pistas #Aviação #Curiosidade",
        caption_summary="O número de uma pista vem do rumo magnético dela, arredondado e dividido por "
                         "10 — a pista '09' aponta para ~090° (leste), e a mesma pista no sentido "
                         "contrário vira a '27'. Pistas paralelas ganham L, C ou R depois do número.",
        slides=[
            EduSlide("CURIOSIDADE", "O que os números da pista significam",
                     image_query="pista aeroporto numeração"),
            EduSlide("A LÓGICA", "O número é o rumo magnético, dividido por 10",
                     "Pista 09 aponta pra ~090° (leste).", "bússola direção"),
            EduSlide("MESMA PISTA, 2 NOMES", "No sentido contrário, vira outro número",
                     "A pista 09 de um lado é a 27 do outro.", "pista aeroporto vista aérea"),
            EduSlide("QUANDO TEM LETRA", "L, C ou R identificam pistas paralelas",
                     image_query="pistas paralelas aeroporto"),
            EduSlide("EXEMPLO REAL", "Guarulhos tem 09L/27R e 09R/27L",
                     image_query="aeroporto pista asfalto"),
            EduSlide("PRA QUE SERVE", "Ajuda o piloto a confirmar a pista certa",
                     image_query="cabine piloto avião"),
        ],
    ),
    # --- o que significam NOTAM e METAR ---
    Topic(
        slug="o_que_e_metar", kind="edu_notam_metar",
        hashtags="#AvisoAereo #METAR #Meteorologia #Aviação",
        caption_summary="METAR é o boletim meteorológico oficial de um aeroporto, emitido de hora em "
                         "hora (ou antes, se o tempo mudar rápido) — vento, visibilidade, nuvens, "
                         "temperatura e pressão, no formato padronizado que a AvisoAereo lê pra saber "
                         "quando o tempo sai dos limites normais de operação.",
        slides=[
            EduSlide("BASTIDORES", "O boletim que a AvisoAereo lê toda hora",
                     image_query="estação meteorológica aeroporto"),
            EduSlide("O QUE É", "METAR é o raio-x do tempo no aeroporto",
                     "Emitido de hora em hora, ou antes se o tempo mudar rápido.",
                     "nuvens céu aeroporto"),
            EduSlide("O QUE TRAZ", "Vento, visibilidade, nuvens, temperatura e pressão",
                     image_query="manga de vento aeroporto"),
            EduSlide("PADRÃO MUNDIAL", "O mesmo formato em qualquer país do planeta",
                     image_query="globo mundo aviação"),
            EduSlide("COMO LER", "Letras e números concentram uma frase inteira",
                     "Ex.: 24015KT = vento de 240°, 15 nós.", "código dados tela"),
            EduSlide("QUEM USA", "Pilotos e controladores decidem com base nele",
                     image_query="torre controle tráfego aéreo"),
            EduSlide("POR QUE IMPORTA PRA VOCÊ", "É a fonte oficial por trás de cada alerta daqui",
                     image_query="passageiro olhando avião"),
        ],
    ),
    Topic(
        slug="o_que_e_notam", kind="edu_notam_metar",
        hashtags="#AvisoAereo #NOTAM #Aviação #Curiosidade",
        caption_summary="NOTAM (Notice to Airmen) é um aviso oficial aos pilotos sobre mudança temporária "
                         "ou permanente que afete a segurança do voo — pista fechada, equipamento fora do "
                         "ar, obstáculo novo. Diferente do METAR (o tempo), o NOTAM é sobre a "
                         "infraestrutura, e pode ficar em vigor por horas, dias ou semanas.",
        slides=[
            EduSlide("BASTIDORES", "O outro aviso que a AvisoAereo acompanha",
                     image_query="aviso placa aeroporto"),
            EduSlide("O QUE É", "Um recado oficial pros pilotos, não pro tempo",
                     "NOTAM = Notice to Airmen.", "piloto documentos cabine"),
            EduSlide("O QUE ELE AVISA", "Pista fechada, equipamento fora do ar, obstáculo novo",
                     image_query="obstáculo construção aeroporto"),
            EduSlide("DIFERENÇA DO METAR", "METAR é o tempo; NOTAM é a estrutura",
                     image_query="pista manutenção aeroporto"),
            EduSlide("QUANTO TEMPO DURA", "Pode ficar em vigor por horas, dias ou semanas",
                     image_query="calendário tempo espera"),
            EduSlide("QUEM CANCELA", "Só sai da lista quando o problema é resolvido",
                     image_query="equipe manutenção aeroporto"),
            EduSlide("POR QUE IMPORTA", "É a fonte oficial por trás de vários alertas daqui",
                     image_query="radar aeroporto tecnologia"),
        ],
    ),
    # --- códigos e matrículas de aeronaves ---
    Topic(
        slug="matricula_aeronave", kind="edu_registration",
        hashtags="#AvisoAereo #MatrículaDeAeronave #Aviação #Curiosidade",
        caption_summary="Toda aeronave registrada no Brasil tem uma matrícula única, pintada na "
                         "fuselagem, começando com PP, PR, PS ou PT seguido de 3 letras — funciona como "
                         "uma placa de carro, identificando aquele avião específico junto à ANAC.",
        slides=[
            EduSlide("CURIOSIDADE", "A 'placa' de todo avião",
                     image_query="fuselagem avião pintura"),
            EduSlide("COMO FUNCIONA", "Toda aeronave brasileira começa com PP, PR, PS ou PT",
                     image_query="avião pista matrícula"),
            EduSlide("ONDE FICA", "Pintada bem visível na fuselagem ou na cauda",
                     image_query="cauda avião logotipo"),
            EduSlide("PRA QUE SERVE", "Identifica o avião específico junto à ANAC",
                     image_query="documentos aviação regulação"),
            EduSlide("TIPO PLACA DE CARRO", "Cada matrícula pertence a uma única aeronave",
                     image_query="avião estacionado pátio"),
            EduSlide("CURIOSIDADE EXTRA", "É por ela que apps de rastreamento identificam seu voo",
                     image_query="celular aplicativo tecnologia"),
        ],
    ),
    Topic(
        slug="rastreamento_voos", kind="edu_registration",
        hashtags="#AvisoAereo #ADSB #RastreamentoDeVoos #Aviação",
        caption_summary="Aviões comerciais transmitem posição, altitude e velocidade continuamente por um "
                         "sistema chamado ADS-B — sites e apps captam esse sinal e mostram o trajeto no "
                         "mapa em tempo real, junto com matrícula, modelo e histórico de voos.",
        slides=[
            EduSlide("CURIOSIDADE", "Como dá pra ver um avião em tempo real",
                     image_query="mapa rastreamento avião"),
            EduSlide("A TECNOLOGIA", "Todo avião comercial transmite sua posição sozinho",
                     "O sistema se chama ADS-B.", "antena transmissão sinal"),
            EduSlide("O QUE É TRANSMITIDO", "Posição, altitude e velocidade, o tempo todo",
                     image_query="painel avião instrumentos"),
            EduSlide("QUEM CAPTA", "Sites e apps recebem o sinal e desenham o mapa",
                     image_query="tela computador mapa"),
            EduSlide("O QUE MAIS DÁ PRA VER", "Modelo do avião, rota prevista e histórico",
                     image_query="avião decolando pista"),
            EduSlide("TESTE VOCÊ", "Da próxima vez, rastreie seu próprio voo",
                     image_query="passageiro celular janela avião"),
        ],
    ),
    # --- aviação executiva / jatinhos ---
    Topic(
        slug="categorias_jatinhos", kind="edu_jets",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
        caption_summary="Jatos executivos se dividem em leves, médios e de longo alcance — a diferença "
                         "está no alcance, na velocidade (750-900 km/h em geral) e no número de "
                         "passageiros, de 4-8 nos leves a mais de 12 nos maiores.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "Jato leve, médio ou grande — qual a diferença",
                     image_query="jato executivo pista"),
            EduSlide("JATOS LEVES", "4 a 8 passageiros, viagens de até 3 mil km",
                     image_query="jato pequeno executivo"),
            EduSlide("JATOS MÉDIOS", "Mais cabine, mais alcance, mais conforto",
                     image_query="cabine jato executivo"),
            EduSlide("LONGO ALCANCE", "Cruzam oceanos inteiros sem escala",
                     image_query="jato executivo voando nuvens"),
            EduSlide("VELOCIDADE", "Cruzeiro entre 750 e 900 km/h, em geral",
                     image_query="avião velocidade céu"),
            EduSlide("O QUE DEFINE O PREÇO", "Alcance e tamanho da cabine, não só luxo",
                     image_query="interior jato luxo"),
        ],
    ),
    Topic(
        slug="custo_jatinho", kind="edu_jets",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
        caption_summary="Um jato executivo consome centenas de litros de combustível por hora — some "
                         "manutenção, tripulação, seguro e hangar, e o custo-hora fica bem acima de um "
                         "voo comercial. O que compensa, pra quem usa, é o tempo que se ganha.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "Quanto custa (de verdade) voar de jato",
                     image_query="jato executivo pátio"),
            EduSlide("COMBUSTÍVEL", "Centenas de litros por hora de voo",
                     image_query="abastecimento avião pista"),
            EduSlide("MANUTENÇÃO", "Peça e mão de obra especializada custam caro",
                     image_query="mecânico avião manutenção"),
            EduSlide("TRIPULAÇÃO E HANGAR", "Salário, seguro e armazenagem entram na conta",
                     image_query="hangar avião executivo"),
            EduSlide("CUSTO-HORA", "Bem acima de um voo comercial equivalente",
                     image_query="cabine piloto controle"),
            EduSlide("POR QUE COMPENSA", "Não é o preço — é o tempo que se ganha",
                     image_query="executivo viagem trabalho"),
        ],
    ),
    Topic(
        slug="instalacoes_jatinho", kind="edu_jets",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
        caption_summary="Jatos executivos maiores podem ter cabine dividida em ambientes, cozinha "
                         "completa e, em alguns modelos de longo alcance, até banheiro com chuveiro — o "
                         "espaço extra compensa voos sem escala que passam de 12 horas.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "O que tem dentro de um jato executivo grande",
                     image_query="interior jato executivo luxo"),
            EduSlide("AMBIENTES SEPARADOS", "Sala de estar, área de trabalho, quarto",
                     image_query="sofá cabine avião"),
            EduSlide("COZINHA COMPLETA", "Refeições preparadas a bordo, em pleno voo",
                     image_query="cozinha avião gourmet"),
            EduSlide("ATÉ BANHEIRO COM CHUVEIRO", "Em alguns modelos de longuíssimo alcance",
                     image_query="banheiro avião luxo"),
            EduSlide("POR QUE TANTO CONFORTO", "Voos sem escala podem passar de 12 horas",
                     image_query="avião voando noite"),
            EduSlide("QUEM VOA ASSIM", "Executivos, chefes de estado e grandes famílias",
                     image_query="avião privado pista"),
        ],
    ),
    # --- mercado de trabalho aeronáutico: pilotos, comissários, mecânicos ---
    Topic(
        slug="carreira_piloto", kind="edu_careers",
        hashtags="#AvisoAereo #CarreiraDePiloto #Aviação #MercadoDeTrabalho",
        caption_summary="Virar piloto comercial no Brasil exige escola homologada pela ANAC e muitas "
                         "horas de voo até chegar numa companhia grande — um caminho de anos. Fora do "
                         "Brasil, mercados como EUA e Oriente Médio têm escassez recorrente de pilotos.",
        slides=[
            EduSlide("MERCADO DE TRABALHO", "Como é virar piloto de verdade no Brasil",
                     image_query="piloto uniforme aeroporto"),
            EduSlide("O CAMINHO", "Escola de aviação civil homologada pela ANAC",
                     image_query="escola aviação treinamento"),
            EduSlide("HORAS DE VOO", "Muitas horas acumuladas até evoluir de nível",
                     image_query="avião pequeno instrução"),
            EduSlide("PRIMEIROS PASSOS", "Instrutor, aviação executiva ou de carga",
                     image_query="avião carga pista"),
            EduSlide("ATÉ A GRANDE COMPANHIA", "Um caminho que costuma levar anos",
                     image_query="avião comercial pátio"),
            EduSlide("OPORTUNIDADE FORA", "EUA e Oriente Médio têm escassez de pilotos",
                     image_query="aeroporto internacional voos"),
            EduSlide("NA PRÁTICA", "Boa parte revalida a licença no país de destino",
                     image_query="documentos licença aviação"),
        ],
    ),
    Topic(
        slug="carreira_comissario_mecanico", kind="edu_careers",
        hashtags="#AvisoAereo #ComissárioDeVoo #MecânicoDeAeronaves #MercadoDeTrabalho",
        caption_summary="Comissário exige o CCF, curso homologado pela ANAC, com inglês fluente pesando "
                         "na seleção. Mecânico de aeronaves passa por curso técnico e licenças por tipo "
                         "de aeronave — área com demanda global relativamente estável.",
        slides=[
            EduSlide("MERCADO DE TRABALHO", "Comissário ou mecânico: como entrar na área",
                     image_query="comissário bordo avião"),
            EduSlide("COMISSÁRIO DE VOO", "Exige curso específico homologado pela ANAC",
                     "O CCF — Curso de Formação de Comissários.", "treinamento comissário voo"),
            EduSlide("INGLÊS PESA MUITO", "Fluência conta ponto forte na seleção",
                     image_query="entrevista emprego escritório"),
            EduSlide("DEMANDA VARIA", "Cresce e encolhe com a abertura de rotas novas",
                     image_query="avião novo rota"),
            EduSlide("MECÂNICO DE AERONAVES", "Curso técnico e depois licença por tipo de avião",
                     image_query="mecânico ferramenta avião"),
            EduSlide("DEMANDA GLOBAL ESTÁVEL", "Todo avião no mundo precisa de manutenção certificada",
                     image_query="hangar manutenção aeronave"),
            EduSlide("NA PRÁTICA", "Área técnica com portas abertas em vários países",
                     image_query="aeroporto internacional trabalho"),
        ],
    ),
]


def build_fallback_post(topic: Topic) -> PostContent:
    """Monta o PostContent de um tópico educativo — carrossel de 6-7 slides curtos
    (ver Topic.slides), todos no mesmo molde visual dos posts de alerta (regra
    fixa 2026-08-27), com severity="informativo" (cor azul, ver slide.py) pra
    nunca ser confundido com um aviso de verdade."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    slides = [
        SlideSpec(kicker_text=s.kicker_text, title=s.title, subtitle=s.subtitle, image_query=s.image_query)
        for s in topic.slides
    ]

    caption_lines = [
        f"✈️ {topic.slides[0].title}",
        "",
        topic.caption_summary,
        "",
        "A AvisoAereo publica atualizações de aeroportos brasileiros direto das fontes oficiais do "
        "DECEA (REDEMET/AISWEB). Sem nenhum aviso ativo relevante agora, aproveitamos pra trazer "
        "essa curiosidade.",
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
        caption="\n".join(caption_lines),
        slides=slides,
        background_category="navaid",  # só usado se Pexels e foto genérica falharem os 2 (ver backgrounds.py)
        dedup_key=f"fallback|{topic.slug}|{hoje}",
    )


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    for topic in TOPICS:
        post = build_fallback_post(topic)
        print(f"=== {topic.slug} ({post.dedup_key}) — {len(post.slides)} slide(s) + CTA ===")
        for i, s in enumerate(post.slides, start=1):
            print(f"  slide {i}: [{s.kicker_text}] {s.title} (foto: {s.image_query})")
        print("--- legenda ---")
        print(post.caption)
        print()
