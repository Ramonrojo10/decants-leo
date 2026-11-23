#!/usr/bin/env python3
"""Split Leo's Daytona (round chronograph) photos into builder layers.

Input : fotos-leo/daytona/originales/dt-NN-*.webp   (765x1024 studio photos, front-ish views)
Output: public/builder/leo/daytona/{case,dial,strap}-dt-NN.webp + shadowdial.webp
        fotos-leo/daytona/partes/{catalogo,mezclas}.jpg   (review sheets)

Same convention as the Santos work (scripts/builder/leo_santos_split.py):
canvas 1000x2000 RGBA, 1000 px = 48 mm, dial centre at (500,1000), layers
strap / dial / shadowdial / case stacked in that order.

 * Every photo is first warped with an affine map that turns the fitted inner edge of the
   bezel (an ellipse, because the photos are slightly tilted) into a true circle of radius R
   centred on (500,1000)  -> the dial is upright and identical in every photo.
 * case  = case + bezel + crown + pushers. The dial opening (R - OPEN_IN) and the strap zones
           above / below the lugs (and the strap band between the lug horns, up to the bezel)
           are transparent.
 * dial  = everything inside the bezel, cut with the canonical circle R - DIAL_IN (a bit
           larger than the case opening so it tucks under the bezel lip).
 * strap = everything beyond the lug seams (rows CT / CB) plus the band between the horns
           up to the outer bezel arc (smeared under the bezel), width = canonical lug width,
           faded at both ends.

Run (venv with Pillow/NumPy/OpenCV):  python scripts/builder/leo_daytona_split.py [export|sheets|all]
"""
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRCD = os.path.join(ROOT, "fotos-leo", "daytona")
OUT = os.path.join(SRCD, "partes")
WEB = os.path.join(ROOT, "public", "builder", "leo", "daytona")
Q = 85
CW, CH = 1000, 2000
CX, CY = 500, 1000
R = 300.0                 # canonical dial radius (inner edge of the bezel), 600 px = 28.8 mm
OPEN_IN = 7.0             # case opening radius = R - OPEN_IN (keeps the lip of the bezel)
DIAL_IN = 1.5             # dial cut radius = R - DIAL_IN (tucks under the lip)
ARC_A = 520.0             # horizontal radius of the outer bezel arc model (flat top, measured on the photos)
EROSION = {}              # source-edge erosion (px), default 2

CASE_IDS = ["02", "07", "01", "08", "05", "14", "15", "11", "10"]
DIAL_IDS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14"]
STRAP_IDS = ["02", "11", "08"]
ALL_IDS = ["%02d" % k for k in range(1, 16)]
RUBBER = {"01", "05", "08", "10"}   # photos that carry a rubber (Oysterflex) strap

# hand guesses (cx, cy, r) of the inner bezel edge in source pixels (seed of the ellipse fit)
GUESS = {
    '01': (398, 472, 188), '02': (383, 451, 175), '03': (425, 485, 190), '04': (388, 468, 175),
    '05': (383, 477, 175), '06': (387, 482, 195), '07': (385, 502, 178), '08': (402, 488, 184),
    '09': (384, 453, 160), '10': (390, 479, 178), '11': (388, 479, 185), '12': (398, 485, 193),
    '13': (385, 497, 190), '14': (408, 500, 195), '15': (395, 485, 195),
}
# outer bezel edge at the centre column, in the warped (canonical) space: (top row, bottom row)
# (read by hand from zoomed crops; only needed for the photos used as case / strap)
BEZ = {
    '01': (614, 1378), '02': (649, 1374), '05': (627, 1402), '07': (633, 1384), '08': (634, 1382),
    '10': (634, 1372), '11': (650, 1366), '14': (642, 1371), '15': (629, 1372),
}


def src_path(i):
    return glob.glob(os.path.join(SRCD, "originales", f"dt-{i}-*"))[0]


