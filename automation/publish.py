"""
Etapa 4 — publicação no Instagram via Graph API.

Fluxo (carrossel quando há slide explicativo, post único quando não há):
  1. hospedar as imagens numa URL pública (GitHub raw, commit+push no próprio
     repositório do site — ver host_images_on_github)
  2. criar o(s) container(s) de mídia (POST /media) — isso NÃO publica nada,
     só prepara o conteúdo do lado do Meta
  3. publicar de fato (POST /media_publish) — só este último passo é visível
     publicamente no Instagram

Uso pensado pra ter uma revisão manual no meio do caminho, como pedido:
    python publish.py SBFL --stage     -> hospeda + cria o container, mostra
                                           tudo (imagens, legenda, creation_id)
                                           e PARA. Nada foi publicado ainda.
    python publish.py SBFL --go <id>   -> publica de fato o container criado
                                           no passo anterior.

Nunca chama --go sozinho: cada publicação real exige rodar os dois passos
em momentos separados, com a legenda/imagens já revisadas no meio.
"""
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import format_state
import style
from airports import AIRPORTS
from content import build_post_content
from fetch_data import FetchError, fetch_metar, fetch_notam
from git_utils import commit_and_push
from rules import evaluate_airport
from slide import render_post_slides, render_post_slides_variation

load_dotenv()

GRAPH_BASE = "https://graph.facebook.com/v21.0"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR_NAME = "posts"
GITHUB_REPO = "PabloEduardo89/aviso-aereo"
GITHUB_BRANCH = "main"


class PublishError(Exception):
    pass


