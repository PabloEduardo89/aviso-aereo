"""
Etapa 3 (parte 2) — gera o(s) slide(s) do post a partir de um PostContent (ver
content.py), no padrão único definido pelo usuário em 2026-08-27: TODO slide do
carrossel — inclusive os que antes eram "explicativos" de fundo branco — segue
o molde do card de notícia (referência: feed do G1 no Instagram): foto real de
fundo (uma DIFERENTE por slide, buscada pela palavra-chave daquele slide
específico — ver content.SlideSpec/backgrounds.fetch_pexels_photo — pra não
repetir imagem dentro do carrossel nem entre posts), degradê escuro na base,
selo `@avisoaereo` em destaque no topo, etiqueta colorida curta (kicker) e
título curto (pouca escrita, no máximo 2 linhas) sobre o degradê.

Regra fixa (2026-08-27): todo carrossel termina com um slide de
Call-to-Action padrão pra seguir a conta (`render_cta_slide`), acrescentado
por `render_post_slides` — quem monta o PostContent (content.py,
fallback_content.py) nunca inclui o CTA na própria lista de slides.
"""
import os
import random
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import style
from backgrounds import duotone, fetch_pexels_photo, get_background_for_post
from content import PostContent, SlideSpec

WIDTH, HEIGHT = 1080, 1350
MARGIN = 72

COLOR_ACCENT_ALTO = "#E9543F"      # vermelho — mesmo tom do duotone de fundo
COLOR_ACCENT_ATENCAO = "#F2A93B"   # âmbar
COLOR_ACCENT_INFO = "#3B82C4"      # azul — conteúdo educativo, nunca vermelho/âmbar (não é alerta)
COLOR_BRAND = "#F2A93B"            # cor de marca do selo @avisoaereo — mesmo âmbar do app (index.html)
COLOR_WHITE = "#FFFFFF"
COLOR_WHITE_MUTED = "#E4E4E4"

