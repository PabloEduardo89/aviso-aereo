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

Quando não há NENHUM candidato real nesta execução, entra o fallback educativo
(fallback_content.py, aprovado pelo usuário em 2026-08-23) — garante que a
conta nunca fique muda por muitas horas seguidas, mesmo em dias sem nenhum
aviso ativo.
"""
import sys
import time
from datetime import datetime, timezone

from airports import AIRPORTS
from content import build_post_content
from fallback_content import TOPICS as FALLBACK_TOPICS
from fallback_content import build_fallback_post
from fetch_data import FetchError, fetch_metar, fetch_notam
from publish import create_container, get_publishing_credentials, host_images_on_github, publish_container
from rules import evaluate_airport
from slide import render_post_slides
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

# intervalo mínimo sem NENHUM post (real ou fallback) antes de soltar um novo
# post educativo de fallback — bem mais espaçado que 1/hora de propósito, pra
# não competir pela cota diária da API do Instagram (~25 posts/24h) nem criar
# um padrão repetitivo (mesmo tipo de conteúdo, mesmo horário, todo dia) que
# sistemas antispam da Meta possam sinalizar. Aprovado 2026-08-23.
MIN_FALLBACK_INTERVAL_SECONDS = 4 * 3600  # 4 horas


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
    """Devolve 1 PostContent educativo (ver fallback_content.py) se já faz tempo
    demais (MIN_FALLBACK_INTERVAL_SECONDS) sem nenhum post — real ou fallback —,
    ou None se ainda não é hora (ou se essa é a 1ª vez, sem registro de tempo)."""
    last_iso = get_meta(state, "last_post_at")
    if last_iso is not None:
        elapsed = (now - datetime.fromisoformat(last_iso)).total_seconds()
        if elapsed < MIN_FALLBACK_INTERVAL_SECONDS:
            return None

    index = get_meta(state, "fallback_topic_index", 0) % len(FALLBACK_TOPICS)
    set_meta(state, "fallback_topic_index", (index + 1) % len(FALLBACK_TOPICS))
    return build_fallback_post(FALLBACK_TOPICS[index])


def run():
    state = load_state()
    now = datetime.now(timezone.utc)
    candidates = collect_candidates(state)

    if not candidates:
        fallback = maybe_build_fallback(state, now)
        if fallback is None:
            print("Nenhuma condição nova pra postar nesta execução (fallback educativo ainda não é hora).")
            return
        print(f"Nenhuma condição nova — publicando conteúdo educativo de fallback ({fallback.dedup_key}).")
        candidates = [fallback]

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

        print(f"[{post.icao}] publicando ({post.dedup_key})")
        try:
            paths = render_post_slides(post)
            image_urls = host_images_on_github(paths, post.icao)
            creation_id = create_container(ig_user_id, page_token, image_urls, post.caption)
            media_id = publish_container(ig_user_id, page_token, creation_id)
        except Exception as err:
            print(f"[{post.icao}] ERRO ao publicar: {err}")
            continue

        posted_at = datetime.now(timezone.utc).isoformat()
        mark_posted(state, post.dedup_key, media_id, posted_at)
        set_meta(state, "last_post_at", posted_at)  # zera o relógio do fallback educativo (ver maybe_build_fallback)
        save_state(state)  # salva a cada post — se o job cair no meio, o que já saiu fica registrado
        posted_count += 1
        print(f"[{post.icao}] publicado: media_id={media_id}")

    print(f"\n{posted_count} post(s) novo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run()