# ----------------------------------------------------------------------------- mask
def fg_mask(rgb):
    """Hard foreground mask: flood fill of 'smooth near-white' from the borders."""
    f = rgb.astype(np.float32)
    lum = f.mean(2)
    sat = f.max(2) - f.min(2)
    g = cv2.GaussianBlur(lum, (0, 0), 1.5)
    grad = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) / 8
    cand = ((lum >= 206) & (sat < 14) & (grad < 5)).astype(np.uint8)
    n, lab = cv2.connectedComponents(cand, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = (~np.isin(lab, list(border))).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    fg = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
    cnt, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(fg)
    cv2.drawContours(out, cnt, -1, 1, -1)
    return out


def extend_colors(rgb, valid, iters):
    img = rgb.astype(np.float32)
    v = valid.astype(np.float32)
    acc = img * v[..., None]
    w = v.copy()
    for _ in range(iters):
        a = cv2.blur(acc, (3, 3))
        b = cv2.blur(w, (3, 3))
        new = a / np.maximum(b, 1e-6)[..., None]
        fill = (w < 0.5) & (b > 1e-6)
        img = np.where(fill[..., None], new, img)
        w = np.where(fill, 1.0, w)
        acc = img * w[..., None]
    return img


def ramp(v, a, b):
    return np.clip((v - a) / (b - a), 0, 1)


# ----------------------------------------------------------------------------- ellipse fit
def fit_inner(rgb, g, span=0.14, n=180):
    """Inner bezel edge: strongest radial colour edge near the seed circle, robust ellipse fit."""
    cx, cy, r = g
    f = cv2.GaussianBlur(rgb.astype(np.float32), (0, 0), 1.2)
    lab = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    ts = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rs = np.linspace(r * (1 - span), r * (1 + span), 60)
    pts = []
    for t in ts:
        xs = (cx + rs * np.cos(t)).astype(np.float32)[None]
        ys = (cy + rs * np.sin(t)).astype(np.float32)[None]
        prof = np.stack([cv2.remap(lab[..., c], xs, ys, cv2.INTER_LINEAR)[0] for c in range(3)], 1)
        d = np.linalg.norm(np.diff(prof, axis=0), axis=1)
        d = d * (1 - 0.5 * np.abs(rs[:-1] - r) / (r * span))
        k = int(np.argmax(d))
        pts.append((cx + rs[k] * np.cos(t), cy + rs[k] * np.sin(t)))
    pts = np.array(pts, np.float32)
    keep = np.ones(len(pts), bool)
    for _ in range(4):
        (ex, ey), (ma, mi), ang = cv2.fitEllipse(pts[keep])
        a = np.deg2rad(ang)
        d = pts - [ex, ey]
        u = d[:, 0] * np.cos(a) + d[:, 1] * np.sin(a)
        v = -d[:, 0] * np.sin(a) + d[:, 1] * np.cos(a)
        res = np.abs(np.hypot(u / (ma / 2), v / (mi / 2)) - 1) * (ma + mi) / 4
        keep = res < max(2.0, np.percentile(res, 70) * 1.5)
    return cv2.fitEllipse(pts[keep])


def affine_to_circle(ell):
    """2x3 map src -> canonical: fitted ellipse becomes the circle R centred on (500,1000)."""
    (ex, ey), (ma, mi), ang = ell
    a = np.deg2rad(ang)
    c, s = np.cos(a), np.sin(a)
    Rm = np.array([[c, s], [-s, c]])
    L = Rm.T @ np.diag([R / (ma / 2), R / (mi / 2)]) @ Rm
    t = np.array([CX, CY]) - L @ np.array([ex, ey])
    return np.hstack([L, t[:, None]]).astype(np.float64)


# ----------------------------------------------------------------------------- measures
def find_cuts(m, win):
    """Seam rows = where the case outline flares out from the strap/lug block."""
    l, t, r, b = win
    H = b - t
    x0 = max(0, int(l - 0.5 * (r - l)))
    x1 = int(r + 0.02 * (r - l))
    wid = np.zeros(m.shape[0], np.float32)
    for y in range(m.shape[0]):
        xs = np.where(m[y, x0:x1])[0]
        wid[y] = (xs[-1] - xs[0] + 1) if len(xs) else 0
    wid = cv2.GaussianBlur(wid[:, None], (1, 0), sigmaX=0.1, sigmaY=2.0)[:, 0]
    d = np.gradient(wid)
    thr_hi = 0.005 * (r - l)
    thr_lo = 0.0018 * (r - l)
    res = []
    for sgn in (-1, 1):
        y = int((t if sgn < 0 else b) + sgn * 0.02 * H)
        seen = False
        while 5 < y < len(wid) - 6:
            g = -sgn * d[y]
            if g > thr_hi:
                seen = True
            elif seen and g < thr_lo:
                break
            y += sgn
        res.append(y)
    return res


def strip_fit(m, y0, y1):
    """Straight-sided strap strip from the widest rows of the mask between y0..y1 (robust to
    the white holes that bright steel links leave in the mask). Returns line coeffs l(y), r(y)."""
    ys, ls, rs = [], [], []
    for y in range(min(y0, y1), max(y0, y1)):
        xs = np.where(m[y, 250:750])[0]
        if len(xs):
            ys.append(y); ls.append(xs[0] + 250); rs.append(xs[-1] + 250)
    ys, ls, rs = map(np.array, (ys, ls, rs))
    w = rs - ls
    ok = w >= 0.93 * np.percentile(w, 90)
    return np.polyfit(ys[ok], ls[ok], 1), np.polyfit(ys[ok], rs[ok], 1)


def analyse(i):
    rgb = np.array(Image.open(src_path(i)).convert("RGB"))
    ell = fit_inner(rgb, GUESS[i])
    M = affine_to_circle(ell)
    fg = fg_mask(rgb)
    a = dict(id=i, rgb=rgb, fg=fg, M=M, Minv=cv2.invertAffineTransform(M))
    if i in BEZ:
        wm = (cv2.warpAffine(fg * 255, M, (CW, CH), flags=cv2.INTER_LINEAR) > 127).astype(np.uint8)
        ct, cb = find_cuts(wm, (CX - R, CY - R, CX + R, CY + R))
        lt, rt = strip_fit(wm, ct - 220, ct - 30)
        lb, rb = strip_fit(wm, cb + 30, cb + 220)
        wt_ = np.polyval(rt, ct) - np.polyval(lt, ct)
        wb_ = np.polyval(rb, cb) - np.polyval(lb, cb)
        a.update(wm=wm, ct=ct, cb=cb, lt=lt, rt=rt, lb=lb, rb=rb, ls=(wt_ + wb_) / 2,
                 ctc=(np.polyval(rt, ct) + np.polyval(lt, ct)) / 2,
                 cbc=(np.polyval(rb, cb) + np.polyval(lb, cb)) / 2,
                 btop=BEZ[i][0], bbot=BEZ[i][1])
    return a


# ----------------------------------------------------------------------------- piecewise map
def piece_arrays(a, canon):
    """Per canvas row: source row (warped space), horizontal scale and strap centre."""
    CT, CB = canon["CT"], canon["CB"]
    ss = canon["lug"] / a["ls"]
    bt, bb = a["btop"], a["bbot"]
    Y = np.arange(CH, dtype=np.float64)
    yw = np.empty(CH); hs = np.empty(CH); xc = np.empty(CH)
    for k, yy in enumerate(Y):
        if yy < CT:
            yw[k] = a["ct"] - (CT - yy) / ss; hs[k] = ss; xc[k] = a["ctc"]
        elif yy < bt:
            u = (yy - CT) / (bt - CT)
            yw[k] = a["ct"] + u * (bt - a["ct"]); hs[k] = ss + u * (1 - ss); xc[k] = a["ctc"] + u * (CX - a["ctc"])
        elif yy <= bb:
            yw[k] = yy; hs[k] = 1.0; xc[k] = CX
        elif yy < CB:
            u = (yy - bb) / (CB - bb)
            yw[k] = bb + u * (a["cb"] - bb); hs[k] = 1 + u * (ss - 1); xc[k] = CX + u * (a["cbc"] - CX)
        else:
            yw[k] = a["cb"] + (yy - CB) / ss; hs[k] = ss; xc[k] = a["cbc"]
    return Y, yw, hs, xc


def arcs(bt, bb, shift=0.0):
    """Outer bezel arc rows (top, bottom) per canvas column, elliptical model."""
    X = np.arange(CW, dtype=np.float64)
    k = np.sqrt(np.clip(1 - ((X - CX) / ARC_A) ** 2, 0, 1))
    return CY - (CY - bt - shift) * k, CY + (bb + shift - CY) * k


def canvas_maps(a, canon, clamp_arcs=None, xclamp=None):
    """Inverse maps canvas -> warped space for case/strap photos.
    clamp_arcs = (top, bottom) rows per column beyond which rows repeat (smear under the bezel);
    xclamp = half width beyond which, inside the case zone, the columns repeat sideways."""
    Y, yw, hs, xc = piece_arrays(a, canon)
    X = np.arange(CW, dtype=np.float64)
    yy = np.repeat(Y[:, None], CW, 1)
    if clamp_arcs is not None:
        at, ab = clamp_arcs
        yy = np.where(yy < CY, np.minimum(yy, at[None, :]), np.maximum(yy, ab[None, :]))
    Xe = np.repeat(X[None, :], CH, 0)
    if xclamp is not None:
        inz = (Y >= canon["CT"] - 1) & (Y <= canon["CB"] + 1)
        Xe = np.where(inz[:, None], np.clip(Xe, CX - xclamp, CX + xclamp), Xe)
    wy = np.interp(yy, Y, yw)
    h = np.interp(yy, Y, hs)
    c = np.interp(yy, Y, xc)
    wx = c + (Xe - CX) / h
    return wx, wy


def identity_maps():
    X, Y = np.meshgrid(np.arange(CW, dtype=np.float64), np.arange(CH, dtype=np.float64))
    return X, Y


def sample(a, wx, wy, kind):
    """Warped-space coords -> source pixels -> sampled colour (kind 'rgb') or float mask."""
    Mi = a["Minv"]
    sx = (Mi[0, 0] * wx + Mi[0, 1] * wy + Mi[0, 2]).astype(np.float32)
    sy = (Mi[1, 0] * wx + Mi[1, 1] * wy + Mi[1, 2]).astype(np.float32)
    if kind == "rgb":
        return cv2.remap(a["rgb"], sx, sy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return cv2.remap(a["fgsoft"], sx, sy, cv2.INTER_LINEAR, borderValue=0)


def sharpen(col):
    bl = cv2.GaussianBlur(col, (0, 0), 1.3)
    return np.clip(col + 0.4 * (col - bl), 0, 255)


def disc(r, ss=4):
    im = Image.new("L", (CW * ss, CH * ss), 0)
    ImageDraw.Draw(im).ellipse([(CX - r) * ss, (CY - r) * ss, (CX + r) * ss - 1, (CY + r) * ss - 1], fill=255)
    return np.asarray(im.resize((CW, CH), Image.LANCZOS), np.float32) / 255.0


# ----------------------------------------------------------------------------- layers
def dial_layer(a):
    wx, wy = identity_maps()
    col = sharpen(sample(a, wx, wy, "rgb").astype(np.float32))
    return to_rgba(col, disc(R - DIAL_IN))


def strip_alpha(a):
    """Warped-space strap strip (straight sides, inset 2 px, valid rows only)."""
    h, w = CH, CW
    yy = np.arange(h, dtype=np.float64)[:, None]
    xx = np.arange(w, dtype=np.float64)[None, :]
    out = np.zeros((h, w), np.float32)
    for sgn in (-1, 1):
        lo, ro = (a["lt"], a["rt"]) if sgn < 0 else (a["lb"], a["rb"])
        ref = a["ct"] if sgn < 0 else a["cb"]
        L = np.polyval(lo, yy) + 2.5
        Rr = np.polyval(ro, yy) - 2.5
        zone = (yy < ref) if sgn < 0 else (yy >= ref)
        # strap extent along y: rows where the centre columns still hold foreground
        col = a["wm"][:, 490:510].mean(1) > 0.5
        rows = np.where(col & ((np.arange(h) < ref) if sgn < 0 else (np.arange(h) >= ref)))[0]
        if len(rows) == 0:
            continue
        lim = rows.min() if sgn < 0 else rows.max()
        valid = (yy >= lim) if sgn < 0 else (yy <= lim)
        inside = ramp(xx, L - 0.5, L + 0.5) * (1 - ramp(xx, Rr - 0.5, Rr + 0.5))
        out = np.maximum(out, (inside * zone * valid).astype(np.float32))
    return out


def case_layer(a, canon, ext=None):
    """Case + bezel + crown + pushers. ext (half-width per row) enables the removal of the
    rubber strap pixels that show inside the horns of photos that carry a rubber strap."""
    CT, CB = canon["CT"], canon["CB"]
    lw = canon["lug"] / 2
    yy = np.arange(CH, dtype=np.float32)[:, None]
    xx = np.arange(CW, dtype=np.float32)[None, :]
    wx, wy = canvas_maps(a, canon)
    a["fgsoft"] = cv2.GaussianBlur(cv2.erode(a["fg"], np.ones((3, 3), np.uint8), iterations=EROSION.get(a["id"], 2)).astype(np.float32), (0, 0), 0.8)
    rgb = sample(a, wx, wy, "rgb")
    al = np.clip((sample(a, wx, wy, "mask") - 0.55) / 0.3, 0, 1)
    valid = (al > 0.98).astype(np.uint8)
    col = sharpen(np.clip(extend_colors(rgb, cv2.erode(valid, np.ones((3, 3), np.uint8)), 6), 0, 255))
    opening = disc(R - OPEN_IN)
    zone_case = ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, CB - 0.5, CB + 0.5))
    band_w = 1 - ramp(np.abs(xx - CX), lw - 2, lw - 1)
    t_arc, b_arc = arcs(a["btop"], a["bbot"], 0.0)
    t_arc = t_arc[None, :] - 3
    b_arc = b_arc[None, :] + 3
    rows_t = ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, t_arc - 0.5, t_arc + 0.5))
    rows_b = ramp(yy, b_arc - 0.5, b_arc + 0.5) * (1 - ramp(yy, CB - 0.5, CB + 0.5))
    cut = np.clip(band_w * (rows_t + rows_b), 0, 1)
    if ext is not None and a["id"] in RUBBER:
        lum = col.mean(2)
        sat = col.max(2) - col.min(2)
        rub = ((lum < 90) & (sat < 35)).astype(np.float32)
        rub = cv2.dilate(rub, np.ones((3, 3), np.uint8))
        e = np.clip(ext, lw + 3, lw + 70)[:, None]
        zone = np.clip(rows_t + rows_b, 0, 1) * (np.abs(xx - CX) < lw + 110)
        side = (1 - ramp(np.abs(xx - CX), e - 1, e)) * zone
        cut = np.maximum(cut, np.clip(rub * side, 0, 1))
        # rubber left outside the strap band (beyond what any case silhouette allows): fill from
        # the neighbouring horn metal so no black notch is left beside a bracelet
        hole = (rub * zone * (1 - side) > 0.5).astype(np.uint8)
        if hole.any():
            hole = cv2.dilate(hole, np.ones((5, 5), np.uint8))
            col = cv2.inpaint(np.clip(col, 0, 255).astype(np.uint8), hole, 6, cv2.INPAINT_TELEA).astype(np.float32)
    case_a = al * zone_case * (1 - opening) * (1 - cut)
    return to_rgba(col, case_a)


