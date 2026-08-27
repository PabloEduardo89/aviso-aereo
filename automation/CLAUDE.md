# Automação @avisoaereo — padrão de design dos posts

Este arquivo documenta o padrão visual que os slides gerados (`slide.py`,
`content.py`, `backgrounds.py`) devem perseguir. Toda vez que este projeto for
retomado — nesta conversa ou em outra — a ideia é que a qualidade visual
continue subindo em direção a essa referência, em vez de recomeçar do zero.

## Redesign completo do carrossel — slide único + CTA (2026-08-27)

**Supera a seção "Referência de estilo: feed do G1" abaixo** (mantida por
histórico) — o usuário pediu pra acabar de vez com a distinção entre slide
CAPA (foto) e slide EXPLICATIVO (fundo branco/serifado): agora **todo** slide
do carrossel, sem exceção, segue o molde fotográfico (era só a capa antes).
Motivo do pedido: "pouca escrita, imagens reais, excelente edição" — o texto
corrido do explicativo antigo foi condensado em títulos curtos, um por slide.

- **Um único renderizador** (`slide.render_photo_slide`) pra todo slide —
  substituiu `render_capa_slide`/`render_explicativo_slide`, que não existem
  mais.
- **Selo `@avisoaereo` bem mais em destaque**: centralizado no topo, fundo
  sólido âmbar (`COLOR_BRAND`, mesmo tom do app principal), em vez do badge
  pequeno/semitransparente de antes — presente em TODO slide, inclusive os
  que antes não tinham selo nenhum (os explicativos).
- **Título curto, no máximo 2 linhas** (`_fit_title(..., max_lines=2)`) — os
  templates de título de capa (`_TITLE_TEMPLATES` em content.py) foram
  encurtados de propósito pra caberem nesse limite mesmo em fonte pequena.
- **Cada slide tem SUA PRÓPRIA foto**, buscada no Pexels pela palavra-chave
  daquele slide específico (`SlideSpec.image_query`, ver `content.py`) — regra
  do usuário: "a palavra-chave principal de algum escrito em um slide precisa
  trazer uma imagem que corresponda aquilo", pra nunca repetir imagem dentro
  do carrossel nem entre posts. Exceção: o 1º slide de um post de ALERTA REAL
  (`image_query=None`) continua usando a foto "oficial" do aeroporto (curada/
  satélite/ilustração, ver backgrounds.get_background_for_post) — é a mais
  confiável/específica que existe; só os demais slides (e TODOS os slides de
  post educativo, que não têm aeroporto específico) usam Pexels.
- **Slide de Call-to-Action obrigatório, sempre por último**
  (`slide.render_cta_slide`), em TODO carrossel — real ou educativo. Nunca faz
  parte da lista `PostContent.slides` que quem monta o conteúdo escreve;
  `render_post_slides` acrescenta esse slide sozinho no final, sempre.
- **Posts de alerta real**: 2 slides de conteúdo (manchete + "o que isso
  significa") + 1 opcional quando há data de término real (só NOTAM, nunca
  METAR — ver `duracao_slide` em `content._build_one_post`) + CTA = 3 ou 4
  slides no total.
- **Posts educativos (fallback)**: 6-7 slides de conteúdo (a escolha entre 6
  e 7 é de quem escreve o `Topic` em `fallback_content.py`, não uma regra
  fixa) + CTA = 7 ou 8 no total. Ver seção "Fallback educativo" mais abaixo.
- `PEXELS_API_KEY` — chave gratuita (pexels.com/api, sem exigir crédito do
  fotógrafo), configurada como secret do GitHub e no `.env` local. Sem ela,
  `backgrounds.fetch_pexels_photo` devolve `None` e quem chamou cai pro fundo
  "oficial" do post — nunca quebra a geração do slide, só perde a variedade.

## Só avisos "quentes" viram post (regra atualizada 2026-08-27)

