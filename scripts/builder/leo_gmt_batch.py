#!/usr/bin/env python3
"""Batch GMT splitter with colour-agnostic bezel detection and a realism pass.

usage: leo_gmt_batch.py ORIGINALES_DIR PARTES_DIR [--raw-out DIR] [--skip imagen-12.jpg]

Per photo imagen-NN.jpg -> PARTES_DIR/gmt-NN/{bracelet,case,dial,bezel,stack}.png on a
1000x2000 RGBA canvas, dial centre (500,1000), bezel outer diameter 40 mm, 1000 px = 48 mm.
Stack order: bracelet -> case -> shadow-bezel -> dial -> shadow-dial -> bezel.
Also writes PARTES_DIR/shadow-bezel.png and shadow-dial.png and detection.json.
--raw-out writes the same layers WITHOUT the realism pass (for before/after comparison).
Needs numpy, opencv-python-headless.
"""
import os, sys, glob, json, argparse, re
import numpy as np, cv2

W, H, CX, CY = 1000, 2000, 500, 1000
MM = 1000 / 48
BEZEL_MM = 40
OVERLAP = 3
# ratios measured on imagen-02 (detected insert outer edge -> bezel outer incl. teeth / dial radius)
K_ROUT = 333.5 / 316.8   # imagen-02: detected insert-edge radius 316.8 -> bezel outer 333.5
K_RIN = 253.0 / 316.8    # -> dial radius 253
ROUT_C = BEZEL_MM * MM / 2          # canvas bezel outer radius (px)
RIN_C = ROUT_C * 253.0 / 333.5      # canvas dial radius (px)
LAYERS = ["bracelet", "case", "dial", "bezel"]


def fit_circle(P):
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    s = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    return s[0], s[1], np.sqrt(s[2] + s[0] ** 2 + s[1] ** 2)


def lug_rows(sil):
    widths = sil.sum(1)
    nz = np.nonzero(widths > 0)[0]
    bw = float(np.median(widths[nz[0] + 5: nz[0] + 65]))
    wide = np.nonzero(widths > bw * 1.25)[0]
    return int(wide.min()), int(wide.max()), bw


def detect(im, span):
    """Hough circle gives the centre (any colour; its radius may lock on the dial edge instead
    of the bezel). Radius prior = lug span (bezel_outer ~ 0.89 * half span), then refine on the
    bright-going-out edge of the insert and fit a circle with outlier rejection."""
    h, w = im.shape[:2]; m = min(h, w)
    g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (0, 0), 2)
    c = None
    for p2 in (40, 30, 22):
        c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, 1, m, param1=100, param2=p2,
                             minRadius=int(m * .15), maxRadius=int(m * .5))
        if c is not None: break
    if c is None: raise RuntimeError("no circle")
    cx, cy, _ = map(float, c[0][0])
    r0 = 0.89 * span / 2 / K_ROUT
    gf = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (0, 0), 1.2).astype(np.float32)
    rad = np.arange(0.92 * r0, 1.08 * r0, 0.5)
    for _ in range(3):
        angs = np.radians(np.arange(0, 360, 1.0))
        angs = angs[np.abs(((np.degrees(angs) + 180) % 360) - 180) > 35]  # skip crown side
        X = cx + np.outer(np.cos(angs), rad); Y = cy + np.outer(np.sin(angs), rad)
        prof = cv2.remap(gf, X.astype(np.float32), Y.astype(np.float32), cv2.INTER_LINEAR)
        d = np.gradient(cv2.GaussianBlur(prof, (0, 0), 1.0), axis=1)
        k = d.argmax(1)
        P = np.c_[cx + np.cos(angs) * rad[k], cy + np.sin(angs) * rad[k]]
        keep = np.ones(len(P), bool)
        for _ in range(4):
            fx, fy, fr = fit_circle(P[keep])
            res = np.abs(np.hypot(P[:, 0] - fx, P[:, 1] - fy) - fr)
            keep = res < max(3.0, 2 * np.median(res[keep]))
        cx, cy, r0 = fx, fy, fr
        rad = np.arange(0.96 * r0, 1.04 * r0, 0.25)
    return cx, cy, r0, float(keep.mean())


# manual bottom cut (source px): imagen-06 has a soft ground shadow under the bracelet end
CUT_BOTTOM = {"imagen-06.jpg": 846}