def case_ext(cases):
    """Half-width per row up to which a strap may show beside the lug band: never wider than the
    narrowest case silhouette (so it can't poke out of any case)."""
    ext = np.full(CH, 1e9)
    for im in cases.values():
        al = np.array(im)[..., 3] > 128
        for y in range(CH):
            xs = np.where(al[y])[0]
            if len(xs):
                ext[y] = min(ext[y], CX - xs.min() - 4, xs.max() - CX - 4)
            else:
                ext[y] = 0.0
    return np.clip(ext, 0, 1e9)


def strap_layer(a, canon, deep, ext):
    CT, CB = canon["CT"], canon["CB"]
    lw = canon["lug"] / 2
    yy = np.arange(CH, dtype=np.float32)[:, None]
    xx = np.arange(CW, dtype=np.float32)[None, :]
    Xs = np.arange(CW, dtype=np.float64)
    k = np.sqrt(np.clip(1 - ((Xs - CX) / ARC_A) ** 2, 0, 1))
    if a["id"] in RUBBER:      # smooth strap: repeat the rows just beyond the seam through the band
        at = np.full(CW, CT - 6.0)
        ab = np.full(CW, CB + 6.0)
    else:                      # bracelet: end link as photographed, repeat rows under the own bezel arc
        at = CY - (CY - a["btop"] + 8) * k
        ab = CY + (a["bbot"] - 8 - CY) * k
    wx, wy = canvas_maps(a, canon, (at, ab), xclamp=lw - 3)
    col = sharpen(np.clip(sample(a, wx, wy, "rgb").astype(np.float32), 0, 255))
    sa = strip_alpha(a)
    wxs, wys = canvas_maps(a, canon)
    sa_c = cv2.remap(sa, wxs.astype(np.float32), wys.astype(np.float32), cv2.INTER_LINEAR, borderValue=0)
    zone_case = ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, CB - 0.5, CB + 0.5))
    dt, db = deep
    dtop, dbot = arcs(dt, db, 0.0)
    e = np.clip(ext, lw + 3, lw + 70)[:, None]
    band_s = 1 - ramp(np.abs(xx - CX), e - 1, e)
    rows_s = (ramp(yy, CT - 3.5, CT - 2.5) * (1 - ramp(yy, dtop[None, :] + 0.5, dtop[None, :] + 1.5))
              + ramp(yy, dbot[None, :] - 1.5, dbot[None, :] - 0.5) * (1 - ramp(yy, CB + 2.5, CB + 3.5)))
    strap_a = np.maximum(sa_c * (1 - zone_case), np.clip(rows_s * band_s, 0, 1))
    rows = np.where(strap_a.max(1) > 0.5)[0]
    top_end, bot_end = rows[0], rows[-1]
    fade = 150.0
    f_top = ramp(yy, top_end, top_end + fade)
    f_bot = 1 - ramp(yy, bot_end - fade, bot_end)
    strap_a = strap_a * np.where(yy < CY, f_top, f_bot)
    return to_rgba(col, strap_a)


