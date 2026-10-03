"""Generate tileable procedural textures (numpy + Pillow) into materials/textures/.

Run with system python3:  python3 scripts/gen_textures.py
Every texture is periodic so it tiles; 1024 px unless noted (512 for small props).
Outputs *_col.png (sRGB), *_nrm.png (OpenGL tangent normal) and, for cards, RGBA with alpha.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "materials", "textures")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def periodic_noise(n, cells, octaves=4, seed=0):
    """Tileable value noise: sum of bicubic-upsampled periodic random grids."""
    r = np.random.default_rng(seed)
    acc = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        if c > n:
            break
        g = r.random((c, c)).astype(np.float32)
        # periodic bilinear upsample with smoothstep
        t = np.arange(n) * c / n
        i0 = np.floor(t).astype(int) % c
        i1 = (i0 + 1) % c
        f = t - np.floor(t)
        f = f * f * (3 - 2 * f)
        a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
        b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
        acc += amp * (a * (1 - f)[:, None] + b * f[:, None])
        tot += amp
        amp *= 0.5
    return acc / tot


def normal_from_height(h, strength=4.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    # OpenGL convention (+Y up in texture space); image row 0 is top -> flip dy sign
    n = np.stack([-dx / l, dy / l, nz / l], -1)
    return ((n * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)


def save_rgb(name, arr):
    Image.fromarray((arr.clip(0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, name))


def save_nrm(name, h, s=4.0):
    Image.fromarray(normal_from_height(h, s)).save(os.path.join(OUT, name))


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def col(*c):
    return np.array(c, np.float32)


# ---------------------------------------------------------------- flagstones (2 m tile)
def flagstones(n=1024):
    # rows of varying height, stones of varying length (running bond-ish), all periodic
    h = np.zeros((n, n), np.float32)
    tint = np.zeros((n, n), np.float32)
    rows = [0, 180, 330, 520, 680, 850, 1024]
    r = np.random.default_rng(3)
    edge = np.zeros((n, n), np.float32)
    yy, xx = np.mgrid[0:n, 0:n]
    for ri in range(len(rows) - 1):
        y0, y1 = rows[ri], rows[ri + 1]
        x = int(r.integers(0, 300))
        cuts = []
        while True:
            cuts.append(x % n)
            x += int(r.integers(240, 420))
            if x - cuts[0] >= n - 120:
                break
        cuts = sorted(cuts)
        for ci in range(len(cuts)):
            a = cuts[ci]
            b = cuts[(ci + 1) % len(cuts)] + (n if ci == len(cuts) - 1 else 0)
            m = (yy >= y0) & (yy < y1) & (((xx - a) % n) < (b - a))
            tint[m] = r.random()
            # distance to stone edge for bevel
            dxl = (xx - a) % n
            dxr = (b - a) - dxl
            dy0 = yy - y0
            dy1 = y1 - yy
            d = np.minimum(np.minimum(dxl, dxr), np.minimum(dy0, dy1)).astype(np.float32)
            edge[m] = d[m]
    bev = np.clip(edge / 14.0, 0, 1)
    grout = edge < 3
    nz = periodic_noise(n, 8, 5, 11)
    fine = periodic_noise(n, 64, 3, 12)
    h = bev * 0.8 + nz * 0.25 + fine * 0.08
    h[grout] = 0
    base = lerp(col(0.74, 0.60, 0.44), col(0.63, 0.50, 0.36), tint)
    base = lerp(base, col(0.80, 0.69, 0.53), np.clip(nz - 0.45, 0, 1) * 1.6)
    base *= (0.86 + 0.18 * fine)[..., None]
    base = lerp(base, col(0.42, 0.34, 0.26), (1 - bev) * 0.55)
    base[grout] = col(0.36, 0.30, 0.24)
    save_rgb("flagstone_col.png", base)
    save_nrm("flagstone_nrm.png", h, 3.0)


# ---------------------------------------------------------------- ashlar sandstone (2 m tile)
def ashlar(n=1024):
    yy, xx = np.mgrid[0:n, 0:n]
    course = n // 8  # 8 courses per 2 m -> 0.25 m courses
    row = yy // course
    r = np.random.default_rng(5)
    offs = r.integers(0, 256, 8)
    lens = [r.integers(150, 300) for _ in range(8)]
    bx = ((xx + offs[row]) % n)
    blen = np.array(lens)[row]
    bid = bx // blen
    # make last block periodic by snapping width to divide n
    nb = np.round(n / blen).astype(int)
    blen2 = n / nb
    bid = (bx / blen2[...]).astype(int)
    lx = bx - bid * blen2
    ly = yy - row * course
    d = np.minimum(np.minimum(lx, blen2 - lx), np.minimum(ly, course - ly))
    seed = (row * 31 + bid * 7) % 97
    tint = (np.sin(seed * 12.9898) * 43758.5453) % 1.0
    nz = periodic_noise(n, 8, 5, 21)
    fine = periodic_noise(n, 96, 3, 22)
    bev = np.clip(d / 10.0, 0, 1)
    mort = d < 3.5
    h = bev * 0.7 + nz * 0.3 + fine * 0.12
    h[mort] = 0.05
    base = lerp(col(0.80, 0.66, 0.49), col(0.70, 0.56, 0.41), tint)
    base = lerp(base, col(0.86, 0.76, 0.60), np.clip(nz - 0.5, 0, 1) * 1.5)
    base *= (0.85 + 0.2 * fine)[..., None]
    base = lerp(base, col(0.5, 0.42, 0.33), (1 - bev) * 0.4)
    base[mort] = col(0.72, 0.66, 0.56)
    save_rgb("ashlar_col.png", base)
    save_nrm("ashlar_nrm.png", h, 3.0)


# ---------------------------------------------------------------- lime plaster (3 m tile)
def plaster(n=1024):
    nz = periodic_noise(n, 4, 6, 31)
    blot = periodic_noise(n, 3, 3, 32)
    fine = periodic_noise(n, 128, 2, 33)
    base = lerp(col(0.86, 0.76, 0.62), col(0.78, 0.64, 0.49), nz)
    # damp stains towards blot peaks, warm patches
    base = lerp(base, col(0.66, 0.55, 0.43), np.clip(blot - 0.55, 0, 1) * 2.2)
    # spalled patches revealing stone
    spall = np.clip((periodic_noise(n, 6, 4, 34) - 0.70) * 9, 0, 1)
    base = lerp(base, col(0.70, 0.57, 0.42), spall)
    base *= (0.93 + 0.1 * fine)[..., None]
    h = nz * 0.4 + fine * 0.15 - spall * 0.4
    save_rgb("plaster_col.png", base)
    save_nrm("plaster_nrm.png", h, 2.0)


# ---------------------------------------------------------------- turquoise zellige band (1 m tile)
def tiles(n=512):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cell = n / 8
    cx = (xx % cell) / cell - 0.5
    cy = (yy % cell) / cell - 0.5
    cid = (xx // cell) + 8 * (yy // cell)
    tint = (np.sin(cid * 7.13) * 43758.5) % 1
    r = np.sqrt(cx * cx + cy * cy)
    ring = (np.abs(r - 0.28) < 0.05) | (r < 0.09)
    diamond = (np.abs(cx) + np.abs(cy)) < 0.5
    edge = np.maximum(np.abs(cx), np.abs(cy)) > 0.46
    base = lerp(col(0.05, 0.47, 0.52), col(0.10, 0.58, 0.62), tint)
    base[~diamond] = lerp(col(0.06, 0.25, 0.42), col(0.10, 0.32, 0.50), tint)[~diamond]
    base[ring] = col(0.90, 0.88, 0.80)
    base[edge] = col(0.80, 0.76, 0.68)
    fine = periodic_noise(n, 32, 2, 41)
    base *= (0.92 + 0.12 * fine)[..., None]
    h = np.where(edge, 0.0, 1.0) * 0.6 + ring * 0.05 + fine * 0.05
    save_rgb("tile_col.png", base)
    save_nrm("tile_nrm.png", h, 3.0)


# ---------------------------------------------------------------- dark timber (1 m tile)
def timber(n=512):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    plank = n / 4
    pid = (xx // plank)
    tint = (np.sin(pid * 3.7) * 1000) % 1
    grain = periodic_noise(n, 4, 4, 51)
    streak = np.sin((xx / plank * 6.283 * 3) + grain * 18 + yy / n * 6.283) * 0.5 + 0.5
    base = lerp(col(0.22, 0.13, 0.08), col(0.33, 0.21, 0.12), streak * 0.6 + tint * 0.4)
    gap = (xx % plank) < 3
    base[gap] = col(0.08, 0.05, 0.03)
    h = streak * 0.2 + np.where(gap, 0, 0.8)
    save_rgb("timber_col.png", base)
    save_nrm("timber_nrm.png", h, 2.5)


# ---------------------------------------------------------------- aged copper (2 m tile)
def copper(n=512):
    nz = periodic_noise(n, 4, 5, 61)
    pat = np.clip((periodic_noise(n, 8, 4, 62) - 0.22) * 2.6, 0, 1)
    base = lerp(col(0.62, 0.32, 0.18), col(0.30, 0.62, 0.52), pat)
    base *= (0.85 + 0.25 * nz)[..., None]
    # standing seams
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    seam = (xx % (n / 6)) < 4
    base[seam] *= 0.7
    rough = 0.35 + 0.5 * pat
    Image.fromarray((rough * 255).astype(np.uint8)).save(os.path.join(OUT, "copper_rgh.png"))
    save_rgb("copper_col.png", base)
    save_nrm("copper_nrm.png", nz * 0.3 + np.where(seam, 1.0, 0.0), 2.0)


# ---------------------------------------------------------------- terracotta (1 m tile)
def terracotta(n=512):
    nz = periodic_noise(n, 6, 5, 71)
    base = lerp(col(0.66, 0.30, 0.17), col(0.52, 0.22, 0.13), nz)
    blot = np.clip((periodic_noise(n, 4, 3, 72) - 0.6) * 3, 0, 1)
    base = lerp(base, col(0.62, 0.55, 0.45), blot * 0.6)  # lime bloom
    save_rgb("terracotta_col.png", base)
    save_nrm("terracotta_nrm.png", nz * 0.4, 2.0)


# ---------------------------------------------------------------- fabric stripes
def stripes(name, c1, c2, n=512, count=8):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    s = ((xx // (n / count)) % 2).astype(np.float32)
    weave = periodic_noise(n, 64, 2, 81)
    fade = periodic_noise(n, 2, 3, 82)
    base = lerp(col(*c1), col(*c2), s)
    base *= (0.9 + 0.12 * weave)[..., None]
    base = lerp(base, col(0.9, 0.85, 0.75), fade * 0.2)
    save_rgb(name, base)


# ---------------------------------------------------------------- airship patchwork
def patchwork(n=1024):
    img = Image.new("RGB", (n, n))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(91)
    pal = [(196, 160, 110), (170, 92, 62), (214, 190, 140), (96, 128, 120), (150, 110, 70),
           (200, 170, 90), (120, 70, 50), (225, 205, 170), (60, 110, 120), (180, 130, 90)]
    cols = 8
    w = n // cols
    for ci in range(cols):
        y = 0
        while y < n:
            hgt = int(r.integers(70, 200))
            if y + hgt > n - 40:
                hgt = n - y
            c = pal[int(r.integers(0, len(pal)))]
            d.rectangle([ci * w, y, ci * w + w, y + hgt], fill=c)
            y += hgt
    a = np.asarray(img).astype(np.float32) / 255
    yy, xx = np.mgrid[0:n, 0:n]
    seam = ((xx % w) < 3)
    a[seam] *= 0.55
    # horizontal seams via colour change detection
    dif = np.abs(np.diff(a.mean(-1), axis=0, append=a[:1].mean(-1))) > 0.02
    dif = dif | np.roll(dif, 1, 0)
    a[dif] *= 0.6
    weave = periodic_noise(n, 128, 2, 92)
    a *= (0.9 + 0.15 * weave)[..., None]
    # stitch dashes
    st = seam & ((yy // 8) % 2 == 0)
    a[np.roll(st, 5, 1)] = 0.85
    save_rgb("patchwork_col.png", a)
    h = 1 - (seam | dif).astype(np.float32) * 0.8
    save_nrm("patchwork_nrm.png", h + weave * 0.1, 3.0)


# ---------------------------------------------------------------- foliage cards (RGBA)
def leaf_card(name, n=1024, leaf_rgb=((0.12, 0.26, 0.08), (0.30, 0.45, 0.14)), fruit=None,
              flower=None, leaf_len=(26, 46), count=900, shape="ellipse", seed=101, density=0.92):
    r = np.random.default_rng(seed)
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = n / 2, n / 2
    # twigs
    for _ in range(14):
        ang = r.uniform(0, 6.283)
        L = r.uniform(0.2, 0.45) * n
        d.line([cx, cy + n * 0.25, cx + np.cos(ang) * L, cy + np.sin(ang) * L * 0.8],
               fill=(60, 42, 28, 255), width=5)
    for i in range(count):
        # leaves clustered in a blob, sparser to edges
        rr = np.sqrt(r.random()) * 0.47 * n * density
        a = r.uniform(0, 6.283)
        x, y = cx + np.cos(a) * rr, cy + np.sin(a) * rr * 0.9
        t = r.random()
        shade = 0.55 + 0.45 * (1 - (y / n)) * 0.6 + 0.25 * r.random()
        c0, c1 = np.array(leaf_rgb[0]), np.array(leaf_rgb[1])
        c = (c0 + (c1 - c0) * t) * shade
        c = tuple(int(v * 255) for v in np.clip(c, 0, 1)) + (255,)
        ll = r.uniform(*leaf_len)
        lw = ll * (0.42 if shape == "ellipse" else 0.18)
        ang = r.uniform(0, 3.1416)
        pts = []
        for k in range(10):
            th = k / 10 * 6.283
            px, py = np.cos(th) * ll / 2, np.sin(th) * lw / 2 * (1 - 0.3 * np.cos(th))
            pts.append((x + px * np.cos(ang) - py * np.sin(ang), y + px * np.sin(ang) + py * np.cos(ang)))
        d.polygon(pts, fill=c)
        # midrib highlight
        d.line([pts[0], pts[5]], fill=tuple(min(255, int(v * 1.25)) for v in c[:3]) + (255,), width=1)
    if fruit:
        for _ in range(fruit[1]):
            rr = np.sqrt(r.random()) * 0.42 * n
            a = r.uniform(0, 6.283)
            x, y = cx + np.cos(a) * rr, cy + np.sin(a) * rr * 0.9
            s = r.uniform(12, 18)
            base = np.array(fruit[0])
            d.ellipse([x - s, y - s, x + s, y + s], fill=tuple(int(v * 255) for v in base) + (255,))
            d.ellipse([x - s * 0.5, y - s * 0.7, x + s * 0.1, y - s * 0.1],
                      fill=tuple(int(min(1, v * 1.35) * 255) for v in base) + (255,))
    if flower:
        for _ in range(flower[1]):
            rr = np.sqrt(r.random()) * 0.46 * n
            a = r.uniform(0, 6.283)
            x, y = cx + np.cos(a) * rr, cy + np.sin(a) * rr * 0.9
            s = r.uniform(8, 16)
            fc = np.array(flower[0]) * r.uniform(0.75, 1.1)
            d.regular_polygon((x, y, s), 3, rotation=r.uniform(0, 120),
                              fill=tuple(int(min(1, v) * 255) for v in fc) + (255,))
    img = img.filter(ImageFilter.SMOOTH)
    img.save(os.path.join(OUT, name))


def strand_card(name, n=512, seed=111):
    """Trailing ivy strands hanging down: 512x1024 RGBA."""
    r = np.random.default_rng(seed)
    w, h = n, n * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for s in range(7):
        x = r.uniform(0.15, 0.85) * w
        L = r.uniform(0.55, 1.0) * h
        y = 0
        while y < L:
            x += r.uniform(-4, 4)
            y += 6
            d.line([x, y - 6, x, y], fill=(50, 70, 30, 255), width=3)
            if r.random() < 0.5:
                s_ = r.uniform(10, 20) * (1 - y / h * 0.5)
                c = (int(r.uniform(30, 70)), int(r.uniform(80, 120)), int(r.uniform(25, 45)), 255)
                ox = r.choice([-1, 1]) * s_ * 0.6
                d.ellipse([x + ox - s_ / 2, y - s_ / 3, x + ox + s_ / 2, y + s_ / 3], fill=c)
    img.filter(ImageFilter.SMOOTH).save(os.path.join(OUT, name))


def palm_frond(name, n=1024, seed=121):
    """Frond seen from above: stem along X, leaflets both sides. RGBA."""
    r = np.random.default_rng(seed)
    img = Image.new("RGBA", (n, n // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cy = n // 8
    d.line([0, cy, n, cy], fill=(90, 80, 40, 255), width=6)
    for i in range(60):
        x = 20 + i * (n - 40) / 60
        L = (n // 8 - 6) * np.sin(np.pi * (0.15 + 0.85 * i / 60)) * r.uniform(0.85, 1.0)
        for sgn in (-1, 1):
            c = (int(r.uniform(50, 80)), int(r.uniform(95, 125)), int(r.uniform(30, 45)), 255)
            d.polygon([(x, cy), (x + 22, cy + sgn * L), (x + 10, cy + sgn * L * 0.95), (x - 6, cy)], fill=c)
    img.filter(ImageFilter.SMOOTH).save(os.path.join(OUT, name))


def grass_card(name, n=512, seed=131):
    r = np.random.default_rng(seed)
    img = Image.new("RGBA", (n, n // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(140):
        x = r.uniform(10, n - 10)
        hgt = r.uniform(0.4, 1.0) * n / 2
        bend = r.uniform(-30, 30)
        c = (int(r.uniform(70, 120)), int(r.uniform(100, 140)), int(r.uniform(35, 60)), 255)
        d.polygon([(x - 3, n / 2), (x + 3, n / 2), (x + bend, n / 2 - hgt)], fill=c)
    img.save(os.path.join(OUT, name))


if __name__ == "__main__":
    flagstones(); print("flagstones")
    ashlar(); print("ashlar")
    plaster(); print("plaster")
    tiles(); print("tiles")
    timber(); print("timber")
    copper(); print("copper")
    terracotta(); print("terracotta")
    stripes("awning_blue_col.png", (0.92, 0.89, 0.80), (0.10, 0.36, 0.52))
    stripes("awning_red_col.png", (0.92, 0.89, 0.80), (0.66, 0.16, 0.12))
    stripes("awning_ochre_col.png", (0.90, 0.80, 0.55), (0.70, 0.45, 0.15))
    patchwork(); print("patchwork")
    leaf_card("leaf_orange.png", leaf_rgb=((0.07, 0.17, 0.05), (0.20, 0.34, 0.10)), fruit=((0.95, 0.48, 0.06), 34), seed=101, count=1900, leaf_len=(30, 54))
    leaf_card("leaf_olive.png", leaf_rgb=((0.25, 0.32, 0.20), (0.48, 0.55, 0.38)),
              shape="narrow", seed=102, count=1300)
    leaf_card("leaf_bougainvillea.png", leaf_rgb=((0.12, 0.25, 0.08), (0.25, 0.40, 0.12)),
              flower=((0.85, 0.12, 0.48), 520), seed=103, count=500)
    leaf_card("leaf_shrub.png", leaf_rgb=((0.10, 0.22, 0.07), (0.22, 0.38, 0.12)), seed=104,
              count=1400, leaf_len=(16, 30), n=512)
    leaf_card("leaf_cypress.png", leaf_rgb=((0.04, 0.10, 0.04), (0.12, 0.22, 0.08)), seed=105,
              count=2200, leaf_len=(10, 22), n=512, shape="narrow", density=1.0)
    strand_card("leaf_ivy.png")
    palm_frond("palm_frond.png")
    grass_card("grass.png")
    print("done ->", os.path.abspath(OUT))