O usuário revisou o feed e achou muitos avisos "mornos" (restrição real mas
geralmente contornável — visibilidade/teto marginal, vento forte mas não
severo, auxílio de navegação fora do ar) — pediu pra só postar risco real de
atraso/cancelamento/desvio. `rules.HIGH_SEVERITY_KINDS` (antes vivia como
`content._HIGH_SEVERITY_KINDS`, só definia a COR do post) agora também
filtra, na origem (`rules.evaluate_airport`), quais `Reason`/`NotamHit`
sequer chegam a existir na `AirportEvaluation` — motivo fora desse conjunto
nunca gera post sozinho, mesmo que apareça junto de um motivo quente na
mesma leitura de METAR (nesse caso, só o motivo quente conta pro post; o
morno fica de fora das reasons desde a origem). Na prática, `severity` de
todo post real agora é sempre `"alto"` — `"atenção"` ficou só como valor
teoricamente possível, não mais alcançável com as regras atuais.

## Referência de estilo: feed do G1 no Instagram (parcialmente superada acima)

O padrão escolhido (aprovado pelo usuário em 2026-08-23) é inspirado no card
de notícia do G1 no Instagram — a foto real de fundo, o degradê escuro na
base, a etiqueta colorida (kicker) e o título em frase normal (não CAIXA
ALTA) continuam valendo, exatamente como descritos abaixo, e agora se aplicam
a TODO slide, não só à capa (ver seção acima):

- **Foto real de fundo**, ocupando o slide inteiro (não ilustração/ícone,
  quando há alternativa real disponível) — é o que dá credibilidade: "as
  pessoas acreditam mais no post quando vêem coisas que reconhecem do dia a
  dia" (aeroporto da própria cidade, não um desenho genérico).
- **Degradê escuro na base** da foto (não mais um bloco preto sólido) —
  garante legibilidade do título sem esconder a foto.
- **Etiqueta colorida curta (kicker)** acima do título — no 1º slide de um
  alerta real mostra `ICAO · UF`; nos demais, uma categoria curta própria do
  slide (ex.: "O QUE ISSO SIGNIFICA", "PREVISÃO"). A cor da etiqueta segue a
  severidade (vermelho = alto impacto; azul = conteúdo educativo).
- **Título em frase normal** (só a primeira letra maiúscula), não em CAIXA
  ALTA — bold, branco, no máximo 2 linhas (ver seção acima).
- Quando a foto de fundo exige/permite crédito, uma linha pequena
  "Foto: {autor}" aparece no rodapé do slide.

**Regra fixa (2026-08-23, contagem de slides atualizada em 2026-08-27): todo
post é carrossel, sempre com no mínimo 2 slides de conteúdo + o CTA final**
— ver contagem exata por tipo de post na seção acima.

## Regra fixa: sempre explicar o impacto prático (aprovado 2026-08-23)

Todo post precisa deixar claro **o que aquilo significa na prática pra vida de
quem viaja** — não basta o fato técnico ("VOR/DME fora de serviço"), tem que
dar pra uma pessoa sem nenhum conhecimento de aviação entender se isso é
"posso ter meu voo atrasado" ou "não afeta em nada o passageiro comum". Essa
explicação (`_IMPACT_TEXT` em `content.py`, uma por `headline_kind`) tem que
aparecer em pelo menos um destes dois lugares — os dois é ainda melhor:
- **na legenda do post** (já é automático — ver `caption_lines` em
  `build_post_content`, linha "O que isso significa na prática: ...");
- **em um slide extra no carrossel** (o EXPLICATIVO já carrega esse texto no
  bloco "O QUE ISSO SIGNIFICA:" quando é gerado).

Nunca publicar um post só com o fato técnico cru, sem essa camada de
explicação em linguagem simples.

### Título de capa variado, sorteado por template (atualizado 2026-08-24)