# Fontes empacotadas no repo (SIL OFL, assets/fonts/) em vez de fontes do
# sistema — C:\Windows\Fonts só existe no PC Windows do usuário; o runner do
# GitHub Actions é Linux e não tem essas fontes (lição do incidente de
# 2026-08-24: sem isso, acentos saíam quebrados nos posts gerados pela nuvem).
FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
_FONT_FILES = {
    "sans": os.path.join(FONT_DIR, "Inter[opsz,wght].ttf"),
    "serif": os.path.join(FONT_DIR, "Lora[wght].ttf"),
    "mono": os.path.join(FONT_DIR, "RobotoMono[wght].ttf"),
}
_FONT_AXES = {
    "sans_bold": ("sans", [32, 700]),
    "sans": ("sans", [16, 400]),
    "serif_bold": ("serif", [700]),
    "serif": ("serif", [400]),
    "mono": ("mono", [400]),
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# rotação de palavras-chave (em INGLÊS — o Pexels responde melhor, ver
# content._IMPACT_IMAGE_QUERY) pro fundo do slide de CTA — genéricas o bastante
# pra caber em qualquer post, mas ainda assim uma foto REAL e específica (não
# reaproveita a foto de nenhum outro slide do carrossel)
_CTA_IMAGE_QUERIES = [
    "sunset sky airplane", "airport runway night", "airplane takeoff clouds",
    "control tower sunset", "airplane window clouds",
]


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _font(role, size):
    family, axes = _FONT_AXES[role]
    font = ImageFont.truetype(_FONT_FILES[family], size)
    font.set_variation_by_axes(axes)
    return font


def _accent(severity: str) -> str:
    if severity == "alto":
        return COLOR_ACCENT_ALTO
    if severity == "informativo":
        return COLOR_ACCENT_INFO
    return COLOR_ACCENT_ATENCAO


def _post_slug(post: PostContent) -> str:
    """Identificador único do post pro nome do arquivo — necessário desde que um
    mesmo aeroporto pode gerar mais de um post ao mesmo tempo (motivos distintos
    viram notícias separadas, ver content.py). Deriva do dedup_key, tirando o
    prefixo do ICAO (já é o nome da pasta/arquivo) e trocando '|' por '_'."""
    _, rest = post.dedup_key.split("|", 1)
    return rest.replace("|", "_").replace("/", "-")


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_title(draw, text, font_role, max_width, max_lines, start_size, min_size=40, step=4):
    """Reduz o tamanho da fonte até o título caber em no máximo `max_lines` linhas."""
    size = start_size
    while size > min_size:
        font = _font(font_role, size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        size -= step
    font = _font(font_role, min_size)
    return font, _wrap_text(draw, text, font, max_width)


def _bottom_gradient(img: Image.Image, start_frac=0.42, max_alpha=250) -> Image.Image:
    """Degradê escuro na base da imagem (estilo card de notícia), pra garantir
    legibilidade do título sobre a foto de fundo. Devolve RGBA."""
    base = img.convert("RGBA")
    start_y = int(HEIGHT * start_frac)
    gradient = Image.new("L", (1, HEIGHT), 0)
    for y in range(start_y, HEIGHT):
        t = (y - start_y) / max(1, HEIGHT - start_y)
        gradient.putpixel((0, y), int(max_alpha * (t ** 1.3)))
    gradient = gradient.resize((WIDTH, HEIGHT))
    black = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    black.putalpha(gradient)
    return Image.alpha_composite(base, black)


def _draw_brand_badge(draw):
    """Selo @avisoaereo — bem mais em destaque do que o padrão anterior (pedido do
    usuário, 2026-08-27): centralizado no topo, fundo sólido na cor de marca (o
    mesmo âmbar do app principal) em vez do badge pequeno/semitransparente de
    antes, pra reforçar a identidade da conta em toda a extensão do carrossel —
    inclusive nos slides que antes eram "explicativos" e não tinham selo nenhum."""
    font_brand = _font("sans_bold", 34)
    brand_text = "@AVISOAEREO"
    brand_w = draw.textlength(brand_text, font=font_brand) + 56
    brand_x = (WIDTH - brand_w) / 2
    draw.rounded_rectangle([(brand_x, 44), (brand_x + brand_w, 44 + 64)], radius=32, fill=COLOR_BRAND)
    draw.text((WIDTH / 2, 44 + 32), brand_text, font=font_brand, fill="#151515", anchor="mm")


def render_photo_slide(background_img, credit, accent, kicker_text, title, subtitle=None,
                        out_path=None) -> str:
    """Slide único, no molde CAPA (foto + degradê + kicker + título curto) — usado
    pra TODO slide do carrossel a partir de 2026-08-27 (antes só a capa em si
    seguia esse padrão; os explicativos tinham um layout de fundo branco à parte,
    removido pra unificar a "cara" do post inteiro)."""
    img = _bottom_gradient(background_img)
    draw = ImageDraw.Draw(img, "RGBA")
    pad = MARGIN
    max_w = WIDTH - 2 * pad

    _draw_brand_badge(draw)

    # kicker = etiqueta curta acima do título — a cor ainda indica a severidade
    font_kicker = _font("sans_bold", 26)
    kicker_h = 46

    # título curto — no máximo 2 linhas (regra "pouca escrita" do usuário,
    # 2026-08-27; a capa original permitia até 3)
    font_title, title_lines = _fit_title(draw, title, "sans_bold", max_w,
                                          max_lines=2, start_size=68, min_size=34)
    title_line_h = font_title.size + 12

    font_sub = _font("sans", 28)
    subtitle_lines = _wrap_text(draw, subtitle, font_sub, max_w)[:2] if subtitle else []
    sub_line_h = 36

    credit_text = f"Foto: {credit}" if credit else None
    font_credit = _font("sans", 19)

    block_h = kicker_h + 22 + len(title_lines) * title_line_h
    if subtitle_lines:
        block_h += 14 + len(subtitle_lines) * sub_line_h
    if credit_text:
        block_h += 24 + 24

    y = HEIGHT - pad - block_h

    kicker_w = draw.textlength(kicker_text, font=font_kicker) + 40
    draw.rounded_rectangle([(pad, y), (pad + kicker_w, y + kicker_h)], radius=kicker_h // 2, fill=accent)
    draw.text((pad + 20, y + kicker_h / 2), kicker_text, font=font_kicker, fill=COLOR_WHITE, anchor="lm")
    y += kicker_h + 22

    for line in title_lines:
        draw.text((pad, y), line, font=font_title, fill=COLOR_WHITE)
        y += title_line_h

    if subtitle_lines:
        y += 14
        for line in subtitle_lines:
            draw.text((pad, y), line, font=font_sub, fill=COLOR_WHITE_MUTED)
            y += sub_line_h

    if credit_text:
        y += 24
        draw.text((pad, y), credit_text, font=font_credit, fill=(255, 255, 255, 165))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(OUTPUT_DIR, "slide.png")
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def render_cta_slide(accent, out_path=None) -> str:
    """Último slide padrão de TODO carrossel (regra fixa, 2026-08-27) — convite
    direto pra seguir a conta, sempre no mesmo molde visual dos demais slides."""
    query = random.choice(_CTA_IMAGE_QUERIES)
    result = fetch_pexels_photo(query)
    if result is None:
        # sem chave/instável no momento — cai numa cor sólida de marca em vez de
        # deixar o slide sem imagem nenhuma
        background_img = Image.new("RGB", (WIDTH, HEIGHT), "#111111")
        credit = None
    else:
        background_img, credit, _ = result

    img = _bottom_gradient(background_img, start_frac=0.0, max_alpha=235)
    draw = ImageDraw.Draw(img, "RGBA")
    _draw_brand_badge(draw)

    font_headline = _font("sans_bold", 64)
    headline_lines = _wrap_text(draw, "Quer saber na hora?", font_headline, WIDTH - 2 * MARGIN)
    font_body = _font("sans", 32)
    body_lines = _wrap_text(draw, "Siga @avisoaereo para alertas reais de aeroportos, direto no seu feed.",
                             font_body, WIDTH - 2 * MARGIN)

    total_h = len(headline_lines) * 76 + 24 + len(body_lines) * 44
    y = (HEIGHT - total_h) / 2
    for line in headline_lines:
        draw.text((WIDTH / 2, y), line, font=font_headline, fill=COLOR_WHITE, anchor="ma")
        y += 76
    y += 24
    for line in body_lines:
        draw.text((WIDTH / 2, y), line, font=font_body, fill=COLOR_WHITE_MUTED, anchor="ma")
        y += 44

    # botão-mock "Seguir", só pra reforçar visualmente a ação pedida
    btn_w, btn_h = 260, 74
    btn_x, btn_y = (WIDTH - btn_w) / 2, y + 30
    draw.rounded_rectangle([(btn_x, btn_y), (btn_x + btn_w, btn_y + btn_h)], radius=btn_h // 2, fill=accent)
    draw.text((WIDTH / 2, btn_y + btn_h / 2), "SEGUIR", font=_font("sans_bold", 30),
               fill=COLOR_WHITE, anchor="mm")

    if credit:
        font_credit = _font("sans", 19)
        draw.text((MARGIN, HEIGHT - MARGIN + 6), f"Foto: {credit}", font=font_credit,
                   fill=(255, 255, 255, 165), anchor="lb")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(OUTPUT_DIR, "cta.png")
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def _resolve_slide_background(post: PostContent, slide: SlideSpec, used_photo_ids: set):
    """slide.image_query is None -> usa o fundo "oficial" do post (foto curada do
    aeroporto / satélite / ilustração, ver backgrounds.get_background_for_post) —
    reservado pro 1º slide, o mais específico/confiável que temos. Qualquer
    image_query preenchido busca uma foto real no Pexels pela palavra-chave
    daquele slide especificamente (regra do usuário, 2026-08-27: cada slide usa
    a foto da SUA própria palavra-chave, nunca repete a mesma foto dentro do
    carrossel)."""
    if slide.image_query is None:
        img, credit = get_background_for_post(post.icao, post.background_category, post.headline_kind)
        return img, credit

    result = fetch_pexels_photo(slide.image_query, exclude_ids=used_photo_ids)
    if result is not None:
        img, credit, photo_id = result
        used_photo_ids.add(photo_id)
        return img, credit

    # Pexels indisponível/sem chave — cai pro fundo "oficial" do post em vez de
    # deixar o slide sem nenhuma imagem
    img, credit = get_background_for_post(post.icao, post.background_category, post.headline_kind)
    return img, credit


def render_post_slides(post: PostContent) -> list:
    """Gera todos os slides do post — cada item de `post.slides` no molde CAPA
    (foto própria + degradê + kicker + título curto) e, por último, sempre o
    slide de Call-to-Action padrão (regra fixa, 2026-08-27: TODO carrossel,
    informativo ou educativo, termina com o convite pra seguir a conta)."""
    accent = _accent(post.severity)
    used_photo_ids = set()
    paths = []

    for i, slide in enumerate(post.slides, start=1):
        background_img, credit = _resolve_slide_background(post, slide, used_photo_ids)
        out_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_{i}.png")
        paths.append(render_photo_slide(
            background_img, credit, accent, slide.kicker_text, slide.title, slide.subtitle,
            out_path=out_path,
        ))

    cta_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_{len(post.slides) + 1}_cta.png")
    paths.append(render_cta_slide(accent, out_path=cta_path))
    return paths


# --------------------------------------------------- MOLDES DE VARIAÇÃO ----
# Moldes visuais alternativos pros posts de alerta real (pedido do usuário,
# 2026-08-28) — convivem com o molde único fotográfico acima ("moderno", o
# carro-chefe) sem substituí-lo. A escolha de QUAL molde usar em cada post
# (incluindo a regra "relevância alta é sempre moderno, sem exceção" e o
# intervalo mínimo saudável entre variações) é feita por style.next_mold,
# fora daqui — este módulo só sabe DESENHAR cada molde, não decide quando
# usá-lo.
#
# - "classico": duotone vermelho na capa + explicativo em fundo branco
#   (retoma o design pré-2026-08-27).
# - "manchete": foto real em cor cheia (sem duotone), título gigante sobre
#   faixa escura no terço superior — tratamento tipográfico mais agressivo,
#   pensado pra prender atenção rápido no feed.

COLOR_CARD_BG_CLASSICO = "#F1F0EC"
COLOR_LINE_CLASSICO = "#DDDDDD"


def render_explicativo_classico(ctx: "style.EventContext", accent: str, headline_label: str,
                                 out_path: str | None = None) -> str:
    """2º slide do molde clássico — fundo branco, serifado, só aparece quando
    style.wants_explicativo_slide diz que há contexto suficiente (aeronave,
    vítimas/sem vítimas, resposta de emergência, duração prevista — ver
    style.EventContext)."""
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_WHITE)
    draw = ImageDraw.Draw(img)
    max_w = WIDTH - 2 * MARGIN
    y = MARGIN

    font_badge = _font("sans_bold", 26)
    badge_text = "@AVISOAEREO"
    badge_w = draw.textlength(badge_text, font=font_badge) + 48
    draw.rounded_rectangle([(MARGIN, y), (MARGIN + badge_w, y + 56)], radius=28, fill=accent)
    draw.text((MARGIN + 24, y + 28), badge_text, font=font_badge, fill=COLOR_WHITE, anchor="lm")
    y += 56 + 44

    font_heading = _font("serif_bold", 44)
    for line in _wrap_text(draw, headline_label, font_heading, max_w):
        draw.text((MARGIN, y), line, font=font_heading, fill=accent)
        y += 54
    y += 14
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=COLOR_LINE_CLASSICO, width=2)
    y += 36

    font_label = _font("sans_bold", 24)
    font_body = _font("serif", 32)

    def block(label, value):
        nonlocal y
        draw.text((MARGIN, y), label, font=font_label, fill="#8A8A8A")
        y += 34
        for line in _wrap_text(draw, value, font_body, max_w):
            draw.text((MARGIN, y), line, font=font_body, fill="#222222")
            y += 42
        y += 30

    if ctx.aircraft_id:
        block("AERONAVE", ctx.aircraft_id)
    if ctx.casualties_info:
        block("VÍTIMAS", ctx.casualties_info)
    if ctx.response_action:
        block("RESPOSTA", ctx.response_action)
    if ctx.duration_text:
        block("DURAÇÃO PREVISTA", ctx.duration_text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(OUTPUT_DIR, "explicativo_classico.png")
    img.save(out_path, "PNG")
    return out_path


def render_capa_manchete(background_img, credit, accent, kicker_text, title,
                          out_path: str | None = None) -> str:
    """Capa do molde 'manchete' — foto real em COR CHEIA (sem duotone, ao
    contrário do clássico) com faixa escura no terço superior e título bem
    maior que o do moderno, kicker em texto simples + barra de destaque
    (não pill) — visualmente distinto dos outros dois moldes de propósito,
    pra ser reconhecível como uma "edição" diferente à primeira vista."""
    img = background_img.convert("RGBA")
    pad = MARGIN
    max_w = WIDTH - 2 * pad

    probe = ImageDraw.Draw(img)
    font_title, title_lines = _fit_title(probe, title, "sans_bold", max_w,
                                          max_lines=3, start_size=92, min_size=50)
    title_line_h = font_title.size + 14
    font_kicker = _font("sans_bold", 24)

    scrim_h = 40 + 8 + 18 + (font_kicker.size + 6) + 20 + len(title_lines) * title_line_h + 36
    scrim_top = int(HEIGHT * 0.30)
    scrim_top = min(scrim_top, HEIGHT - scrim_h - MARGIN)
    scrim = Image.new("RGBA", (WIDTH, scrim_h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(scrim)
    fade = 40
    for y in range(scrim_h):
        alpha = int(238 * min(1.0, y / fade))
        sdraw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    img.alpha_composite(scrim, (0, scrim_top))

    draw = ImageDraw.Draw(img, "RGBA")
    _draw_brand_badge(draw)

    y = scrim_top + 40
    draw.rectangle([(pad, y), (pad + 72, y + 8)], fill=accent)
    y += 8 + 18

    draw.text((pad, y), kicker_text, font=font_kicker, fill=accent)
    y += font_kicker.size + 6 + 20

    for line in title_lines:
        draw.text((pad, y), line, font=font_title, fill=COLOR_WHITE)
        y += title_line_h

    if credit:
        font_credit = _font("sans", 19)
        draw.text((pad, HEIGHT - MARGIN + 6), f"Foto: {credit}", font=font_credit,
                   fill=(255, 255, 255, 165), anchor="lb")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(OUTPUT_DIR, "capa_manchete.png")
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def render_post_slides_variation(post: PostContent, mold: str, fmt_state: dict) -> list:
    """Gera os slides de um molde de VARIAÇÃO ("classico" ou "manchete") pra
    este post — capa sempre, explicativo em fundo branco só quando há
    contexto suficiente (ver style.wants_explicativo_slide, compartilhado
    pelos dois moldes de variação), CTA padrão por último. Muta `fmt_state`
    em memória (índices das rotações) — quem chama persiste
    (format_state.save), igual ao dedup de state.py. Quem decide QUAL molde
    usar é style.next_mold, sempre chamado ANTES desta função — aqui só
    desenha."""
    if mold not in style.VARIATION_MOLDS:
        raise ValueError(f"molde de variação desconhecido: {mold!r} (esperado um de {style.VARIATION_MOLDS})")

    tier = style.severity_tier(post.headline_kind)
    accent = style.RED_BY_TIER[tier]
    badge = style.category_badge(post.headline_kind)
    when_dt = post.when_dt or datetime.now(timezone.utc)

    query = style.pick_image_query(post.headline_kind, fmt_state)
    result = fetch_pexels_photo(query)
    if result is not None:
        bg, credit, _ = result
    else:
        bg, credit = get_background_for_post(post.icao, post.background_category, post.headline_kind)

    fmt = style.next_title_format(fmt_state)
    title = style.title_format_variation(fmt, post.city, post.headline_kind, when_dt)

    paths = []
    capa_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_1_capa_{mold}.png")
    if mold == "classico":
        bg_treated = ImageEnhance.Brightness(bg).enhance(0.55) if style.is_nighttime(when_dt) else bg
        bg_treated = duotone(bg_treated, light=_hex_to_rgb(accent))
        render_photo_slide(bg_treated, credit, accent, badge, title, out_path=capa_path)
    else:  # manchete — cor cheia, sem duotone (mesma regra de qualidade de imagem do moderno)
        render_capa_manchete(bg, credit, accent, badge, title, out_path=capa_path)
    paths.append(capa_path)

    ctx = style.extract_event_context(post)
    if style.wants_explicativo_slide(ctx):
        exp_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_2_explicativo_{mold}.png")
        render_explicativo_classico(ctx, accent, post.headline, out_path=exp_path)
        paths.append(exp_path)

    cta_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_{len(paths) + 1}_cta.png")
    render_cta_slide(accent, out_path=cta_path)
    paths.append(cta_path)
    return paths


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    from airports import AIRPORTS
    from fetch_data import FetchError, fetch_metar, fetch_notam
    from rules import evaluate_airport
    from content import build_post_content

    by_code = {a["code"]: a for a in AIRPORTS}
    generated = 0
    for icao, airport in by_code.items():
        try:
            metar = fetch_metar(icao)
        except FetchError:
            metar = None
        try:
            notams = fetch_notam(icao)
        except FetchError:
            notams = []

        evaluation = evaluate_airport(icao, metar, notams)
        for post in build_post_content(icao, airport, metar, evaluation):
            paths = render_post_slides(post)
            print(f"[{icao}] ({post.dedup_key}) {len(paths)} slide(s): {', '.join(paths)}")
            generated += 1

    print(f"\n{generated} post(s) gerado(s) em {OUTPUT_DIR}")
