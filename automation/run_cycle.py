"""
Etapa 4 (parte 2) — ciclo totalmente automático, sem pausa manual: busca
dados de todos os aeroportos, filtra (rules.py), monta o post (content.py +
slide.py), e publica direto no Instagram — só quando é uma condição NOVA
(ver state.py). Feito pra rodar sozinho, agendado, via
.github/workflows/post-avisos.yml (a cada hora).

Diferente de publish.py (--stage / --go), aqui não há revisão humana no meio
— é o modo "publicações automáticas" pedido pelo usuário em 2026-08-23, com a
deduplicação (state.py) fazendo o papel de não postar a mesma coisa 2x.
"""
import sys
from datetime import datetime, timezone

from airports import AIRPORTS
from content import build_post_content
from fetch_data import FetchError, fetch_metar, fetch_notam
from publish import create_container, get_publishing_credentials, host_images_on_github, publish_container
from rules import evaluate_airport
from slide import render_post_slides
from state import is_posted, load_state, mark_posted, save_state

# limite conservador de posts novos por execução (agendada de hora em hora) —
# evita rajada de publicações que pareça comportamento de bot pra Meta/Instagram,
# mesmo em dias com muitos avisos simultâneos (ex.: frente fria afetando vários
# aeroportos ao mesmo tempo). O que passar do limite sai nas próximas execuções,
# nunca se perde — só fica pra depois. Aprovado pelo usuário em 2026-08-23.
MAX_POSTS_PER_RUN = 3


def run():
    state = load_state()
    _, page_token, ig_user_id = get_publishing_credentials()

    posted_count = 0
    for airport in AIRPORTS:
        if posted_count >= MAX_POSTS_PER_RUN:
            print(f"Limite de {MAX_POSTS_PER_RUN} post(s) por execução atingido — o resto fica pra próxima hora.")
            break
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
        post = build_post_content(icao, airport, metar, evaluation)
        if post is None:
            continue

        if is_posted(state, post.dedup_key):
            print(f"[{icao}] já postado ({post.dedup_key}) — pulando")
            continue

        print(f"[{icao}] condição nova ({post.dedup_key}) — gerando e publicando")
        try:
            paths = render_post_slides(post)
            image_urls = host_images_on_github(paths, icao)
            creation_id = create_container(ig_user_id, page_token, image_urls, post.caption)
            media_id = publish_container(ig_user_id, page_token, creation_id)
        except Exception as err:
            print(f"[{icao}] ERRO ao publicar: {err}")
            continue

        mark_posted(state, post.dedup_key, media_id, datetime.now(timezone.utc).isoformat())
        save_state(state)  # salva a cada post — se o job cair no meio, o que já saiu fica registrado
        posted_count += 1
        print(f"[{icao}] publicado: media_id={media_id}")

    print(f"\n{posted_count} post(s) novo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run()
