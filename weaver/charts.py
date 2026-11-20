"""SZL estate card-weaver: SVG chart primitives (stdlib only).

Palette: KANCHAY v1.1.1 + logo palette (space navy, coral, silver linework).
Every chart is deterministic: same data in, same bytes out (hash-receiptable).
"""
import html
import math

INK = "#030F29"
CORAL = "#DF735F"
SILVER_HI = "#E9EEF6"
SILVER_MID = "#9AA7BD"
SILVER_LO = "#5C6B86"
GRID = "#9AA7BD"
YAWAR = "#c0392b"
YUYAY = "#168f89"
HATUN = "#cda64a"
PAPER = "#ffffff"
SERIES = [CORAL, YUYAY, HATUN, SILVER_LO, YAWAR]
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def _esc(s):
    return html.escape(str(s), quote=True)


def _txt(x, y, s, size=11, fill=SILVER_LO, anchor="start", weight=400):
    return ('<text x="%s" y="%s" font-family="%s" font-size="%s" fill="%s" '
            'text-anchor="%s" font-weight="%s">%s</text>' %
            (round(x, 1), round(y, 1), FONT, size, fill, anchor, weight, _esc(s)))


def _num(v):
    try:
        if v is None:
            return "-"
        f = float(v)
        if f == int(f) and abs(f) < 1e6:
            return "{:,}".format(int(f))
        return ("%.4f" % f).rstrip("0").rstrip(".")
    except Exception:
        return str(v)


def _empty(w, h, title):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">' % (w, h, w, h)]
    if title:
        out.append(_txt(10, 18, title, 13, INK, "start", 600))
    out.append(_txt(w / 2, h / 2, "no admissible data - UNKNOWN", 11, SILVER_MID, "middle"))
    out.append("</svg>")
    return "".join(out)


def line_chart(series, width=720, height=280, x_labels=None, y_fmt=None,
               title=None, legend=None, fill_area=False):
    """series: list of dicts {name, points:[(x,y), ...]} on a shared numeric x scale."""
    w, h = width, height
    ml, mr, mt, mb = 58, 16, 30, 34
    pts_all = [p for s_ in series for p in s_.get("points", [])]
    if not pts_all:
        return _empty(w, h, title)
    xs = [p[0] for p in pts_all]
    ys = [p[1] for p in pts_all]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if ymax == ymin:
        ymax = ymin + 1.0
    def X(x): return ml + (x - xmin) / ((xmax - xmin) or 1.0) * (w - ml - mr)
    def Y(y): return mt + (1 - (y - ymin) / (ymax - ymin)) * (h - mt - mb)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">' % (w, h, w, h)]
    if title:
        parts.append(_txt(ml, 16, title, 13, INK, "start", 600))
    for i in range(5):
        yv = ymin + (ymax - ymin) * i / 4.0
        yy = Y(yv)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1" stroke-opacity="0.45" stroke-dasharray="2 3"/>' % (ml, yy, w - mr, yy, GRID))
        parts.append(_txt(ml - 6, yy + 3.5, (y_fmt or _num)(yv), 10, SILVER_LO, "end"))
    for i, s_ in enumerate(series):
        col = SERIES[i % len(SERIES)]
        pts = s_["points"]
        if fill_area:
            base = Y(ymin)
            parts.append('<polygon points="%s %.1f,%.1f %.1f,%.1f %.1f" fill="%s" fill-opacity="0.08"/>' %
                         (" ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in pts),
                          X(pts[-1][0]), base, X(pts[0][0]), base, col))
        parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round"/>' %
                     (" ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in pts), col))
        parts.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (X(pts[0][0]), Y(pts[0][1]), col))
        parts.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (X(pts[-1][0]), Y(pts[-1][1]), col))
    if legend:
        lx = ml
        for i, name in enumerate(legend):
            col = SERIES[i % len(SERIES)]
            parts.append('<rect x="%.1f" y="%.1f" width="10" height="10" rx="2" fill="%s"/>' % (lx, h - 12, col))
            parts.append(_txt(lx + 14, h - 3.5, name, 10, SILVER_LO))
            lx += 30 + 7.0 * len(str(name))
    if x_labels:
        for xv, lab in x_labels:
            parts.append(_txt(X(xv), h - mb + 14, lab, 10, SILVER_LO, "middle"))
    parts.append("</svg>")
    return "".join(parts)


