"""
Fundos do slide CAPA (etapa 3).

Prioridade (ver PHOTO_POLICY.md pro critério de curadoria das fotos):
  1. foto real curada do aeroporto (assets/photos/<ICAO>.jpg) — dá
     reconhecimento e credibilidade, usada em cor natural + degradê (estilo
     G1), sem nenhum tratamento de cor
  2. imagem de satélite real da REDEMET, pra avisos de origem meteorológica,
     em duotone vermelho (não é "o lugar", então mantém o tratamento gráfico)
  3. ilustração geométrica simples desenhada por código, pra avisos de
     origem operacional (pista/torre/aux. navegação) quando não há foto
     curada do aeroporto — também em duotone vermelho
"""
import json
import os
import random
from datetime import datetime, timezone
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageOps

from fetch_data import REDEMET_API_KEY, REDEMET_BASE, REQUEST_TIMEOUT

WIDTH, HEIGHT = 1080, 1350

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "assets", "photos")
PHOTOS_MANIFEST = os.path.join(PHOTOS_DIR, "manifest.json")

DUOTONE_DARK = (18, 4, 6)        # sombra quase preta, levemente avermelhada
DUOTONE_LIGHT = (233, 84, 63)    # vermelho/laranja de destaque (mesmo tom do selo de "alto impacto")


def duotone(img: Image.Image, dark=DUOTONE_DARK, light=DUOTONE_LIGHT) -> Image.Image:
    """Converte qualquer imagem (foto ou ilustração) pro duotone vermelho da marca."""
    gray = ImageOps.grayscale(img)
    return ImageOps.colorize(gray, black=dark, white=light).convert("RGB")


def cover_resize(img: Image.Image, width=WIDTH, height=HEIGHT) -> Image.Image:
    """Redimensiona mantendo proporção e corta o excedente pra preencher width x height (como CSS 'cover')."""
    src_ratio = img.width / img.height
    dst_ratio = width / height
    if src_ratio > dst_ratio:
        new_height = height
        new_width = int(height * src_ratio)
    else:
        new_width = width
        new_height = int(width / src_ratio)
    resized = img.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def fetch_satellite_background() -> Image.Image | None:
    """Última imagem de satélite (Brasil inteiro) da REDEMET, já em duotone e no tamanho do slide.
    Retorna None se a API não tiver imagem disponível no momento (cai pro chamador tratar o fallback)."""
    now = datetime.now(timezone.utc)
    url = (
        f"{REDEMET_BASE}/produtos/satelite/realcada"
        f"?anima=1&data={now.strftime('%Y%m%d%H')}&api_key={REDEMET_API_KEY}"
    )
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    frames = ((resp.json().get("data") or {}).get("satelite")) or []
    if not frames:
        return None

    img_resp = requests.get(frames[-1]["path"], timeout=REQUEST_TIMEOUT)
    img_resp.raise_for_status()
    img = Image.open(BytesIO(img_resp.content)).convert("RGB")
    return duotone(cover_resize(img))


def _illustration_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (WIDTH, HEIGHT), 20)   # cinza bem escuro — vira o "dark" do duotone
    return img, ImageDraw.Draw(img)


def _runway_illustration() -> Image.Image:
    """Pista vista em perspectiva, com eixo central tracejado — usada em avisos de RWY CLSD."""
    img, draw = _illustration_canvas()
    cx = WIDTH // 2
    top_w, bottom_w = 90, 620
    top_y, bottom_y = HEIGHT * 0.30, HEIGHT * 0.95
    draw.polygon([
        (cx - top_w / 2, top_y), (cx + top_w / 2, top_y),
        (cx + bottom_w / 2, bottom_y), (cx - bottom_w / 2, bottom_y),
    ], fill=200)
    # eixo tracejado
    dash_count = 14
    for i in range(dash_count):
        t0 = i / dash_count
        t1 = t0 + 0.045
        y0 = top_y + (bottom_y - top_y) * t0
        y1 = top_y + (bottom_y - top_y) * t1
        w0 = 4 + (18 - 4) * t0
        draw.line([(cx, y0), (cx, y1)], fill=20, width=max(2, int(w0)))
    return img


def _tower_illustration() -> Image.Image:
    """Torre de controle estilizada — usada em avisos de TWR CLSD."""
    img, draw = _illustration_canvas()
    cx = WIDTH // 2
    base_w = 70
    base_top, base_bottom = HEIGHT * 0.55, HEIGHT * 0.92
    draw.polygon([
        (cx - base_w / 2, base_top), (cx + base_w / 2, base_top),
        (cx + base_w / 2 + 24, base_bottom), (cx - base_w / 2 - 24, base_bottom),
    ], fill=200)
    cab_w, cab_h = 300, 150
    cab_top = base_top - cab_h
    draw.rounded_rectangle([(cx - cab_w / 2, cab_top), (cx + cab_w / 2, base_top + 10)], radius=18, fill=200)
    # janelas
    win_y = cab_top + 34
    for i in range(5):
        x = cx - cab_w / 2 + 30 + i * (cab_w - 60) / 4
        draw.rectangle([(x, win_y), (x + 32, win_y + 40)], fill=20)
    return img