**Superado pela regra abaixo** — ver histórico: a versão anterior desta seção
fixava `cover_title` sempre no formato `"Aeroporto de {cidade}: {problema}
pode atrasar ou alterar voos"`. O usuário revisou o feed real, viu um "título
padrão" repetido demais, e pediu criatividade: `aeroporto`, `cancelamentos`,
`atrasos`, `alteração de voos` etc. são **exemplos** de palavra-chave pra
gerar urgência, não uma regra obrigatória em todo post — só "aeroporto" pode
seguir aparecendo com mais frequência que as outras, mas também não em todos.

`_pick_cover_title` (content.py) sorteia (`random.choice`) um template de
`_TITLE_TEMPLATES["alto"]` ou `_TITLE_TEMPLATES["atenção"]` (por severidade)
a cada post — variam a estrutura da frase (às vezes começa pela cidade, às
vezes pelo problema, às vezes é pergunta/chamada direta) em vez de repetir
sempre "Aeroporto de {cidade}: ...". Pra adicionar variedade nova, só
acrescentar um template na lista certa (usa `{city}`, `{problema}` e
`{Problema}` — versão com primeira letra maiúscula, pra frases que começam
pelo problema).

### `_IMPACT_TEXT` com ênfase em VOO (aplicado 2026-08-24)

Os textos de `_IMPACT_TEXT` (content.py, um por `headline_kind`) foram
reescritos pra deixar explícito que é **o voo do passageiro** que
atrasa/desvia (não só o fato técnico genérico), e "desvio" sempre é explicado
como pousar numa **pista ou aeroporto diferente** do planejado. Ao adicionar
um `headline_kind` novo, manter essa linha — "o seu voo pode..." em vez de
"há chance de...".

### Slide explicativo: contextualização + fonte DECEA (aplicado 2026-08-24; SUPERADO 2026-08-27)

**Superado pelo redesign do carrossel (ver seção no topo do arquivo)** — o
slide EXPLICATIVO e a classe `ExplicativoContent` não existem mais, então o
parágrafo de contexto descrito abaixo também não existe mais como slide.
A menção à fonte oficial (DECEA/REDEMET/AISWEB) permanece na legenda dos
posts de alerta real (`content._build_one_post`), mas ficou de fora da
legenda do educativo na reescrita de `fallback_content.py` — vale considerar
adicionar de volta ali se fizer falta pra credibilidade da conta.

~~O slide EXPLICATIVO agora abre com um parágrafo de contexto~~
~~(`ExplicativoContent.contexto`, renderizado em `slide.py` logo após a linha~~
~~divisória, antes de "O QUE ACONTECEU") que situa a notícia e deixa claro que~~
~~a conta traz dados das fontes oficiais do DECEA (REDEMET/AISWEB) — pedido do~~
~~usuário depois de ver o carrossel ir direto pros blocos técnicos sem~~
~~contextualizar nada antes.~~

### Fontes empacotadas no repo, não do sistema (correção de bug, 2026-08-24)

**Incidente**: o primeiro post gerado pela automação na nuvem (GitHub
Actions, runner Ubuntu) saiu com os acentos quebrados ("DURAÇÃO" virou
"DURA▯▯O", "aeródromo" virou "aer▯dromo" etc.). Causa: `slide.py` apontava
`FONT_DIR` pra `C:\Windows\Fonts`, que só existe no PC Windows do usuário —
no runner Linux o carregamento falhava silenciosamente (`try/except OSError`)
e caía no fallback bitmap do Pillow (`ImageFont.load_default`), que não sabe
desenhar caracteres acentuados.

**Correção**: fontes de verdade (SIL Open Font License) agora ficam
versionadas em `automation/assets/fonts/` — `Inter[opsz,wght].ttf` (sans,
CAPA), `Lora[wght].ttf` (serif, EXPLICATIVO) e `RobotoMono[wght].ttf` (mono,
card de registro bruto). São fontes variáveis; `slide.py._font(role, size)`
carrega o arquivo certo e ajusta o eixo de peso (`set_variation_by_axes`) por
"papel" (`sans`, `sans_bold`, `serif`, `serif_bold`, `mono`) em vez de um
arquivo por peso. Isso funciona identicamente local (Windows) e na automação
(Linux) — não depende mais de fonte nenhuma do sistema operacional. O
`try/except` que mascarava esse tipo de falha foi removido de propósito: se o
arquivo de fonte sumir do repo, agora quebra alto (erro claro), em vez de
degradar silenciosamente pra um visual quebrado como aconteceu aqui.
Não voltar a apontar fontes pra um caminho do sistema operacional.