def donut(parts_, size=170, hole=0.62, title=None, legend=True):
    """parts_: [(label, value, color?)]"""
    w = size + (250 if legend else 0)
    h = max(size, 26 + 22 * len(parts_))
    total = sum(v for _, v, *_ in parts_) or 1
    cx, cy, r = size / 2, h / 2, min(size, h) / 2 - 8
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">' % (w, h, w, h)]
    if title:
        out.append(_txt(10, 16, title, 13, INK, "start", 600))
        cy = cy + 8
    a0 = -90.0
    inner = r * hole
    for i, item in enumerate(parts_):
        label, value = item[0], item[1]
        col = item[2] if len(item) > 2 and item[2] else SERIES[i % len(SERIES)]
        frac = max(value / total, 0.0)
        if frac <= 0:
            continue
        a1 = a0 + frac * 360.0
        large = 1 if (a1 - a0) > 180 else 0
        x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
        x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
        xi0, yi0 = cx + inner * math.cos(math.radians(a0)), cy + inner * math.sin(math.radians(a0))
        xi1, yi1 = cx + inner * math.cos(math.radians(a1)), cy + inner * math.sin(math.radians(a1))
        out.append('<path d="M %.2f %.2f A %.2f %.2f 0 %d 1 %.2f %.2f L %.2f %.2f A %.2f %.2f 0 %d 0 %.2f %.2f Z" fill="%s" stroke="%s" stroke-width="2"/>' %
                   (x0, y0, r, r, large, x1, y1, xi1, yi1, inner, inner, 0, xi0, yi0, col, PAPER))
        a0 = a1
    out.append(_txt(cx, cy + 5, _num(total), 20, INK, "middle", 700))
    if legend:
        for i, item in enumerate(parts_):
            col = item[2] if len(item) > 2 and item[2] else SERIES[i % len(SERIES)]
            ly = 26 + i * 22
            out.append('<rect x="%d" y="%d" width="11" height="11" rx="2" fill="%s"/>' % (size + 12, ly - 11, col))
            out.append(_txt(size + 30, ly, "%s: %s" % (item[0], _num(item[1])), 11, SILVER_LO))
    out.append("</svg>")
    return "".join(out)


def hbar(items, width=720, row_h=30, title=None):
    """items: [(label, value, color?)] top-down horizontal bars."""
    h = 28 + row_h * len(items) + 8
    lab_w = 210
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">' % (width, h, width, h)]
    if title:
        out.append(_txt(12, 18, title, 13, INK, "start", 600))
    vmax = max((v for _, v, *_ in items), default=1) or 1
    for i, item in enumerate(items):
        label, value = item[0], item[1]
        col = item[2] if len(item) > 2 and item[2] else SERIES[i % len(SERIES)]
        y = 30 + i * row_h
        bw = (value / vmax) * (width - lab_w - 110)
        out.append(_txt(8, y + row_h / 2 + 4, label, 11.5, INK, "start", 500))
        out.append('<rect x="%d" y="%d" width="%d" height="%.0f" rx="4" fill="%s" fill-opacity="0.88"/>' % (lab_w, y + 6, max(bw, 2), row_h - 14, col))
        out.append(_txt(lab_w + max(bw, 2) + 8, y + row_h / 2 + 4, _num(value), 10.5, SILVER_LO))
    out.append("</svg>")
    return "".join(out)


def sparkline(points, width=160, height=36, color=CORAL):
    if not points:
        return ''
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if ymax == ymin:
        ymax = ymin + 1
    def X(x): return 2 + (x - xmin) / ((xmax - xmin) or 1) * (width - 4)
    def Y(y): return 3 + (1 - (y - ymin) / (ymax - ymin)) * (height - 6)
    poly = " ".join("%.1f,%.1f" % (X(p[0]), Y(p[1])) for p in points)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">'
            '<polyline points="%s" fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round"/></svg>'
            % (width, height, width, height, poly, color))