def to_rgba(col, alpha):
    return Image.fromarray(np.dstack([col.astype(np.uint8), (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)]), "RGBA")


def shadow_layer():
    ins = disc(R - OPEN_IN + 2)
    outside = 1 - ins
    M = np.float32([[1, 0, 3], [0, 1, 6]])
    sh = cv2.GaussianBlur(cv2.warpAffine(outside, M, (CW, CH), borderValue=1), (0, 0), 8)
    near = cv2.GaussianBlur(outside, (0, 0), 3)
    a = np.clip(0.34 * sh * ins + 0.09 * near * ins, 0, 0.45)
    return Image.fromarray(np.dstack([np.zeros((CH, CW, 3), np.uint8), (a * 255).astype(np.uint8)]), "RGBA")


def stack(layers):
    base = Image.new("RGBA", (CW, CH), (255, 255, 255, 255))
    for im in layers:
        base.alpha_composite(im)
    return base


# ----------------------------------------------------------------------------- main
MIXES = [
    ("11", "12", "08", "oro rosa arcoiris + blanco + hule"),
    ("15", "08", "11", "acero baguettes + champagne + brazalete oro rosa"),
    ("01", "04", "02", "oro amarillo + arabe celeste + brazalete acero"),
    ("07", "10", "08", "acero ceramica + jirafa + hule"),
    ("14", "09", "02", "acero arcoiris + negro arcoiris + acero"),
    ("05", "11", "11", "oro rosa negro + pave + brazalete oro rosa"),
    ("02", "06", "08", "acero + arabe azul + hule"),
    ("08", "03", "02", "oro amarillo negro + panda + acero"),
]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    A = {i: analyse(i) for i in ALL_IDS}
    parts = [i for i in ALL_IDS if i in BEZ]
    canon = dict(lug=float(np.median([A[i]["ls"] for i in parts])),
                 CT=float(np.median([A[i]["ct"] for i in parts])),
                 CB=float(np.median([A[i]["cb"] for i in parts])))
    print("canon", canon, "R", R)
    for i in parts:
        a = A[i]
        print(i, "ct", a["ct"], "cb", a["cb"], "lug", round(a["ls"]), "btop/bbot", a["btop"], a["bbot"])
    deep = (max(v[0] for v in BEZ.values()) + 12, min(v[1] for v in BEZ.values()) - 12)
    os.makedirs(OUT, exist_ok=True)
    shadow = shadow_layer()
    L = {}
    for i in ALL_IDS:
        L[i] = {}
        if i in DIAL_IDS:
            L[i]["dial"] = dial_layer(A[i])
    cases0 = {i: case_layer(A[i], canon) for i in parts}
    ext = case_ext(cases0)
    for i in parts:
        L[i]["case"] = case_layer(A[i], canon, ext)
        L[i]["strap"] = strap_layer(A[i], canon, deep, ext)
    if mode in ("export", "all"):
        os.makedirs(WEB, exist_ok=True)
        for i in CASE_IDS: L[i]["case"].save(os.path.join(WEB, f"case-dt-{i}.webp"), "WEBP", quality=Q, method=6)
        for i in DIAL_IDS: L[i]["dial"].save(os.path.join(WEB, f"dial-dt-{i}.webp"), "WEBP", quality=Q, method=6)
        for i in STRAP_IDS: L[i]["strap"].save(os.path.join(WEB, f"strap-dt-{i}.webp"), "WEBP", quality=Q, method=6)
        shadow.save(os.path.join(WEB, "shadowdial.webp"), "WEBP", quality=Q, method=6)
    if mode in ("sheets", "all"):
        sheets(L, shadow)
    print("ok")


