"""
Etapa 3 (parte 2) — gera o(s) slide(s) do post a partir de um PostContent
(ver content.py), seguindo os dois padrões de design definidos pelo usuário:

- CAPA (regra geral, sempre gerado): estilo card de notícia (referência: feed
  do G1 no Instagram) — foto real de fundo (quando temos uma curada pro
  aeroporto; senão satélite/ilustração, ver backgrounds.py) com degradê
  escuro na base, selo pequeno da conta no canto, etiqueta colorida curta
  (kicker) e título em frase normal (não caixa alta) sobre o degradê.
- EXPLICATIVO (exceção, só quando a capa sozinha não é suficiente): fundo
  branco, selo da conta, subtítulo serifado em vermelho, texto corrido
  organizado em blocos ("o que aconteceu", "o que significa", "duração
  prevista") e um card de rodapé com o registro bruto (METAR/NOTAM) — na
  falta de mapa de apoio, é o que temos de mais autêntico pra mostrar ali.
"""
import os

from PIL import Image, ImageDraw, ImageFont

from backgrounds import get_background_for_post
from content import PostContent

WIDTH, HEIGHT = 1080, 1350
MARGIN = 72

COLOR_ACCENT_ALTO = "#E9543F"      # vermelho — mesmo tom do duotone de fundo
COLOR_ACCENT_ATENCAO = "#F2A93B"   # âmbar
COLOR_ACCENT_INFO = "#3B82C4"      # azul — conteúdo educativo de fallback, nunca vermelho/âmbar (não é alerta)
COLOR_BLACK_BLOCK = "#0A0A0A"
COLOR_WHITE = "#FFFFFF"
COLOR_WHITE_MUTED = "#C9C9C9"
COLOR_CARD_BG = "#F1F0EC"
COLOR_LINE = "#DDDDDD"

FONT_DIR = r"C:\Windows\Fonts"
FONT_CONDENSED_BOLD = os.path.join(FONT_DIR, "ARIALNB.TTF")
FONT_CONDENSED = os.path.join(FONT_DIR, "ARIALN.TTF")
FONT_SANS_BOLD = os.path.join(FONT_DIR, "segoeuib.ttf")
FONT_SANS = os.path.join(FONT_DIR, "segoeui.ttf")
FONT_SERIF = os.path.join(FONT_DIR, "georgia.ttf")
FONT_SERIF_BOLD = os.path.join(FONT_DIR, "georgiab.ttf")
FONT_MONO = os.path.join(FONT_DIR, "consola.ttf")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _accent(post: PostContent) -> str:
    if post.severity == "alto":
        return COLOR_ACCENT_ALTO
    if post.severity == "informativo":
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


