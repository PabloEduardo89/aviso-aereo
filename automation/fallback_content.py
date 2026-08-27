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
from dataclasses import dataclass, field
from datetime import datetime, timezone

from content import PostContent, SlideSpec
from jobs import fetch_real_job


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
    job_categories: list = field(default_factory=list)  # categorias de jobs.JOB_FEEDS pra buscar vaga
    # REAL e recente e acrescentar como slide(s) extra no fim (pedido do usuário, 2026-08-27: "sempre que
    # possível anunciando vagas de trabalho... reais"). Vazio (padrão) = tópico sem busca de vaga ao vivo.
    # Quando a busca falha ou não há vaga no momento, o slide correspondente simplesmente não é incluído
    # — nunca quebra o post por causa disso (ver build_fallback_post).


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
                     image_query="flight delay airport waiting"),
            EduSlide("A REGRA", "Mais de 4h de atraso? Você escolhe",
                     "Reacomodação, reembolso ou outro transporte — a escolha é sua.",
                     "airport service counter"),
            EduSlide("ASSISTÊNCIA", "Direito a comunicação, comida e hospedagem",
                     "Mesmo antes de completar as 4 horas de espera.",
                     "passenger waiting airport lounge"),
            EduSlide("CANCELAMENTO", "Cancelou o voo? As regras são as mesmas",
                     image_query="flight cancelled board airport"),
            EduSlide("QUEM DECIDE", "A ANAC regula, mas a empresa deve cumprir",
                     image_query="aviation regulation documents"),
            EduSlide("NA PRÁTICA", "Guarde o comprovante do atraso, sempre",
                     "Ele é sua prova pra cobrar os direitos depois.",
                     "travel receipt document"),
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
                     image_query="crowded airport boarding gate"),
            EduSlide("O QUE É", "Overbooking é aposta calculada da empresa",
                     "Vende a mais apostando que alguém não vai aparecer.",
                     "airline check-in counter"),
            EduSlide("SE SOBRAR GENTE", "Primeiro, a empresa pede voluntários",
                     "Com compensação — dinheiro, milhas ou outro benefício.",
                     "passengers queue airport"),
            EduSlide("SE NINGUÉM TOPAR", "Recusa forçada dá direito a indenização",
                     image_query="airplane boarding gate"),
            EduSlide("VALE SABER", "Você pode negociar sua própria compensação",
                     image_query="handshake business agreement"),
            EduSlide("NA PRÁTICA", "Chegue cedo — reduz o risco de ficar de fora",
                     image_query="airport clock check-in"),
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
                     image_query="luggage airport conveyor belt"),
            EduSlide("A REGRA", "23kg despachados de graça, sempre",
                     "Vale pra qualquer tarifa, mesmo a promocional.",
                     "luggage scale airport"),
            EduSlide("BAGAGEM DE MÃO", "Tem limite próprio, e varia por empresa",
                     image_query="carry-on bag airplane cabin"),
            EduSlide("EXCEDEU O PESO?", "A empresa pode cobrar taxa extra",
                     image_query="luggage tag airport"),
            EduSlide("ITENS PROIBIDOS", "Líquidos, baterias soltas e cortantes ficam de fora",
                     image_query="airport security x-ray scanner"),
            EduSlide("DICA", "Pese a mala em casa antes de sair",
                     image_query="home scale suitcase"),
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
                     image_query="airport sign code"),
            EduSlide("O CÓDIGO IATA", "3 letras que você vê na etiqueta da mala",
                     "Ex.: GRU é Guarulhos.", "luggage tag airport"),
            EduSlide("O CÓDIGO ICAO", "4 letras usadas por pilotos e controladores",
                     "Ex.: SBGR, o mesmo Guarulhos.", "airport control tower"),
            EduSlide("POR QUE 'SB' NO BRASIL", "A 1ª letra indica a região do mundo",
                     image_query="world map aviation"),
            EduSlide("NEM SEMPRE BATEM", "Às vezes as duas siglas nem se parecem",
                     image_query="international airport terminal sign"),
            EduSlide("TESTE VOCÊ", "Sabe o código do aeroporto mais perto de você?",
                     image_query="airport runway airplane"),
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
                     image_query="airport runway numbers markings"),
            EduSlide("A LÓGICA", "O número é o rumo magnético, dividido por 10",
                     "Pista 09 aponta pra ~090° (leste).", "compass direction navigation"),
            EduSlide("MESMA PISTA, 2 NOMES", "No sentido contrário, vira outro número",
                     "A pista 09 de um lado é a 27 do outro.", "airport runway aerial view"),
            EduSlide("QUANDO TEM LETRA", "L, C ou R identificam pistas paralelas",
                     image_query="parallel runways airport"),
            EduSlide("EXEMPLO REAL", "Guarulhos tem 09L/27R e 09R/27L",
                     image_query="airport runway asphalt"),
            EduSlide("PRA QUE SERVE", "Ajuda o piloto a confirmar a pista certa",
                     image_query="airplane cockpit pilot"),
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
                     image_query="weather station airport"),
            EduSlide("O QUE É", "METAR é o raio-x do tempo no aeroporto",
                     "Emitido de hora em hora, ou antes se o tempo mudar rápido.",
                     "clouds sky airport"),
            EduSlide("O QUE TRAZ", "Vento, visibilidade, nuvens, temperatura e pressão",
                     image_query="windsock airport"),
            EduSlide("PADRÃO MUNDIAL", "O mesmo formato em qualquer país do planeta",
                     image_query="globe world map aviation"),
            EduSlide("COMO LER", "Letras e números concentram uma frase inteira",
                     "Ex.: 24015KT = vento de 240°, 15 nós.", "code data screen technology"),
            EduSlide("QUEM USA", "Pilotos e controladores decidem com base nele",
                     image_query="air traffic control tower"),
            EduSlide("POR QUE IMPORTA PRA VOCÊ", "É a fonte oficial por trás de cada alerta daqui",
                     image_query="passenger looking airplane window"),
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
                     image_query="warning sign airport runway"),
            EduSlide("O QUE É", "Um recado oficial pros pilotos, não pro tempo",
                     "NOTAM = Notice to Airmen.", "pilot documents cockpit"),
            EduSlide("O QUE ELE AVISA", "Pista fechada, equipamento fora do ar, obstáculo novo",
                     image_query="airport construction obstacle"),
            EduSlide("DIFERENÇA DO METAR", "METAR é o tempo; NOTAM é a estrutura",
                     image_query="runway maintenance airport"),
            EduSlide("QUANTO TEMPO DURA", "Pode ficar em vigor por horas, dias ou semanas",
                     image_query="calendar waiting time"),
            EduSlide("QUEM CANCELA", "Só sai da lista quando o problema é resolvido",
                     image_query="maintenance crew airport"),
            EduSlide("POR QUE IMPORTA", "É a fonte oficial por trás de vários alertas daqui",
                     image_query="radar airport technology"),
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
                     image_query="airplane fuselage paint closeup"),
            EduSlide("COMO FUNCIONA", "Toda aeronave brasileira começa com PP, PR, PS ou PT",
                     image_query="airplane runway registration number"),
            EduSlide("ONDE FICA", "Pintada bem visível na fuselagem ou na cauda",
                     image_query="airplane tail logo"),
            EduSlide("PRA QUE SERVE", "Identifica o avião específico junto à ANAC",
                     image_query="aviation documents regulation"),
            EduSlide("TIPO PLACA DE CARRO", "Cada matrícula pertence a uma única aeronave",
                     image_query="airplane parked apron"),
            EduSlide("CURIOSIDADE EXTRA", "É por ela que apps de rastreamento identificam seu voo",
                     image_query="smartphone app technology"),
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
                     image_query="airplane tracking map screen"),
            EduSlide("A TECNOLOGIA", "Todo avião comercial transmite sua posição sozinho",
                     "O sistema se chama ADS-B.", "antenna signal transmission"),
            EduSlide("O QUE É TRANSMITIDO", "Posição, altitude e velocidade, o tempo todo",
                     image_query="airplane instrument panel cockpit"),
            EduSlide("QUEM CAPTA", "Sites e apps recebem o sinal e desenham o mapa",
                     image_query="computer screen map data"),
            EduSlide("O QUE MAIS DÁ PRA VER", "Modelo do avião, rota prevista e histórico",
                     image_query="airplane taking off runway"),
            EduSlide("TESTE VOCÊ", "Da próxima vez, rastreie seu próprio voo",
                     image_query="passenger phone airplane window"),
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
                     image_query="private jet runway"),
            EduSlide("JATOS LEVES", "4 a 8 passageiros, viagens de até 3 mil km",
                     image_query="small private jet airplane"),
            EduSlide("JATOS MÉDIOS", "Mais cabine, mais alcance, mais conforto",
                     image_query="private jet cabin interior"),
            EduSlide("LONGO ALCANCE", "Cruzam oceanos inteiros sem escala",
                     image_query="private jet flying clouds"),
            EduSlide("VELOCIDADE", "Cruzeiro entre 750 e 900 km/h, em geral",
                     image_query="airplane speed sky"),
            EduSlide("O QUE DEFINE O PREÇO", "Alcance e tamanho da cabine, não só luxo",
                     image_query="luxury jet interior seats"),
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
                     image_query="private jet apron airport"),
            EduSlide("COMBUSTÍVEL", "Centenas de litros por hora de voo",
                     image_query="airplane refueling runway"),
            EduSlide("MANUTENÇÃO", "Peça e mão de obra especializada custam caro",
                     image_query="aircraft mechanic maintenance"),
            EduSlide("TRIPULAÇÃO E HANGAR", "Salário, seguro e armazenagem entram na conta",
                     image_query="private jet hangar"),
            EduSlide("CUSTO-HORA", "Bem acima de um voo comercial equivalente",
                     image_query="cockpit pilot controls"),
            EduSlide("POR QUE COMPENSA", "Não é o preço — é o tempo que se ganha",
                     image_query="business executive airport travel"),
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
                     image_query="luxury private jet interior"),
            EduSlide("AMBIENTES SEPARADOS", "Sala de estar, área de trabalho, quarto",
                     image_query="airplane cabin sofa lounge"),
            EduSlide("COZINHA COMPLETA", "Refeições preparadas a bordo, em pleno voo",
                     image_query="gourmet airplane galley food"),
            EduSlide("ATÉ BANHEIRO COM CHUVEIRO", "Em alguns modelos de longuíssimo alcance",
                     image_query="luxury airplane bathroom"),
            EduSlide("POR QUE TANTO CONFORTO", "Voos sem escala podem passar de 12 horas",
                     image_query="airplane flying night sky"),
            EduSlide("QUEM VOA ASSIM", "Executivos, chefes de estado e grandes famílias",
                     image_query="private airplane runway"),
        ],
    ),
    Topic(
        slug="fretar_vs_comprar_jato", kind="edu_jets",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
        caption_summary="Fretar um jato executivo significa pagar só quando voa, sem custo fixo; comprar "
                         "traz disponibilidade total, mas um custo fixo alto. Existe também a cota de "
                         "propriedade compartilhada, um meio-termo entre as duas opções.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "Fretar ou comprar: o que compensa mais",
                     image_query="private jet decision boarding"),
            EduSlide("FRETAR", "Paga só quando voa, sem custo fixo",
                     image_query="jet charter booking app"),
            EduSlide("COMPRAR", "Custo fixo alto, mas disponibilidade total",
                     image_query="private jet hangar owner"),
            EduSlide("PONTO DE EQUILÍBRIO", "Empresas calculam pelas horas voadas por ano",
                     image_query="business calculator finance"),
            EduSlide("MEIO-TERMO", "Cotas de propriedade compartilhada existem",
                     "Você é dono de uma fração do avião.", "group executives private jet"),
            EduSlide("NA PRÁTICA", "A maioria freta — poucos realmente compram",
                     image_query="private jet taking off"),
        ],
    ),
    Topic(
        slug="recordes_jato_executivo", kind="edu_jets",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
        caption_summary="Alguns jatos executivos cruzam mais de 14 mil km sem escala, aviões comerciais "
                         "convertidos viram cabines VIP, e os modelos mais caros já vendidos ultrapassam "
                         "100 milhões de dólares — manter um jato desses pode custar milhões por ano.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "Recordes que os jatos executivos já bateram",
                     image_query="private jet record breaking"),
            EduSlide("MAIOR ALCANCE", "Alguns modelos cruzam mais de 14 mil km sem parar",
                     image_query="private jet flying ocean"),
            EduSlide("MAIS RÁPIDO", "Jatos supersônicos voltaram a ser desenvolvidos",
                     image_query="supersonic airplane sky"),
            EduSlide("MAIOR CABINE", "Aviões comerciais convertidos viram jato VIP",
                     "Um Boeing ou Airbus, por dentro, todo reformado.", "vip airplane cabin interior"),
            EduSlide("MAIS CARO JÁ VENDIDO", "Alguns modelos ultrapassam 100 milhões de dólares",
                     image_query="luxury private jet wealth"),
            EduSlide("CURIOSIDADE FINAL", "Manter um jato do tipo pode custar milhões por ano",
                     image_query="luxury hangar maintenance"),
        ],
    ),
    Topic(
        slug="manutencao_jato_executivo", kind="edu_jets",
        hashtags="#AvisoAereo #AviaçãoExecutiva #JatosExecutivos #Curiosidade",
        caption_summary="Jatos executivos passam por checagens antes de cada voo e revisões programadas "
                         "por hora de voo, não por defeito. Tripulação dedicada, hangar e seguro completam "
                         "o custo fixo — qualquer falha em voo executivo tem tolerância zero.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "O que é preciso pra manter um jato voando",
                     image_query="aircraft mechanic hangar jet"),
            EduSlide("INSPEÇÕES CONSTANTES", "Checagens antes de cada voo, sem exceção",
                     image_query="pilot checklist airplane"),
            EduSlide("REVISÕES PROGRAMADAS", "Peças trocadas por hora de voo, não por defeito",
                     image_query="aircraft parts workshop"),
            EduSlide("TRIPULAÇÃO PRÓPRIA", "Pilotos e comissários dedicados, prontos pra qualquer hora",
                     image_query="flight crew uniform airport"),
            EduSlide("HANGAR E SEGURO", "Armazenagem e apólice também entram no custo fixo",
                     image_query="private jet hangar storage"),
            EduSlide("POR QUE TANTO CUIDADO", "Qualquer falha em voo executivo tem tolerância zero",
                     image_query="air traffic control safety"),
        ],
    ),
    # --- lugares incríveis e pouco visitados (com ângulo de aviação) ---
    Topic(
        slug="aeroportos_mais_dificeis", kind="edu_destinations",
        hashtags="#AvisoAereo #Aeroportos #Curiosidade #Aviação",
        caption_summary="Alguns aeroportos exigem treinamento extra dos pilotos: Paro, no Butão, só libera "
                         "cerca de 40 pilotos no mundo; Saba, no Caribe, tem a pista comercial mais curta "
                         "do planeta; e Courchevel, na França, tem pista inclinada sem chance de arremeter.",
        slides=[
            EduSlide("CURIOSIDADE", "Os aeroportos mais radicais do mundo",
                     image_query="mountain airport runway dramatic"),
            EduSlide("PARO, BUTÃO", "Só 40 pilotos no mundo pousam lá",
                     "Cercado de picos de mais de 5 mil metros.", "himalaya mountains airplane"),
            EduSlide("SABA, CARIBE", "A pista comercial mais curta do planeta",
                     "Menos de 400 metros de comprimento.", "short runway caribbean island"),
            EduSlide("GIBRALTAR", "A pista corta uma avenida movimentada",
                     image_query="airport runway city street"),
            EduSlide("COURCHEVEL, FRANÇA", "Pista inclinada, sem chance de arremeter",
                     image_query="ski resort mountain snow runway"),
            EduSlide("POR QUE ISSO IMPORTA", "Pilotos passam por treinamento extra pra voar lá",
                     image_query="pilot training cockpit"),
        ],
    ),
    Topic(
        slug="ilhas_dificeis_chegar", kind="edu_destinations",
        hashtags="#AvisoAereo #Destinos #Curiosidade #Aviação",
        caption_summary="Tristan da Cunha nem tem aeroporto — só chega de navio. Svalbard tem o aeroporto "
                         "mais ao norte do mundo com voos regulares. E ilhas como Bora Bora só se alcançam "
                         "com avião pequeno seguido de barco — o isolamento vira exclusividade.",
        slides=[
            EduSlide("CURIOSIDADE", "Paraísos que só um avião pequeno alcança",
                     image_query="paradise island aerial view"),
            EduSlide("TRISTAN DA CUNHA", "A ilha habitada mais isolada do mundo",
                     "Nem tem aeroporto — só chega de navio.", "remote island ocean"),
            EduSlide("ILHAS COOK", "Atóis que dependem de voos regionais raros",
                     image_query="turquoise atoll aerial"),
            EduSlide("SVALBARD, NORUEGA", "Aeroporto mais ao norte do mundo com voos regulares",
                     image_query="arctic snow airport"),
            EduSlide("BORA BORA", "Chegada de avião, depois barco até o resort",
                     image_query="overwater bungalow blue lagoon"),
            EduSlide("O CUSTO DISSO", "Isolamento vira exclusividade — e preço alto",
                     image_query="small seaplane beach"),
        ],
    ),
    Topic(
        slug="destinos_jato_particular", kind="edu_destinations",
        hashtags="#AvisoAereo #AviaçãoExecutiva #Destinos #Curiosidade",
        caption_summary="Aspen, Mônaco, Ibiza e Dubai são clássicos entre quem voa de jato particular — "
                         "o que todos têm em comum é acesso fácil, exclusividade e discrição, mais do que "
                         "só luxo pelo luxo.",
        slides=[
            EduSlide("AVIAÇÃO EXECUTIVA", "Os destinos favoritos de quem voa de jato",
                     image_query="private jet luxury apron"),
            EduSlide("ASPEN, EUA", "Estação de esqui badalada, pista traiçoeira",
                     image_query="aspen ski resort snow luxury"),
            EduSlide("MÔNACO", "Chega-se de helicóptero a partir de Nice",
                     image_query="monaco yacht harbor"),
            EduSlide("IBIZA, ESPANHA", "Pico de voos executivos no verão europeu",
                     image_query="ibiza beach summer party"),
            EduSlide("DUBAI", "Hub de luxo com terminal dedicado a jatos",
                     image_query="dubai skyline luxury"),
            EduSlide("O QUE TEM EM COMUM", "Fácil acesso, exclusividade e discrição",
                     image_query="private airstrip desert"),
        ],
    ),
    Topic(
        slug="rotas_exoticas_comerciais", kind="edu_destinations",
        hashtags="#AvisoAereo #Destinos #Curiosidade #Aviação",
        caption_summary="Existem rotas comerciais que sobrevoam o Himalaia perto do Everest, cruzam o "
                         "Pacífico Sul em mais de 15 horas sem escala e passam por geleiras da Groenlândia "
                         "— trechos que valem a pena pesquisar o lado certo da janela antes de voar.",
        slides=[
            EduSlide("CURIOSIDADE", "As rotas comerciais mais incríveis do mundo",
                     image_query="airplane flying scenic landscape"),
            EduSlide("SOBRE O HIMALAIA", "Voos que passam perto do Everest",
                     image_query="everest snow mountain peak"),
            EduSlide("PACÍFICO SUL", "Trechos de mais de 15 horas sem escala",
                     image_query="ocean view airplane window"),
            EduSlide("GROENLÂNDIA", "Sobrevoo de geleiras em rota regular",
                     image_query="glacier ice blue aerial"),
            EduSlide("ILHAS GREGAS", "Pousos curtos entre arquipélagos",
                     image_query="greek island blue sea"),
            EduSlide("DICA", "Peça janela do lado certo — pesquise antes de voar",
                     image_query="airplane window clouds view"),
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
                     image_query="pilot uniform airport"),
            EduSlide("O CAMINHO", "Escola de aviação civil homologada pela ANAC",
                     image_query="aviation school training"),
            EduSlide("HORAS DE VOO", "Muitas horas acumuladas até evoluir de nível",
                     image_query="small training airplane"),
            EduSlide("PRIMEIROS PASSOS", "Instrutor, aviação executiva ou de carga",
                     image_query="cargo airplane runway"),
            EduSlide("ATÉ A GRANDE COMPANHIA", "Um caminho que costuma levar anos",
                     image_query="commercial airplane apron"),
            EduSlide("OPORTUNIDADE FORA", "EUA e Oriente Médio têm escassez de pilotos",
                     image_query="international airport flights"),
            EduSlide("NA PRÁTICA", "Boa parte revalida a licença no país de destino",
                     image_query="aviation license documents"),
            EduSlide("ONDE PROCURAR VAGAS", "LinkedIn, JSfirm e o site de cada companhia",
                     "Ainda não achamos uma fonte de vaga real de piloto pra puxar aqui automaticamente.",
                     "computer job search laptop"),
        ],
    ),
    Topic(
        slug="carreira_comissario_mecanico", kind="edu_careers",
        hashtags="#AvisoAereo #ComissárioDeVoo #MecânicoDeAeronaves #MercadoDeTrabalho",
        caption_summary="Comissário exige o CCF, curso homologado pela ANAC, com inglês fluente pesando "
                         "na seleção. Mecânico de aeronaves passa por curso técnico e licenças por tipo "
                         "de aeronave — área com demanda global relativamente estável.",
        job_categories=["flight_attendant", "mechanic"],  # ver jobs.py — acrescenta vaga real ao vivo
        slides=[
            EduSlide("MERCADO DE TRABALHO", "Comissário ou mecânico: como entrar na área",
                     image_query="flight attendant airplane cabin"),
            EduSlide("COMISSÁRIO DE VOO", "Exige curso específico homologado pela ANAC",
                     "O CCF — Curso de Formação de Comissários.", "flight attendant training"),
            EduSlide("INGLÊS PESA MUITO", "Fluência conta ponto forte na seleção",
                     image_query="job interview office"),
            EduSlide("DEMANDA VARIA", "Cresce e encolhe com a abertura de rotas novas",
                     image_query="new airplane route"),
            EduSlide("MECÂNICO DE AERONAVES", "Curso técnico e depois licença por tipo de avião",
                     image_query="aircraft mechanic tools"),
            EduSlide("DEMANDA GLOBAL ESTÁVEL", "Todo avião no mundo precisa de manutenção certificada",
                     image_query="aircraft maintenance hangar"),
            EduSlide("NA PRÁTICA", "Área técnica com portas abertas em vários países",
                     image_query="international airport work"),
        ],
    ),
]


