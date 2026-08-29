"""
Etapa 4 (parte 2) — ciclo totalmente automático, sem pausa manual: busca
dados de todos os aeroportos, filtra (rules.py), monta o(s) post(s)
(content.py + slide.py — um aeroporto pode gerar mais de um post quando há
motivos distintos e não relacionados, ex.: pista fechada + trovoada), e
publica direto no Instagram — só quando é uma condição NOVA (ver state.py).
Feito pra rodar sozinho, agendado, via .github/workflows/post-avisos.yml
(a cada hora).

Diferente de publish.py (--stage / --go), aqui não há revisão humana no meio
— é o modo "publicações automáticas" pedido pelo usuário em 2026-08-23, com a
deduplicação (state.py) fazendo o papel de não postar a mesma coisa 2x.

O fallback educativo (fallback_content.py) é OBRIGATÓRIO sempre que passar
MIN_FALLBACK_INTERVAL_SECONDS (6h) sem nenhum post INFORMATIVO REAL ter saído
— regra atualizada em 2026-08-27 (pedido do usuário: "caso não tenha nenhum
informativo real do METAR, dentro de um período de 6 horas, continue com os
posts educativos"). Diferente da versão anterior (relógio fixo de 4h desde o
último educativo, sempre disparando de hora em hora independente de haver
notícia real ou não), agora o relógio só é resetado por um post REAL — se a
seca de notícias reais continuar, o educativo pode voltar a sair na execução
seguinte, passando pro próximo tópico da rotação a cada vez.
"""
import os
import sys
import time
from datetime import datetime, timezone

import requests

import format_state
import style
from airports import AIRPORTS
from content import build_post_content
from fallback_content import TOPICS as FALLBACK_TOPICS
from fallback_content import build_fallback_post
from fetch_data import FetchError, fetch_metar, fetch_notam
from publish import create_container, get_publishing_credentials, host_images_on_github, publish_container
from rules import evaluate_airport
from slide import render_post_slides, render_post_slides_variation
from state import get_meta, is_posted, load_state, mark_posted, save_state, set_meta

# limite conservador de posts novos por execução (agendada de hora em hora) —
# evita rajada de publicações que pareça comportamento de bot pra Meta/Instagram,
# mesmo em dias com muitas condições novas ao mesmo tempo. O que passar do
# limite sai nas próximas execuções, nunca se perde. Aprovado 2026-08-23.
MAX_POSTS_PER_RUN = 3

# espaçamento mínimo entre publicações distintas dentro da MESMA execução —
# mesmo quando há mais de um motivo relevante e não relacionado pro mesmo (ou
# outro) aeroporto, os posts não saem juntos/ao mesmo tempo. Aprovado 2026-08-23.
MIN_INTERVAL_SECONDS = 360  # 6 minutos

# tempo máximo sem NENHUM post real antes do educativo virar obrigatório —
# regra atualizada 2026-08-27 (ver docstring do módulo). O relógio
# (`_meta.last_real_post_at`) só é resetado por um post real (nunca por um
# educativo) — 6h é mais folgado que os antigos 4h fixos, mas agora reage à
# seca de notícias de verdade em vez de disparar sempre na mesma cadência.
MIN_FALLBACK_INTERVAL_SECONDS = 6 * 3600  # 6 horas


PEXELS_PREFLIGHT_URL = "https://api.pexels.com/v1/search"