def silhouette(im, cut_bottom=None):
    # background per row from the left/right edge columns (top/bottom edges hold the bracelet)
    side = np.concatenate([im[:, :8], im[:, -8:]], 1).astype(np.float32)
    bg = cv2.GaussianBlur(np.median(side, 1)[:, None, :], (0, 0), 5)[:, 0]
    dist = np.abs(im.astype(np.float32) - bg[:, None, :]).max(2)
    cand = (dist <= 12).astype(np.uint8)
    n, lab = cv2.connectedComponents(cand, connectivity=4)
    border = (set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])) - {0}
    fg = (~np.isin(lab, list(border))).astype(np.uint8)
    m = finish_mask(fg)
    # soft ground shadows under a bracelet that ends inside the frame: cut rows beyond the
    # last row that still has a strong (non-shadow) bracelet span
    strict = (dist > 110).astype(np.uint8) * (m > 0)
    strict = cv2.morphologyEx(strict, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnt = strict.sum(1); rows = np.nonzero(cnt > 0.3 * np.median(cnt[cnt > 0]))[0]
    h = m.shape[0]
    if rows.max() < h - 3 and m[rows.max() + 3:].any(): m[rows.max() + 2:] = 0
    if rows.min() > 3 and m[:rows.min() - 2].any(): m[:rows.min() - 2] = 0
    if cut_bottom: m[cut_bottom:] = 0
    return m


def silhouette_gold(im):
    """Rose-gold on grey gradient background with a transparent stand: segment by chroma."""
    f = im.astype(int)
    fg = ((f[..., 2] - f[..., 0]) > 28).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return finish_mask(fg)


def finish_mask(fg):
    n, lab = cv2.connectedComponents(1 - fg, connectivity=4)
    bl = (set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])) - {0}
    fg = (~np.isin(lab, list(bl))).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg, connectivity=4)
    if n > 2:
        fg = (lab == 1 + st[1:, cv2.CC_STAT_AREA].argmax()).astype(np.uint8)
    # near-white bracelet links can match the white background: on bracelet rows (span about
    # the bracelet width) fill everything between the outer edges of the row
    cols = np.arange(fg.shape[1])
    anyr = fg.any(1)
    lo = np.where(anyr, np.where(fg > 0, cols, 10 ** 6).min(1), 0)
    hi = np.where(anyr, np.where(fg > 0, cols, -1).max(1), 0)
    span = np.where(anyr, hi - lo + 1, 0)
    nz = np.nonzero(anyr)[0]
    bw = np.percentile(span[nz[0] + 5: nz[0] + 65], 85)
    for y in nz:
        if span[y] <= bw * 1.1:
            fg[y, lo[y]:hi[y] + 1] = 1
    return fg.astype(np.float32)


def feather(m, s=0.8):
    return np.clip(cv2.GaussianBlur(m, (0, 0), s), 0, 1)


def steel_sample(im, sil, cx, cy, rout):
    """per-channel median of neutral, mid-bright metal pixels outside the bezel."""
    h, w = im.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    out = (np.hypot(xx - cx, yy - cy) > rout * 1.08) & (sil > 0.5)
    f = im.astype(np.float32)
    mx, mn = f.max(2), f.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    ok = out & (sat < 0.10) & (mx > 110) & (mx < 235)
    return (np.median(f[ok], 0), int(ok.sum()), int(out.sum())) if ok.sum() > 0.03 * out.sum() and ok.sum() > 2000 else (None, int(ok.sum()), int(out.sum()))


def unsharp(img, amount, sigma=1.2):
    b = cv2.GaussianBlur(img, (0, 0), sigma)
    return np.clip(img + amount * (img - b), 0, 255)


FADE = 140  # px of soft vertical fade at the free end of every bracelet