_JOB_CATEGORY_LABEL = {"mechanic": "MECÂNICO", "flight_attendant": "COMISSÁRIO"}
_JOB_CATEGORY_IMAGE_QUERY = {
    "mechanic": "mecânico avião ferramenta trabalho",
    "flight_attendant": "comissário bordo uniforme trabalho",
}


def _job_slide_and_caption_line(category: str) -> tuple:
    """Busca 1 vaga real (jobs.fetch_real_job) e devolve (SlideSpec, linha_de_legenda)
    — ou (None, None) se não achar nenhuma agora (feed fora do ar, categoria vazia
    etc.). Nunca levanta exceção: uma vaga a menos não pode derrubar o post inteiro."""
    job = fetch_real_job(category)
    if job is None:
        return None, None
    label = _JOB_CATEGORY_LABEL.get(category, "VAGA")
    subtitle = " — ".join(p for p in [job.get("company"), job.get("location")] if p) or None
    slide = SlideSpec(
        kicker_text=f"VAGA REAL · {label}",
        title=job["title"][:70],
        subtitle=subtitle,
        image_query=_JOB_CATEGORY_IMAGE_QUERY.get(category, "aviação trabalho oportunidade"),
    )
    caption_line = f"• {label.capitalize()}: {job['title']}" + (f" ({subtitle})" if subtitle else "")
    if job.get("link"):
        caption_line += f" — {job['link']}"
    return slide, caption_line