## Biblioteca de fotos reais por aeroporto

- `assets/photos/<ICAO>.jpg` — foto curada do aeroporto, sem nenhum
  tratamento de cor (usada em cor natural, ao contrário do satélite/
  ilustração, que levam duotone vermelho).
- `assets/photos/manifest.json` — um registro por ICAO com `source_page`,
  `source_file`, `author`, `license`, `date_taken`. Sempre preencher ao
  adicionar uma foto nova.
- Prioridade de fundo (`backgrounds.get_background_for_post`):
  1. foto curada do aeroporto (se existir em `assets/photos/`)
  2. imagem de satélite real da REDEMET, só pra avisos de origem
     meteorológica (visibilidade, vento, trovoada etc.)
  3. ilustração geométrica simples desenhada por código (pista/torre/antena),
     último recurso quando não há foto curada e o motivo é operacional
     (pista/torre/aux. navegação)

Status atual (2026-08-23): **28 de 30 aeroportos têm foto curada** — SBEG
(Manaus), SBGR (Guarulhos), SBSP (Congonhas), SBCF (Confins/BH), SBRJ (Santos
Dumont), SBGL (Galeão), SBBR (Brasília), SBPA (Porto Alegre), SBBE (Belém),
SBSV (Salvador), SBCY (Cuiabá), SBFL (Florianópolis), SBGO (Goiânia), SBVT
(Vitória), SBRF (Recife), SBFZ (Fortaleza), SBCG (Campo Grande), SBJP (João
Pessoa), SBSG (Natal — atenção: é o Aeroporto Aluízio Alves/São Gonçalo do
Amarante, NÃO o antigo Augusto Severo, desativado p/ civil em 2014), SBAR
(Aracaju), SBKP (Viracopos/Campinas), SBPJ (Palmas), SBTE (Teresina), SBMO
(Maceió), SBSL (São Luís), SBPV (Porto Velho), SBBV (Boa Vista), SBRB (Rio
Branco).
Faltam só 2: **SBMQ (Macapá)** — o terminal antigo foi demolido/substituído
em 2019 e só achei fotos do prédio antigo, que não existe mais, então pulei
de propósito (evitar mostrar um lugar que não é mais real); **SBCT
(Curitiba)** — tentado 3x, as únicas fotos encontradas são de 2006-2009 ou
distantes/pouco reconhecíveis. Ambos precisam de uma nova tentativa de busca
mais pra frente (talvez fontes além do Wikimedia Commons).
Ir preenchendo os outros ao longo do tempo é o principal jeito de "melhorar o
post" — quanto mais aeroportos tiverem foto real, menos posts caem no
fallback genérico/ilustração. Busca ampliada além do Wikimedia Commons quando
fizer sentido (o usuário pediu explicitamente pra não restringir a fontes só
brasileiras) — mas o Commons continua sendo a fonte mais confiável pra achar
fotos com licença livre e verificável.

Biblioteca genérica (`assets/photos/generic/<categoria>/`, ver seção abaixo):
`aircraft` e `terminal` já têm 1 foto cada; `queue` (fila de check-in com
pessoas) ainda está vazia — não achei rapidamente uma foto brasileira boa,
livre de direitos e sem logo de companhia extinta. Prioridade pra próxima
sessão de curadoria.

### Cuidado com fotos muito panorâmicas (lição aprendida 2026-08-23)