def _fit_title(draw, text, font_path, max_width, max_lines, start_size, min_size=40, step=4):
    """Reduz o tamanho da fonte até o título caber em no máximo `max_lines` linhas."""
    size = start_size
    while size > min_size:
        font = _font(font_path, size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        size -= step
    font = _font(font_path, min_size)
    return font, _wrap_text(draw, text, font, max_width)


# ---------------------------------------------------------------- CAPA ----

def _bottom_gradient(img: Image.Image, start_frac=0.40, max_alpha=248) -> Image.Image:
    """Degradê escuro na base da imagem (estilo card de notícia), pra garantir
    legibilidade do título sobre a foto/ilustração de fundo. Devolve RGBA."""
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


def render_capa_slide(post: PostContent, out_path: str | None = None) -> str:
    accent = _accent(post)
    bg, photo_author = get_background_for_post(post.icao, post.background_category, post.headline_kind)
    img = _bottom_gradient(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    pad = MARGIN
    max_w = WIDTH - 2 * pad

    # selo pequeno da conta, canto superior esquerdo (discreto, como o logo do G1)
    font_brand = _font(FONT_SANS_BOLD, 26)
    brand_text = "@AVISOAEREO"
    brand_w = draw.textlength(brand_text, font=font_brand) + 36
    draw.rounded_rectangle([(pad - 20, 44), (pad - 20 + brand_w, 44 + 50)], radius=25, fill=(0, 0, 0, 140))
    draw.text((pad - 2, 44 + 25), brand_text, font=font_brand, fill=COLOR_WHITE, anchor="lm")

    # pré-calcula todo o bloco de texto de baixo pra cima, pra ancorar no rodapé
    # kicker = código + UF (informação nova, já que o título abaixo repete o
    # nome da cidade e a categoria do aviso) — a cor da etiqueta ainda indica a severidade
    font_kicker = _font(FONT_SANS_BOLD, 26)
    kicker_text = post.kicker_text or f"{post.icao} · {post.uf}"
    kicker_h = 46

    font_title, title_lines = _fit_title(draw, post.cover_title, FONT_SANS_BOLD, max_w,
                                          max_lines=3, start_size=72, min_size=42)
    title_line_h = font_title.size + 12

    font_sub = _font(FONT_SANS, 30)
    subtitle_lines = _wrap_text(draw, post.cover_subtitle, font_sub, max_w)[:2] if post.cover_subtitle else []
    sub_line_h = 38

    credit_text = f"Foto: {photo_author}" if photo_author else None
    font_credit = _font(FONT_SANS, 20)

    block_h = kicker_h + 22 + len(title_lines) * title_line_h
    if subtitle_lines:
        block_h += 16 + len(subtitle_lines) * sub_line_h
    if credit_text:
        block_h += 26 + 26

    y = HEIGHT - pad - block_h

    # kicker: etiqueta curta e colorida (a categoria do aviso), acima do título
    kicker_w = draw.textlength(kicker_text, font=font_kicker) + 40
    draw.rounded_rectangle([(pad, y), (pad + kicker_w, y + kicker_h)], radius=kicker_h // 2, fill=accent)
    draw.text((pad + 20, y + kicker_h / 2), kicker_text, font=font_kicker, fill=COLOR_WHITE, anchor="lm")
    y += kicker_h + 22

    # título — manchete em frase normal, não caixa alta
    for line in title_lines:
        draw.text((pad, y), line, font=font_title, fill=COLOR_WHITE)
        y += title_line_h

    if subtitle_lines:
        y += 16
        for line in subtitle_lines:
            draw.text((pad, y), line, font=font_sub, fill=COLOR_WHITE_MUTED)
            y += sub_line_h

    if credit_text:
        y += 26
        draw.text((pad, y), credit_text, font=font_credit, fill=(255, 255, 255, 165))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_1_capa.png")
    img.convert("RGB").save(out_path, "PNG")
    return out_path


# --------------------------------------------------------- EXPLICATIVO ----

def render_explicativo_slide(post: PostContent, out_path: str | None = None) -> str | None:
    if post.explicativo is None:
        return None
    e = post.explicativo
    accent = _accent(post)

    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_WHITE)
    draw = ImageDraw.Draw(img)
    max_w = WIDTH - 2 * MARGIN
    y = MARGIN

    # selo com o nome da conta em destaque colorido
    font_badge = _font(FONT_SANS_BOLD, 26)
    badge_text = "@AVISOAEREO"
    badge_w = draw.textlength(badge_text, font=font_badge) + 48
    draw.rounded_rectangle([(MARGIN, y), (MARGIN + badge_w, y + 56)], radius=28, fill=accent)
    draw.text((MARGIN + 24, y + 28), badge_text, font=font_badge, fill=COLOR_WHITE, anchor="lm")
    y += 56 + 44

    # subtítulo/categoria — serifado, em vermelho
    font_subtitulo = _font(FONT_SERIF_BOLD, 44)
    for line in _wrap_text(draw, e.subtitulo, font_subtitulo, max_w):
        draw.text((MARGIN, y), line, font=font_subtitulo, fill=accent)
        y += 54
    y += 14

    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=COLOR_LINE, width=2)
    y += 36

    font_heading = _font(FONT_SERIF_BOLD, 30)
    font_body = _font(FONT_SERIF, 30)
    body_line_h = 40

    def draw_block(heading, body_text):
        nonlocal y
        draw.text((MARGIN, y), heading, font=font_heading, fill="#111111")
        y += body_line_h
        for line in _wrap_text(draw, body_text, font_body, max_w):
            draw.text((MARGIN, y), line, font=font_body, fill="#222222")
            y += body_line_h
        y += 26

    draw_block(e.heading_1, e.o_que_aconteceu)
    draw_block(e.heading_2, e.o_que_significa)
    if e.duracao_prevista:
        draw_block("DURAÇÃO PREVISTA:", e.duracao_prevista)

    # card de rodapé com o registro bruto (METAR/NOTAM) ou exemplo real — na
    # falta de mapa/foto de apoio, é a informação mais autêntica disponível
    # pra mostrar ali; oculto quando não há snippet (ex.: alguns posts educativos)
    if e.raw_snippet:
        card_h = 190
        card_top = HEIGHT - MARGIN - card_h
        if card_top > y + 20:
            font_label = _font(FONT_SANS_BOLD, 22)
            draw.text((MARGIN, card_top - 34), e.raw_snippet_label, font=font_label, fill="#8A8A8A")
            draw.rounded_rectangle([(MARGIN, card_top), (WIDTH - MARGIN, HEIGHT - MARGIN)],
                                    radius=20, fill=COLOR_CARD_BG)
            font_mono = _font(FONT_MONO, 25)
            my = card_top + 28
            for line in _wrap_text(draw, e.raw_snippet, font_mono, max_w - 48)[:5]:
                draw.text((MARGIN + 24, my), line, font=font_mono, fill="#333333")
                my += 33

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(OUTPUT_DIR, f"{post.icao}_{_post_slug(post)}_2_explicativo.png")
    img.save(out_path, "PNG")
    return out_path


def render_post_slides(post: PostContent) -> list:
    """Gera todos os slides do post: capa sempre, explicativo só quando necessário."""
    paths = [render_capa_slide(post)]
    if post.needs_explicativo:
        path = render_explicativo_slide(post)
        if path:
            paths.append(path)
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