def build_fallback_post(topic: Topic) -> PostContent:
    """Monta o PostContent de um tópico educativo — carrossel de 6-7 slides curtos
    (ver Topic.slides), todos no mesmo molde visual dos posts de alerta (regra
    fixa 2026-08-27), com severity="informativo" (cor azul, ver slide.py) pra
    nunca ser confundido com um aviso de verdade.

    Quando `topic.job_categories` não está vazio, busca vaga real e recente pra
    cada categoria (jobs.fetch_real_job) e acrescenta 1 slide por vaga encontrada
    no fim do carrossel, com o link real na legenda (pedido do usuário,
    2026-08-27: "sempre que possível anunciando vagas de trabalho... reais")."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    slides = [
        SlideSpec(kicker_text=s.kicker_text, title=s.title, subtitle=s.subtitle, image_query=s.image_query)
        for s in topic.slides
    ]

    job_caption_lines = []
    for category in topic.job_categories:
        slide, caption_line = _job_slide_and_caption_line(category)
        if slide is not None:
            slides.append(slide)
            job_caption_lines.append(caption_line)

    caption_lines = [
        f"✈️ {topic.slides[0].title}",
        "",
        topic.caption_summary,
        "",
        "A AvisoAereo publica atualizações de aeroportos brasileiros direto das fontes oficiais do "
        "DECEA (REDEMET/AISWEB). Sem nenhum aviso ativo relevante agora, aproveitamos pra trazer "
        "essa curiosidade.",
    ]
    if job_caption_lines:
        caption_lines += [
            "",
            "🔎 Vaga real aberta agora (oportunidade internacional, fora do Brasil):",
            *job_caption_lines,
        ]
    caption_lines += ["", topic.hashtags]

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