`backgrounds.cover_resize` faz um corte central simples (estica pela altura e
corta as bordas laterais) — em fotos com proporção MUITO larga (ex.: um
panorama 3861×1059, quase 4:1), isso corta fora a parte que mais importa (o
nome do aeroporto ficou de fora no primeiro corte da foto de Teresina/SBTE).
Antes de salvar uma foto assim em `assets/photos/`, recorte manualmente uma
região que mantenha o elemento identificador (nome/torre) centralizado, numa
proporção mais próxima de retrato/quadrada, e só depois deixe o
`cover_resize` fazer o ajuste fino pro tamanho do slide.

### Critério pra escolher uma foto nova

Buscar na internet como um todo (inclusive sites de notícia), com fallback pro
Wikimedia Commons se nada bom for encontrado. Ao escolher, evitar:
- fotos com **logo de companhia aérea desatualizado/extinto** em destaque
  (ex.: TAM, Varig — empresas que não existem mais);
- fotos claramente datadas (obras temporárias, aeronaves de décadas atrás);
- marca d'água de banco de imagens ou crédito de fotógrafo sobreposto à
  própria foto (diferente de placas/letreiros do próprio aeroporto, que são
  parte real do lugar e podem ficar).

Sempre registrar o crédito/licença no manifest — mesmo quando a licença não
exige atribuição, é bom hábito manter o registro de onde a foto veio.

### Variedade de foto por tipo de aviso (aprovado 2026-08-23)

Não é só fachada de aeroporto — o usuário pediu variedade, buscando o tipo de
foto mais pertinente ao que o aviso está dizendo:

- **Fachada/torre do aeroporto específico** (o que já temos pra SBEG) — bom
  padrão geral, principalmente pra auxílio de navegação e avisos meteorológicos.
- **Saguão/terminal por dentro, com pessoas de verdade circulando** — reforça
  a identificação ("cada um que já esteve num aeroporto reconhece aquilo").
- **Aeronave em pista/pátio, de qualquer companhia** (sem viés de marca — não
  precisa ser da companhia que o passageiro usa) — boa opção genérica quando
  não há foto específica do aeroporto.
- **Fila em guichê de check-in/balcão** — a mais pertinente especificamente
  pra avisos que tendem a gerar atraso/cancelamento (pista fechada, torre
  fechada) — reforça visualmente a consequência prática do aviso.

Essas três últimas categorias não precisam ser do aeroporto específico (fotos
genéricas servem, guardadas por categoria, não por ICAO) — usar como camada
intermediária de fallback: quando não há foto curada do aeroporto em questão,
prefira uma foto genérica da categoria mais pertinente ao `headline_kind` (fila
pra pista/torre fechada, aeronave pra clima/aux. navegação, saguão como
alternativa geral) antes de cair no satélite/ilustração.

## Arquivos do pipeline de design (etapa 3)

- `content.py` — traduz o resultado da etapa 2 (rules.py) em português
  natural: título de capa, kicker, texto do slide explicativo, legenda do
  Instagram.
- `backgrounds.py` — fundo do slide CAPA (foto curada / satélite / ilustração
  + duotone).
- `slide.py` — desenho dos slides (CAPA e EXPLICATIVO) com Pillow.

## Etapa 4 (publicação)

Dois modos, pra dois momentos diferentes:

- **Manual/teste** (`publish.py`): fluxo em dois passos — `--stage` (monta,
  hospeda no GitHub, cria o container) e depois `--go <creation_id>` (publica
  de fato). Use isso quando quiser testar/revisar um post específico à mão.