def sheets(L, shadow):
    tiles = []
    for c, d, s, name in MIXES:
        im = stack([L[s]["strap"], L[d]["dial"], shadow, L[c]["case"]]).convert("RGB")
        tiles.append(im.crop((0, 250, 1000, 1750)).resize((400, 600), Image.LANCZOS))
    sh = Image.new("RGB", (400 * 4, 600 * 2), "white")
    for k, t in enumerate(tiles):
        sh.paste(t, ((k % 4) * 400, (k // 4) * 600))
    sh.save(os.path.join(OUT, "mezclas.jpg"), quality=90)
    cells = []
    for i in CASE_IDS: cells.append(("case dt-" + i, stack([L[i]["case"]])))
    for i in DIAL_IDS: cells.append(("dial dt-" + i, stack([L[i]["dial"], shadow])))
    for i in STRAP_IDS: cells.append(("strap dt-" + i, stack([L[i]["strap"]])))
    cols = 8
    rows = (len(cells) + cols - 1) // cols
    cw, ch = 250, 420
    sh = Image.new("RGB", (cw * cols, ch * rows), "white")
    dr = ImageDraw.Draw(sh)
    for k, (name, im) in enumerate(cells):
        t = im.convert("RGB").crop((0, 250, 1000, 1750)).resize((cw - 6, int((cw - 6) * 1.5)), Image.LANCZOS)
        x, y = (k % cols) * cw, (k // cols) * ch
        sh.paste(t, (x + 3, y + 20))
        dr.text((x + 6, y + 4), name, fill=(200, 0, 0))
    sh.save(os.path.join(OUT, "catalogo.jpg"), quality=90)


if __name__ == "__main__":
    sys.exit(main())