def warp_layers(imc, sil, cx, cy, rout, rin, sharpen_amt, ends=None):
    h, w = imc.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.hypot(xx - cx, yy - cy)
    yt, yb, bw = lug_rows(sil)
    # bracelet width between the lugs, measured on the bracelet right next to the lug tips
    def band(row):
        xs = np.nonzero(sil[row] > 0.5)[0]
        return xs.min(), xs.max()
    tl, tr = band(max(yt - 4, 0)); bl, br = band(min(yb + 4, sil.shape[0] - 1))
    top = yy < cy
    band_wide = np.where(top, (xx >= tl - OVERLAP) & (xx <= tr + OVERLAP), (xx >= bl - OVERLAP) & (xx <= br + OVERLAP))
    band_hole = np.where(top, (xx >= tl + 2) & (xx <= tr - 2), (xx >= bl + 2) & (xx <= br - 2))
    # bracelet = everything beyond the lug tips PLUS the end link sitting between the lugs
    # (it runs under the case by OVERLAP px; the case layer is cut out there)
    tb = (((yy < yt + OVERLAP) | (yy > yb - OVERLAP) | band_wide) & (rr > rout - OVERLAP)).astype(np.float32)
    cr = ((yy >= yt) & (yy <= yb) & ~band_hole).astype(np.float32)
    A = {"bracelet": feather(sil * tb, .7) * sil,
         "case": feather(sil * cr * (1 - (rr < rout - OVERLAP)), .7) * sil,
         "bezel": feather(((rr <= rout) & (rr >= rin)).astype(np.float32), .8),
         "dial": feather((rr <= rin + OVERLAP).astype(np.float32), .8)}
    s = ROUT_C / rout
    M = np.float32([[s, 0, CX - s * cx], [0, s, CY - s * cy]])
    col = cv2.warpAffine(imc, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    if sharpen_amt > 0: col = unsharp(col.astype(np.float32), sharpen_amt)
    col = np.clip(col, 0, 255).astype(np.uint8)
    L = {}
    for k in LAYERS:
        al = cv2.warpAffine(A[k], M, (W, H), flags=cv2.INTER_LINEAR)
        L[k] = np.dstack([col, (np.clip(al, 0, 1) * 255).round().astype(np.uint8)])
    if ends is not None:  # common free ends of all bracelets (canvas rows) with soft fade
        ramp = np.ones(H, np.float32); ys = np.arange(H, dtype=np.float32)
        ramp *= np.clip((ys - ends[0]) / FADE, 0, 1) * np.clip((ends[1] - ys) / FADE, 0, 1)
        a = L["bracelet"][..., 3].astype(np.float32) * ramp[:, None]
        L["bracelet"][..., 3] = a.round().astype(np.uint8)
    return L, s, (yt, yb, bw)


def over(layers):
    pc = np.zeros((H, W, 3), np.float32); pa = np.zeros((H, W), np.float32)
    for L in layers:
        L = L.astype(np.float32); al = L[..., 3:] / 255
        pc = L[..., :3] * al + pc * (1 - al); pa = al[..., 0] + pa * (1 - al[..., 0])
    return np.dstack([pc / np.maximum(pa, 1e-6)[..., None], pa * 255]).clip(0, 255).astype(np.uint8)


def deglare_dial(dial):
    """The crystal edge of each dial reflects the colour of ITS OWN bezel (red/blue/green/purple
    tint at the rehaut). Remove only that chroma in the outer rim band (luminance, detail and the
    grey glass glare are kept; nothing is painted in)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot(xx - CX, yy - CY) / RIN_C
    w = np.clip((r - 0.93) / 0.05, 0, 1) * 0.9
    c = dial[..., :3].astype(np.float32)
    g = (c * np.float32([0.114, 0.587, 0.299])).sum(2, keepdims=True)  # BGR luma
    out = dial.copy()
    out[..., :3] = np.clip(g + (1 - w[..., None]) * (c - g), 0, 255).astype(np.uint8)
    return out


def make_shadows():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # contact shadow of the bezel on the case: light from above -> slightly lower
    r = np.hypot(xx - CX, yy - (CY + 4))
    a = 0.55 * np.exp(-np.clip(r - ROUT_C, 0, None) / 7.0) * (r >= ROUT_C - 6)
    a = np.where(r >= ROUT_C - 6, a, 0)
    sb = np.dstack([np.zeros((H, W, 3), np.float32), a * 255]).astype(np.uint8)
    # inner shadow on dial edge (under the bezel's inner chamfer)
    r = np.hypot(xx - CX, yy - CY)
    a = 0.5 * np.exp(-np.clip(RIN_C - r, 0, None) / 12.0) * (r <= RIN_C + 3)
    sd = np.dstack([np.zeros((H, W, 3), np.float32), a * 255]).astype(np.uint8)
    return sb, sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--raw-out"); ap.add_argument("--skip", nargs="*", default=["imagen-12.jpg"])
    ap.add_argument("--ref", default="imagen-02.jpg")
    a = ap.parse_args()
    files = [f for f in sorted(glob.glob(os.path.join(a.src, "imagen-*.jpg"))) if os.path.basename(f) not in a.skip]
    data = {}
    for f in files:
        im = cv2.imread(f); name = os.path.basename(f)
        gold = name in ("imagen-05.jpg",)
        sil = silhouette_gold(im) if gold else silhouette(im, CUT_BOTTOM.get(name))
        yt, yb, _ = lug_rows(sil)
        cx, cy, re_, inl = detect(im, yb - yt)
        rout, rin = re_ * K_ROUT, re_ * K_RIN
        st, nk, no = steel_sample(im, sil, cx, cy, rout)
        data[name] = dict(im=im, cx=cx, cy=cy, re=re_, inl=inl, sil=sil, rout=rout, rin=rin, steel=st, nk=nk, no=no)
    target = data[a.ref]["steel"]
    report = {}
    # pass 1: free ends of every bracelet -> common ends = the shortest bracelet at each side
    tops, bots = [], []
    for f in files:
        d = data[os.path.basename(f)]
        Lx, _, _ = warp_layers(d["im"].astype(np.float32), d["sil"], d["cx"], d["cy"], d["rout"], d["rin"], 0)
        ys = np.nonzero((Lx["bracelet"][..., 3] > 8).any(1))[0]
        tops.append(ys.min()); bots.append(ys.max())
    ends = (max(tops), min(bots))
    print("common bracelet ends (canvas rows):", ends, "tops", tops, "bots", bots)
    for f in files:
        name = os.path.basename(f); d = data[name]
        pid = "gmt-" + re.search(r"(\d+)", name).group(1)
        s = ROUT_C / d["rout"]
        if d["steel"] is not None:
            gain = np.clip(target / d["steel"], 0.8, 1.25)
        else:
            gain = np.ones(3); 
        imc = np.clip(d["im"].astype(np.float32) * gain, 0, 255)
        amt = 0.3 + 0.5 * max(0.0, (s - 1.3) / 0.6)
        amt_raw = 0
        Lc, s, lug = warp_layers(imc, d["sil"], d["cx"], d["cy"], d["rout"], d["rin"], amt, ends)
        Lc["dial"] = deglare_dial(Lc["dial"])
        od = os.path.join(a.out, pid); os.makedirs(od, exist_ok=True)
        for k in LAYERS: cv2.imwrite(os.path.join(od, k + ".png"), Lc[k])
        cv2.imwrite(os.path.join(od, "stack.png"), over([Lc[k] for k in LAYERS]))
        if a.raw_out:
            Lr, _, _ = warp_layers(d["im"].astype(np.float32), d["sil"], d["cx"], d["cy"], d["rout"], d["rin"], 0, ends)
            od = os.path.join(a.raw_out, pid); os.makedirs(od, exist_ok=True)
            for k in LAYERS: cv2.imwrite(os.path.join(od, k + ".png"), Lr[k])
        report[pid] = dict(source=name, center=[round(d["cx"], 1), round(d["cy"], 1)], insert_edge_r=round(d["re"], 1),
                           bezel_outer_r=round(d["rout"], 1), dial_r=round(d["rin"], 1), fit_inlier=round(d["inl"], 2),
                           scale=round(s, 3), upscaled=bool(s > 1.35), steel_px=d["nk"],
                           wb_gain=[round(float(x), 3) for x in gain[::-1]], steel_matched=d["steel"] is not None,
                           sharpen=round(amt, 2), bracelet_ends=list(map(int, ends)), lug_rows=[lug[0], lug[1]], bracelet_w=round(float(lug[2])))
        print(pid, json.dumps(report[pid]))
    sb, sd = make_shadows()
    cv2.imwrite(os.path.join(a.out, "shadow-bezel.png"), sb)
    cv2.imwrite(os.path.join(a.out, "shadow-dial.png"), sd)
    json.dump(report, open(os.path.join(a.out, "detection.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