- **Automático** (`run_cycle.py` + `.github/workflows/post-avisos.yml`):
  publicação sem pausa manual, decidido pelo usuário em 2026-08-23 ("não
  quero ter que autorizar isso"). Roda sozinho no GitHub Actions, de hora em
  hora. Ver detalhes na seção seguinte.

### Automação total (regra fixa, decidido 2026-08-23)

- **Um post por notícia relevante, não um post por aeroporto.** `build_post_content`
  (content.py) devolve uma LISTA de posts, não um post só — um mesmo aeroporto só
  gera mais de um post quando existem motivos DISTINTOS e não relacionados ao
  mesmo tempo (ex.: uma pista fechada e, à parte, uma trovoada); cada NOTAM
  relevante é sua própria notícia, e todas as condições de METAR do momento
  juntas contam como uma notícia só (é uma situação meteorológica, não várias).
  Isso não é o padrão comum — a maioria dos aeroportos não vai gerar post
  nenhum na maior parte do tempo, e quando gerar, normalmente é só um.
- **Nunca simultâneo — sempre espaçado.** Mesmo quando há mais de um post
  relevante pra sair na mesma execução (do mesmo aeroporto ou de aeroportos
  diferentes), eles NÃO saem juntos: `run_cycle.py` espera
  `MIN_INTERVAL_SECONDS` (6 minutos) entre uma publicação e a próxima, dentro
  da mesma execução. Importante: o usuário corrigiu explicitamente esse ponto
  em 2026-08-23 — não implementar publicação em lote/paralela de novo.
- **Onde roda**: GitHub Actions (nuvem), não depende do PC do usuário ligado.
  Workflow em `.github/workflows/post-avisos.yml`, cron `'0 * * * *'` (de
  hora em hora) + `workflow_dispatch` pra rodar manualmente pela aba Actions.
- **Deduplicação** (`state.py`, `state/posted.json`, comitado de volta no
  repo a cada execução): cada post tem um `dedup_key` (`PostContent.dedup_key`
  em content.py) — pra NOTAM é o id do próprio NOTAM (não repete enquanto o
  mesmo NOTAM segue em vigor, por mais dias que dure); pra clima é
  `icao|weather|kind|data-de-hoje-em-Brasília` (uma condição de tempo que
  continua no dia seguinte conta como "nova" — atualização diária, não
  repetição a cada hora). **Sem isso, um NOTAM de dias viraria post repetido
  a cada execução.**
- **Limite de ritmo** (`run_cycle.py`, `MAX_POSTS_PER_RUN = 3`): no máximo 3
  posts NOVOS por execução — o resto sai nas próximas execuções, nunca se
  perde. Existe pra não parecer comportamento de bot/spam pra Meta (a API do
  Instagram tem um teto de ~25 posts/24h por conta, e rajadas de posts
  parecidos em pouco tempo são o tipo de padrão que sistemas antispam
  costumam sinalizar) — combinado com o espaçamento de 6 min acima.
- **Lançamento** (2026-08-23): o registro (`state/posted.json`) foi
  "primado" com todas as condições ativas no dia do lançamento (30 notícias
  distintas nos ~28 aeroportos com algo ativo) — incluindo os 2 posts de
  teste manuais já publicados (Manaus/SBEG NOTAM 12308060, Salvador/SBSV
  NOTAM 12399153, com o media_id real) e as demais marcadas como vistas sem
  post real (`media_id: "skipped_at_launch_no_post"`) — pra automação
  começar reagindo só a coisas NOVAS a partir do lançamento, sem rajada
  inicial. Isso foi uma escolha pontual do lançamento, não repetir esse
  "priming" depois — a partir daqui o registro só cresce organicamente. Se o
  formato do `dedup_key` mudar de novo no futuro, o registro precisa ser
  refeito com a chave nova (senão perde efeito e volta a dar rajada).

### Fallback educativo (atualizado 2026-08-24 — agora obrigatório, não condicional)

**Superado em parte — ver histórico**: até 2026-08-24 esse post só saía
quando NENHUM aeroporto monitorado tinha aviso real ativo na execução (senão
a conta ficava muda naquele ciclo). O usuário pediu pra mudar: agora o post
educativo tem ritmo **próprio e garantido**, independente de haver posts reais
na mesma execução ou não — não é mais "só quando não há nada real pra
postar".

- **Obrigatório sempre que passar `MIN_FALLBACK_INTERVAL_SECONDS` (6h) sem
  post REAL** (regra atualizada 2026-08-27 — antes eram 4h fixas contadas
  desde o último EDUCATIVO, disparando sempre nessa cadência mesmo em dia
  cheio de avisos reais; agora é contado desde o último post real,
  `_meta.last_real_post_at` em `state/posted.json` — um dia cheio de avisos
  reais não força educativo nenhum, mas uma seca de notícia real mantém a
  conta ativa). `run_cycle.run()` chama `maybe_build_fallback` sempre (não só
  quando `candidates` está vazio) e, se for hora, insere o educativo na
  FRENTE da lista de candidatos daquela execução (garante que ele entra
  dentro do `MAX_POSTS_PER_RUN`).
- **Carrossel de 6-7 slides de conteúdo + CTA** (regra atualizada 2026-08-27
  — supera a versão de 3 slides de 2026-08-24, ver histórico abaixo): cada
  `Topic` (fallback_content.py) traz uma lista `slides: list[EduSlide]` com 6
  ou 7 itens (a escolha entre 6 e 7 é de quem escreve o tópico) — cada
  `EduSlide` já é, sozinho, um slide completo no molde único do carrossel
  (kicker + título curto + palavra-chave própria de imagem, ver seção
  "Redesign completo do carrossel" no topo deste arquivo). `slide.py` não
  tem mais um caso especial pra fallback — o mesmo `render_post_slides` que
  atende post real atende o educativo, só que com uma lista mais longa de
  slides.
  ~~Carrossel de 3 slides, não mais 2 (regra 2026-08-24, capa + 1 slide~~
  ~~explicativo por bloco de conteúdo, via `PostContent.explicativo_slides`~~
  ~~e `ExplicativoContent`) — campo e classe não existem mais.~~
- **Conteúdo**: rotação fixa de tópicos (`fallback_content.TOPICS`) nas 6
  categorias pedidas pelo usuário — regras/leis/regulamentos da aviação
  (geral e comercial), significado de códigos de aeroporto (IATA/ICAO,
  numeração de pista), o que são METAR e NOTAM, matrícula/rastreamento de
  aeronaves, curiosidades sobre aviação executiva (jatinhos — categorias,
  custo, instalações) e mercado de trabalho de aeronautas — piloto,
  comissário, mecânico de aeronaves — no Brasil e fora (adicionada
  2026-08-24). Passa por todos os tópicos em ordem antes de repetir
  qualquer um (`_meta.fallback_topic_index`).
- **Nunca é confundido com um alerta real**: `severity="informativo"` usa cor
  azul (`COLOR_ACCENT_INFO` em `slide.py`), diferente do vermelho/âmbar dos
  avisos de verdade — visualmente distinto de propósito.
- Se algum dia adicionar tópico novo, só acrescentar em `TOPICS` — a rotação
  e o dedup (`dedup_key = fallback|<slug>|<data>`) já lidam com isso sozinhos.

### Segredos necessários no GitHub (Settings → Secrets and variables → Actions)

`INSTAGRAM_TOKEN`, `REDEMET_API_KEY`, `AISWEB_API_KEY`, `AISWEB_API_PASS`,
`PEXELS_API_KEY` (adicionado 2026-08-27 — busca de foto por palavra-chave em
cada slide, ver backgrounds.fetch_pexels_photo) — os mesmos valores do `.env`
local. `gh` CLI foi instalado nesta máquina em
2026-08-24 (`winget install --id GitHub.cli`, autenticado como
PabloEduardo89) — dá pra usar `gh secret set NOME --repo
PabloEduardo89/aviso-aereo` direto do terminal a partir de agora, sem precisar
colar segredo em nenhum arquivo. **Cuidado ao digitar o nome do secret**: um
erro de digitação (`INTAGRAM_TOKEN` em vez de `INSTAGRAM_TOKEN`) foi a causa
raiz de todas as execuções agendadas falharem entre o lançamento (2026-08-23)
e a correção (2026-08-24) — o workflow lia a env var vazia e abortava. `gh
secret list --repo PabloEduardo89/aviso-aereo` é a forma rápida de conferir
os nomes exatos cadastrados.