def get_publishing_credentials():
    """Deriva o Page Access Token e o ID da conta do Instagram a partir do
    INSTAGRAM_TOKEN (token de usuário) do .env. Sempre busca na hora — não
    guarda o Page Access Token em disco, pra nunca depender de um valor
    potencialmente desatualizado."""
    user_token = os.getenv("INSTAGRAM_TOKEN")
    if not user_token:
        raise PublishError("INSTAGRAM_TOKEN não configurado no .env")

    resp = requests.get(f"{GRAPH_BASE}/me/accounts", params={
        "access_token": user_token,
        "fields": "id,name,access_token,instagram_business_account",
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data") or []
    if not data:
        raise PublishError("Nenhuma Página do Facebook encontrada para esse token")

    page = data[0]
    ig_account = page.get("instagram_business_account")
    if not ig_account:
        raise PublishError(f"A página '{page['name']}' não tem conta do Instagram vinculada")

    return page["id"], page["access_token"], ig_account["id"]


def host_images_on_github(paths: list, icao: str) -> list:
    """Copia as imagens pra <repo>/posts/<icao>/, comita e dá push (com retry
    resiliente a push concorrente — ver git_utils.commit_and_push e o
    incidente de 2026-08-26 que motivou isso) — devolve as URLs
    raw.githubusercontent.com correspondentes."""
    dest_dir = os.path.join(REPO_ROOT, POSTS_DIR_NAME, icao)
    os.makedirs(dest_dir, exist_ok=True)

    rel_paths = []
    for path in paths:
        filename = os.path.basename(path)
        dest_path = os.path.join(dest_dir, filename)
        with open(path, "rb") as src, open(dest_path, "wb") as dst:
            dst.write(src.read())
        rel_paths.append(f"{POSTS_DIR_NAME}/{icao}/{filename}")

    commit_and_push(REPO_ROOT, rel_paths, f"post: imagens {icao}", branch=GITHUB_BRANCH)

    return [f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{rel}" for rel in rel_paths]


def _graph_post(path: str, token: str, **params) -> dict:
    resp = requests.post(f"{GRAPH_BASE}/{path}", data={**params, "access_token": token}, timeout=30)
    payload = resp.json()
    if resp.status_code >= 400 or "error" in payload:
        raise PublishError(f"Graph API erro em {path}: {payload}")
    return payload


def _graph_get(path: str, token: str, **params) -> dict:
    resp = requests.get(f"{GRAPH_BASE}/{path}", params={**params, "access_token": token}, timeout=30)
    payload = resp.json()
    if resp.status_code >= 400 or "error" in payload:
        raise PublishError(f"Graph API erro em GET {path}: {payload}")
    return payload


# Quanto esperar o container de mídia terminar de processar do lado do Meta
# antes de publicar. Carrossel de várias imagens costuma levar alguns segundos;
# chamar /media_publish antes de o container ficar FINISHED devolve o erro
# 9007 / subcode 2207027 ("A mídia não está pronta para ser publicada") — foi o
# que derrubou o post de SBPA em 2026-08-29.
_CONTAINER_READY_TIMEOUT_S = 120
_CONTAINER_POLL_INTERVAL_S = 5


def wait_until_container_ready(token: str, creation_id: str) -> None:
    """Faz polling de GET /{creation_id}?fields=status_code até o container
    ficar FINISHED (pronto pra publicar). Levanta PublishError se o Meta
    devolver ERROR/EXPIRED ou se estourar o timeout."""
    deadline = time.monotonic() + _CONTAINER_READY_TIMEOUT_S
    status = None
    while True:
        info = _graph_get(creation_id, token, fields="status_code,status")
        status = info.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(
                f"Container {creation_id} falhou no processamento do Meta: {info}")
        if time.monotonic() >= deadline:
            raise PublishError(
                f"Container {creation_id} não ficou pronto em "
                f"{_CONTAINER_READY_TIMEOUT_S}s (último status_code: {status})")
        time.sleep(_CONTAINER_POLL_INTERVAL_S)


def create_container(ig_user_id: str, token: str, image_urls: list, caption: str) -> str:
    """Cria o container de mídia (carrossel se houver mais de uma imagem). Não publica nada."""
    if len(image_urls) == 1:
        result = _graph_post(f"{ig_user_id}/media", token, image_url=image_urls[0], caption=caption)
        return result["id"]

    child_ids = []
    for url in image_urls:
        child = _graph_post(f"{ig_user_id}/media", token, image_url=url, is_carousel_item="true")
        child_ids.append(child["id"])

    parent = _graph_post(f"{ig_user_id}/media", token, media_type="CAROUSEL",
                          children=",".join(child_ids), caption=caption)
    return parent["id"]


def publish_container(ig_user_id: str, token: str, creation_id: str) -> str:
    """Publica de fato — este é o passo que vira post público no Instagram.
    Espera o container ficar FINISHED antes de publicar, senão o Meta rejeita
    com "A mídia não está pronta para ser publicada" (9007 / 2207027)."""
    wait_until_container_ready(token, creation_id)
    result = _graph_post(f"{ig_user_id}/media_publish", token, creation_id=creation_id)
    return result["id"]


def stage_post(icao: str, index: int = 0, mold: str | None = None):
    """Monta o post (dados + slides), hospeda as imagens e cria o container —
    tudo isso sem tornar nada público. Um aeroporto pode ter mais de um post
    relevante ao mesmo tempo (motivos distintos, ver content.py) — `index`
    escolhe qual deles estagear; os outros ficam listados no retorno pra você
    saber que existem. `mold` força um de style.MOLDS (ver style.py) —
    diferente do ciclo automático, um valor explícito aqui IGNORA a regra
    "relevância alta é sempre moderno" (é uma escolha manual deliberada, pra
    testar qualquer molde em qualquer post). None (padrão) deixa
    style.next_mold decidir sozinho, igual ao ciclo automático faria.
    Devolve (creation_id, image_urls, caption, ig_user_id, page_token,
    total_posts, mold_usado)."""
    airport = next((a for a in AIRPORTS if a["code"] == icao), None)
    if airport is None:
        raise PublishError(f"{icao} não está em airports.py")

    try:
        metar = fetch_metar(icao)
    except FetchError:
        metar = None
    try:
        notams = fetch_notam(icao)
    except FetchError:
        notams = []

    evaluation = evaluate_airport(icao, metar, notams)
    posts = build_post_content(icao, airport, metar, evaluation)
    if not posts:
        raise PublishError(f"{icao} não tem nenhum motivo ativo pra postar agora")
    if index >= len(posts):
        raise PublishError(f"{icao} só tem {len(posts)} post(s) relevante(s) agora (índice {index} não existe)")

    post = posts[index]
    fmt_state = format_state.load()
    chosen_mold = mold or style.next_mold(post.headline_kind, datetime.now(timezone.utc), fmt_state)
    if chosen_mold != "moderno":
        paths = render_post_slides_variation(post, chosen_mold, fmt_state)
        caption = style.apply_caption_opening(post, fmt_state)
    else:
        paths = render_post_slides(post)
        caption = post.caption
    format_state.save(fmt_state)
    image_urls = host_images_on_github(paths, icao)

    _, page_token, ig_user_id = get_publishing_credentials()
    creation_id = create_container(ig_user_id, page_token, image_urls, caption)

    return creation_id, image_urls, caption, ig_user_id, page_token, len(posts), chosen_mold


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 3 or sys.argv[2] not in ("--stage", "--go"):
        print("Uso:")
        print("  python publish.py <ICAO> --stage [indice] [--mold moderno|classico|manchete]")
        print("                                              (monta e prepara, não publica;")
        print("                                               sem --mold, a rotação automática decide)")
        print("  python publish.py <ICAO> --go <creation_id> (publica de fato)")
        sys.exit(1)

    icao_arg = sys.argv[1].upper()

    if sys.argv[2] == "--stage":
        rest = sys.argv[3:]
        mold_arg = None
        if "--mold" in rest:
            mold_pos = rest.index("--mold")
            mold_arg = rest[mold_pos + 1]
            rest = rest[:mold_pos] + rest[mold_pos + 2:]
        index_arg = int(rest[0]) if rest else 0
        creation_id, image_urls, caption, ig_user_id, page_token, total, mold_used = stage_post(
            icao_arg, index_arg, mold=mold_arg)
        if total > 1:
            print(f"{icao_arg} tem {total} posts relevantes agora (motivos distintos) — "
                  f"estageando o índice {index_arg}. Pra ver os outros: --stage 1, --stage 2, etc.")
        print(f"Molde usado: {mold_used}")
        print(f"Container criado (ainda NÃO publicado): {creation_id}")
        print("Imagens:")
        for url in image_urls:
            print(f"  {url}")
        print("--- legenda ---")
        print(caption)
        print()
        print(f'Revise acima. Pra publicar de verdade: python publish.py {icao_arg} --go {creation_id}')

    elif sys.argv[2] == "--go":
        if len(sys.argv) < 4:
            print("Falta o creation_id: python publish.py <ICAO> --go <creation_id>")
            sys.exit(1)
        creation_id = sys.argv[3]
        _, page_token, ig_user_id = get_publishing_credentials()
        media_id = publish_container(ig_user_id, page_token, creation_id)
        print(f"Publicado! media_id = {media_id}")
        print(f"https://www.instagram.com/p/{media_id}/  (ou confira direto em instagram.com/avisoaereo)")