def preflight():
    """Barreira de sanidade antes de QUALQUER publicação: se a fonte de imagem
    por slide (Pexels) não estiver utilizável, ABORTA a execução com erro (o
    job do GitHub Actions falha; o heartbeat abre o issue = e-mail pro dono).

    Decidido em 2026-08-29: por semanas o carrossel saiu com a MESMA imagem
    repetida/espelhada porque o secret PEXELS_API_KEY estava vazio no Actions
    e `fetch_pexels_photo` degradava em silêncio (retornava None pra todo
    slide). Agora essa falha é barulhenta e para o pipeline em vez de publicar
    um post ruim."""
    key = (os.getenv("PEXELS_API_KEY") or "").strip()
    if not key:
        raise SystemExit(
            "PREFLIGHT FALHOU: PEXELS_API_KEY ausente/vazia. Sem ela, cada slide "
            "do carrossel cai na mesma imagem de fallback. Configure o secret "
            "(gh secret set PEXELS_API_KEY --repo PabloEduardo89/aviso-aereo) e "
            "rode de novo. Nada foi publicado."
        )
    try:
        resp = requests.get(
            PEXELS_PREFLIGHT_URL,
            headers={"Authorization": key},
            params={"query": "airport", "per_page": 1},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise SystemExit(f"PREFLIGHT FALHOU: Pexels inacessível ({exc}). Nada foi publicado.")
    if resp.status_code == 401:
        raise SystemExit(
            "PREFLIGHT FALHOU: PEXELS_API_KEY inválida (HTTP 401 do Pexels). "
            "Gere uma nova em pexels.com/api e atualize o secret. Nada foi publicado."
        )
    try:
        has_photos = bool(resp.json().get("photos"))
    except ValueError:
        has_photos = False
    if resp.status_code != 200 or not has_photos:
        raise SystemExit(
            f"PREFLIGHT FALHOU: Pexels respondeu HTTP {resp.status_code} sem fotos "
            "utilizáveis. Nada foi publicado."
        )
    print("[preflight] Pexels OK — chave válida e API respondendo.")


def collect_candidates(state: dict) -> list:
    """Busca dados de todos os aeroportos e devolve os posts (PostContent) que
    são relevantes agora e ainda não foram publicados (ver dedup_key/state.py)."""
    candidates = []
    for airport in AIRPORTS:
        icao = airport["code"]
        try:
            metar = fetch_metar(icao)
        except FetchError as err:
            print(f"[{icao}] erro ao buscar METAR: {err}")
            metar = None
        try:
            notams = fetch_notam(icao)
        except FetchError as err:
            print(f"[{icao}] erro ao buscar NOTAM: {err}")
            notams = []

        evaluation = evaluate_airport(icao, metar, notams)
        for post in build_post_content(icao, airport, metar, evaluation):
            if is_posted(state, post.dedup_key):
                continue
            candidates.append(post)
    return candidates


def maybe_build_fallback(state: dict, now: datetime) -> object | None:
    """Devolve 1 PostContent educativo (ver fallback_content.py) se já faz
    MIN_FALLBACK_INTERVAL_SECONDS (6h) sem NENHUM post sair — real ou
    educativo — regra corrigida em 2026-08-27 (segunda passada no dia):
    a primeira versão só olhava `_meta.last_real_post_at`, o que fazia o
    educativo disparar a CADA execução (de hora em hora) durante uma seca de
    notícia real, em vez de espaçado de 6 em 6h como pedido ("de 6 em 6 horas
    haverá um post educativo"). Agora o relógio usa o mais recente entre
    `last_real_post_at` e `last_fallback_at` — um post real OU um educativo,
    qualquer um dos dois, adia o próximo educativo por 6h. Devolve None se
    ainda não é hora — ou se nunca houve nenhum post (real nem educativo),
    considera que já é hora (evita nunca ligar o fallback num lançamento sem
    histórico)."""
    last_real = get_meta(state, "last_real_post_at")
    last_fallback = get_meta(state, "last_fallback_at")
    last_iso = max(filter(None, [last_real, last_fallback]), default=None)
    if last_iso is not None:
        elapsed = (now - datetime.fromisoformat(last_iso)).total_seconds()
        if elapsed < MIN_FALLBACK_INTERVAL_SECONDS:
            return None

    index = get_meta(state, "fallback_topic_index", 0) % len(FALLBACK_TOPICS)
    set_meta(state, "fallback_topic_index", (index + 1) % len(FALLBACK_TOPICS))
    return build_fallback_post(FALLBACK_TOPICS[index])


def run():
    preflight()
    state = load_state()
    fmt_state = format_state.load()
    now = datetime.now(timezone.utc)
    candidates = collect_candidates(state)

    # post educativo é obrigatório quando passou MIN_FALLBACK_INTERVAL_SECONDS
    # (6h) sem post real (ver maybe_build_fallback) — quando entra, vai sempre
    # na frente da lista pra garantir que cabe dentro do MAX_POSTS_PER_RUN; o
    # resto dos candidatos reais (se sobrar espaço) sai junto ou fica pra
    # próxima execução.
    fallback = maybe_build_fallback(state, now)
    if fallback is not None:
        print(f"Post educativo obrigatório (a cada {MIN_FALLBACK_INTERVAL_SECONDS // 3600}h) "
              f"incluído nesta execução ({fallback.dedup_key}).")
        candidates = [fallback] + candidates

    if not candidates:
        print("Nenhuma condição nova pra postar nesta execução (nem post educativo — ainda não é hora).")
        return

    to_publish = candidates[:MAX_POSTS_PER_RUN]
    if len(candidates) > MAX_POSTS_PER_RUN:
        print(f"{len(candidates)} condição(ões) nova(s) encontrada(s) — publicando {MAX_POSTS_PER_RUN} agora "
              f"(espaçadas), o resto fica pra próxima execução.")

    _, page_token, ig_user_id = get_publishing_credentials()

    posted_count = 0
    for i, post in enumerate(to_publish):
        if i > 0:
            print(f"Aguardando {MIN_INTERVAL_SECONDS}s antes do próximo post (espaçamento entre publicações)...")
            time.sleep(MIN_INTERVAL_SECONDS)

        # variação de molde só entra pra posts REAIS (dados de METAR/NOTAM) —
        # o educativo de fallback continua sempre no molde único fotográfico.
        # style.next_mold já aplica as regras pedidas em 2026-08-28: relevância
        # alta (severity_tier "alta" — pista/torre fechada, tesoura de vento)
        # é SEMPRE moderno, sem exceção; fora isso, uma variação só sai depois
        # de MIN_VARIATION_INTERVAL_SECONDS desde a última — moderno continua
        # sendo o carro-chefe, a grande maioria do feed.
        is_real = post.icao != "_FALLBACK"
        mold = style.next_mold(post.headline_kind, now, fmt_state) if is_real else "moderno"

        print(f"[{post.icao}] publicando ({post.dedup_key}) — molde {mold}")
        try:
            if mold != "moderno":
                paths = render_post_slides_variation(post, mold, fmt_state)
                caption = style.apply_caption_opening(post, fmt_state)
            else:
                paths = render_post_slides(post)
                caption = post.caption
            image_urls = host_images_on_github(paths, post.icao)
            creation_id = create_container(ig_user_id, page_token, image_urls, caption)
            media_id = publish_container(ig_user_id, page_token, creation_id)
        except Exception as err:
            print(f"[{post.icao}] ERRO ao publicar: {err}")
            continue

        posted_at = datetime.now(timezone.utc).isoformat()
        mark_posted(state, post.dedup_key, media_id, posted_at)
        set_meta(state, "last_post_at", posted_at)
        if post.icao == "_FALLBACK":
            set_meta(state, "last_fallback_at", posted_at)  # espaça o PRÓXIMO educativo por 6h
        else:
            set_meta(state, "last_real_post_at", posted_at)  # espaça o PRÓXIMO educativo por 6h também
        save_state(state)  # salva a cada post — se o job cair no meio, o que já saiu fica registrado
        format_state.save(fmt_state)  # idem pro estado de rotação de formato/molde
        posted_count += 1
        print(f"[{post.icao}] publicado: media_id={media_id}")

    print(f"\n{posted_count} post(s) novo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run()