def _navaid_illustration() -> Image.Image:
    """Antena com ondas de rádio — usada em avisos de auxílio de navegação (ILS/VOR/DME/NDB/PAPI) fora de serviço."""
    img, draw = _illustration_canvas()
    cx, base_y = WIDTH // 2, HEIGHT * 0.78
    draw.line([(cx, base_y), (cx, base_y - 260)], fill=200, width=16)
    draw.polygon([(cx - 90, base_y), (cx + 90, base_y), (cx, base_y - 90)], fill=200)
    for radius in (140, 230, 320):
        bbox = [(cx - radius, base_y - 260 - radius), (cx + radius, base_y - 260 + radius)]
        draw.arc(bbox, start=200, end=340, fill=200, width=14)
    return img


_ILLUSTRATION_BUILDERS = {
    "runway": _runway_illustration,
    "tower": _tower_illustration,
    "navaid": _navaid_illustration,
}


def illustration_background(category: str) -> Image.Image:
    builder = _ILLUSTRATION_BUILDERS.get(category, _runway_illustration)
    return duotone(builder().convert("RGB"))


def get_background(category: str) -> Image.Image:
    """category: 'weather' -> satélite REDEMET (com fallback pra ilustração se a API falhar);
    'runway' | 'tower' | 'navaid' -> ilustração correspondente."""
    if category == "weather":
        try:
            img = fetch_satellite_background()
            if img is not None:
                return img
        except requests.RequestException:
            pass
        return illustration_background("navaid")  # fallback genérico se a REDEMET falhar
    return illustration_background(category)


GENERIC_PHOTOS_DIR = os.path.join(PHOTOS_DIR, "generic")
GENERIC_PHOTOS_MANIFEST = os.path.join(GENERIC_PHOTOS_DIR, "manifest.json")

# qual categoria de foto genérica pega melhor cada tipo de aviso, na falta de
# foto curada do aeroporto específico (ver CLAUDE.md "Variedade de foto por
# tipo de aviso") — fila combina com avisos que tendem a atrasar/cancelar,
# aeronave serve de fallback genérico pros demais (clima, aux. navegação)
_GENERIC_CATEGORY_BY_KIND = {
    "rwy_closed": "queue",
    "twr_closed": "queue",
    # posts educativos de fallback (ver fallback_content.py) — variedade de foto por tema
    "edu_rules": "terminal",
    "edu_codes": "terminal",
    "edu_notam_metar": "aircraft",
    "edu_registration": "aircraft",
    "edu_jets": "aircraft",
    "edu_careers": "terminal",
}
_DEFAULT_GENERIC_CATEGORY = "aircraft"


def _manifest_credit(manifest_path: str, key: str) -> str | None:
    if not os.path.isfile(manifest_path):
        return None
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    entry = manifest.get(key)
    return entry["author"] if entry else None


def get_curated_photo(icao: str) -> tuple | None:
    """Foto real curada do aeroporto específico (assets/photos/<ICAO>.jpg), já
    cortada pro tamanho do slide, SEM duotone (mantém a cor natural, como uma
    foto de notícia). Devolve (imagem, crédito_ou_None); None se ainda não
    tivermos foto pra esse aeroporto."""
    path = os.path.join(PHOTOS_DIR, f"{icao}.jpg")
    if not os.path.isfile(path):
        return None
    img = cover_resize(Image.open(path).convert("RGB"))
    return img, _manifest_credit(PHOTOS_MANIFEST, icao)


def get_generic_photo(headline_kind: str | None) -> tuple | None:
    """Foto genérica (não amarrada a um aeroporto específico) da categoria mais
    pertinente ao tipo de aviso — fila de check-in, aeronave, saguão etc.
    Devolve (imagem, crédito_ou_None); None se a categoria ainda não tiver
    nenhuma foto na biblioteca."""
    category = _GENERIC_CATEGORY_BY_KIND.get(headline_kind, _DEFAULT_GENERIC_CATEGORY)
    cat_dir = os.path.join(GENERIC_PHOTOS_DIR, category)
    if not os.path.isdir(cat_dir):
        return None
    files = sorted(f for f in os.listdir(cat_dir) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    if not files:
        return None
    filename = random.choice(files)
    img = cover_resize(Image.open(os.path.join(cat_dir, filename)).convert("RGB"))
    return img, _manifest_credit(GENERIC_PHOTOS_MANIFEST, f"{category}/{filename}")


def get_background_for_post(icao: str, category: str, headline_kind: str | None = None) -> tuple:
    """Ponto de entrada usado pelo slide.py: devolve (imagem, crédito_ou_None).
    Prioridade: foto curada do aeroporto -> foto genérica pertinente à
    categoria do aviso -> satélite (clima) / ilustração (último recurso)."""
    curated = get_curated_photo(icao)
    if curated is not None:
        return curated
    generic = get_generic_photo(headline_kind)
    if generic is not None:
        return generic
    return get_background(category), None


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "output", "backgrounds")
    os.makedirs(out_dir, exist_ok=True)
    for cat in ("weather", "runway", "tower", "navaid"):
        img = get_background(cat)
        path = os.path.join(out_dir, f"{cat}.png")
        img.save(path)
        print(f"{cat}: {path}")
