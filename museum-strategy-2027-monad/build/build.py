# Rebuilds "Тошкент политехника музейи — стратегия 2027" in the Monad visual system.
# All slide text is read verbatim from the source deck; speaker notes are copied as XML.
import copy, sys, os
from lib import *
from lib import _style_run

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'src', 'src.pptx')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'out', 'deck.pptx')
A = lambda f: os.path.join(HERE, 'assets', f)

src = Presentation(SRC)
def T(s, j):
    return src.slides[s - 1].shapes[j].text_frame.text
def TB(s, j):
    return [[c.text for c in r.cells] for r in src.slides[s - 1].shapes[j].table.rows]
def sentence(t, strip_prefix=False):
    if strip_prefix and '. ' in t:
        t = t.split('. ', 1)[1]
    s = t.lower()
    i = next(k for k, ch in enumerate(s) if ch.isalnum())
    if s[i].isalpha():
        s = s[:i] + s[i].upper() + s[i + 1:]
    return s.replace('“ўзавтосаноат”', '“Ўзавтосаноат”').replace('тошкент', 'Тошкент')

prs = Presentation()
prs.slide_width, prs.slide_height = E(W), E(H)
BLANK = prs.slide_layouts[6]
TOTAL = 20
SLIDES = []          # (slide, source index for notes)

def new_slide(src_idx, dark=False):
    sl = prs.slides.add_slide(BLANK)
    background(sl, INK if dark else PARCH)
    SLIDES.append((sl, src_idx))
    return sl

def header(sl, section, title, dark=False):
    fg = PARCH if dark else INK
    pill(sl, M, PILL_Y, section, size=10, color=fg, border=ASH, name='Section')
    if nlines(title, 'head', TITLE_SIZE, CW) > 1:
        warn(f'title wraps: {title}')
    tbox(sl, M, TITLE_Y, CW, 0.62, [title], size=TITLE_SIZE, kind='head', color=fg,
         lead=TITLE_LEAD, name='Title')

def footer(sl, n, source=None, dark=False):
    c = ASH if dark else SMOKE
    tbox(sl, W - M - 1.1, FB - 0.2, 1.1, 0.2, [f'{n:02d} / {TOTAL:02d}'], size=10, color=c,
         align='r', anchor='b', name='Slide number')
    if not source:
        return FB
    h = text_h(source, 'body', 9, FN_W)
    tbox(sl, M, FB - h, FN_W, h, source, size=9, color=c, anchor='b', name='Source')
    return FB - h

def cb_of(top):
    return top - GAP

def check_bottom(n, y, cb):
    if y > cb + 0.01:
        warn(f'slide {n}: content bottom {y:.2f} > {cb:.2f}')

def logo_card(sl, x, y):
    w, h = 2.9, 1.24
    rect(sl, x, y, w, h, fill=PARCH, radius=0.4, name='Logo card')
    lw = 2.5; lh = lw * 1011 / 2400
    picture(sl, A('logo.png'), x + (w - lw) / 2, y + (h - lh) / 2, lw, lh,
            descr='Тошкент политехника музейи логотипи', name='Logo')

# =================================================================== 1 · title (dark)
def s1():
    sl = new_slide(1, dark=True)
    picture(sl, A('blob-title.png'), 0, 0, W, H, descr='', decorative=True, name='Gradient')
    logo_card(sl, M, M)
    pw, ph = 4.4, 5.75
    px = W - M - pw
    picture(sl, A('main-hall.jpg'), px, M, pw, ph, radius=0.3,
            descr='Музейнинг бош зали, 1-қават: ретро-автомобиллар', name='Photo main hall', focus=(0.6, 0.5))
    cap = T(1, 7)
    ch = text_h(cap, 'body', 10, pw)
    tbox(sl, px, FB - ch, pw, ch, cap, size=10, color=ASH, anchor='b', name='Photo caption')
    title = sentence(T(1, 2))
    tw_ = px - GAP_L - M
    size = next(s for s in (60, 56, 54, 52, 48) if nlines(title, 'head', s, tw_) <= 4)
    th = text_h(title, 'head', size, tw_)
    ty = 2.25
    tbox(sl, M, ty, tw_, th, [title], size=size, kind='head', color=PARCH, name='Title')
    tbox(sl, M, ty + th + 0.3, tw_, 0.3, T(1, 3), size=16, color=ASH, name='Subtitle')
    x = M
    for j in (4, 5):
        x += pill(sl, x, FB - 0.34, T(1, j), size=11, color=PARCH, border=ASH, h=0.34) + 0.2

# =================================================================== 2 · summary
def s2():
    n = 2
    sl = new_slide(2)
    header(sl, '01 · Асосий мазмун', sentence(T(2, 1)))
    cb = cb_of(footer(sl, n, T(2, 2)))
    colw, mx = 3.35, M
    cols = (mx, mx + colw + GAP)
    hdr = [[('2026 ЙИЛ', {}), (' · АМАЛДА ВА КУТИЛИШ', {'color': SMOKE})],
           [('2027 ЙИЛ ЯКУНИ', {}), (' · РЕЖА', {'color': SMOKE})]]
    for c, h_ in zip(cols, hdr):
        tbox(sl, c, CT, colw, 0.2, [h_], size=10, check=False)
    y = CT + 0.34
    mw = 2 * colw + GAP
    line(sl, mx, y, mx + mw, y)
    cells = [
        [('ТАШРИФЧИЛАР, КИШИ', T(2, 13), T(2, 14), INK), ('ТАШРИФЧИЛАР, КИШИ', T(2, 25), T(2, 26), BLUE)],
        [('МУЗЕЙ ТУШУМИ, МЛН СЎМ', T(2, 17).replace(' млн сўм', ''), T(2, 18), INK),
         ('МУЗЕЙ ТУШУМИ, МЛН СЎМ', T(2, 29).replace(' млн сўм', ''), T(2, 30), INK)],
        [(T(2, 20).upper(), T(2, 21), T(2, 22), INK), (T(2, 32).upper(), T(2, 33), T(2, 34), INK)],
    ]
    NS, NL = 32, 0.47
    for row in cells:
        hs = []
        for (lab, num, cap, col) in row:
            nw = tw(num, 'head', NS) + 0.05
            capw = colw - nw - 0.2
            hs.append(max(NL, text_h(cap, 'body', 12, capw)))
        rh = 0.16 + 0.2 + 0.1 + max(hs) + 0.16
        for c, (lab, num, cap, col) in zip(cols, row):
            nw = tw(num, 'head', NS) + 0.05
            tbox(sl, c, y + 0.16, colw, 0.2, lab, size=10, color=GRAPH)
            tbox(sl, c, y + 0.46, nw, NL, [num], size=NS, kind='head', color=col, lead=34)
            capw = colw - nw - 0.2
            tbox(sl, c + nw + 0.2, y + 0.5, capw, max(hs), cap, size=12, color=GRAPH)
        y += rh
        line(sl, mx, y, mx + mw, y)
    check_bottom(n, y, cb)
    # decisions card
    cx = mx + mw + GAP_L
    cw = W - M - cx
    rect(sl, cx, CT, cw, cb - CT, fill=PERI, radius=0.4, name='Decisions card')
    ix, iw, yy = cx + 0.3, cw - 0.6, CT + 0.28
    tbox(sl, ix, yy, iw, 0.2, [[('ҚАРОРЛАР', {}), (' · ' + T(2, 8).split('\n')[1].upper(), {'color': GRAPH})]],
         size=10, check=False)
    yy += 0.4
    items = T(2, 36)
    ih = text_h(items, 'body', 14, iw, after=2)
    tbox(sl, ix, yy, iw, ih, items, size=14, after=2, name='Decisions')
    yy += ih + 0.17
    line(sl, ix, yy, ix + iw, yy)
    yy += 0.17
    tag = T(2, 38).upper()
    pill(sl, W - M - tw(tag, 'body', 10) - 0.32, PILL_Y, tag, size=10, fill=None, border=ASH, name='Tag')
    t39 = T(2, 39)
    h39 = text_h(t39, 'body', 14, iw)
    tbox(sl, ix, yy, iw, h39, t39, size=14)
    check_bottom(n, yy + h39 + 0.28, cb)

# =================================================================== 3 · rent-dependent
def s3():
    n = 3
    sl = new_slide(3)
    header(sl, '02 · Ҳозирги ҳолат', sentence(T(3, 1)))
    cb = cb_of(footer(sl, n, T(3, 2)))
    k = 5
    cw = (CW - (k - 1) * GAP) / k
    stats = [(4, 5, 6), (8, 9, 10), (12, 13, 14), (16, 17, 18), (20, 21, 22)]
    capmax = max(text_h(T(3, c), 'body', 12, cw) for _, _, c in stats)
    for i, (l, v, c) in enumerate(stats):
        x = M + i * (cw + GAP)
        tbox(sl, x, CT, cw, 0.2, T(3, l).upper(), size=10, color=GRAPH)
        val = T(3, v)
        if tw(val, 'head', 42) > cw:
            warn(f's3 number too wide {val}')
        tbox(sl, x, CT + 0.32, cw, 0.62, [val], size=42, kind='head',
             color=BLUE if v == 17 else INK, lead=44)
        tbox(sl, x, CT + 1.02, cw, capmax, T(3, c), size=12, color=GRAPH)
        if i:
            line(sl, x - GAP / 2, CT, x - GAP / 2, CT + 1.02 + capmax)
    y = CT + 1.02 + capmax + GAP_L
    # comparison card
    cw2 = 8.3
    ch = cb - y
    rect(sl, M, y, cw2, ch, fill=PERI, radius=0.4, name='Comparison card')
    ix = M + 0.35
    tbox(sl, ix, y + 0.3, cw2 - 0.7, 0.2, T(3, 24).upper(), size=10, color=GRAPH)
    colw = (cw2 - 0.7 - 0.7) / 2
    for i, (vj, cj) in enumerate(((25, 28), (26, 29))):
        x = ix + i * (colw + 0.7)
        num, unit = T(3, vj).split(' ', 1)[0], None
        v = T(3, vj)
        parts = v.rsplit(' млн', 1)
        tbox(sl, x, y + 0.65, colw, 0.6, [[(parts[0], {'kind': 'head', 'size': 36}),
                                            (' млн' + parts[1], {'size': 14, 'color': GRAPH})]],
             size=36, lead=40, check=False)
        hh = text_h(T(3, cj), 'body', 14, colw)
        tbox(sl, x, y + 1.32, colw, hh, T(3, cj), size=14)
        check_bottom(n, y + 1.32 + hh + 0.25, cb)
    tbox(sl, ix + colw, y + 0.65, 0.7, 0.6, ['≈'], size=36, kind='head', align='c', lead=40)
    qx = M + cw2 + GAP_L
    qw = W - M - qx
    q = T(3, 30)
    qh = text_h(q, 'head', 24, qw, lead=29)
    tbox(sl, qx, y + (ch - qh) / 2, qw, qh, [q], size=24, kind='head', lead=29, name='Key message')

# =================================================================== 4 · risks if nothing changes
def s4():
    n = 4
    sl = new_slide(4)
    header(sl, '02 · Ҳозирги ҳолат', sentence(T(4, 1)))
    cb = cb_of(footer(sl, n, T(4, 2)))
    rows = [(5, 6), (9, 10), (13, 14), (17, 18)]
    inset = 0.3
    nx = M + inset
    tx, tw_ = nx + 0.85, 3.2
    bx = tx + tw_ + GAP_L
    bw = W - M - inset - bx
    pad = 0.17
    hs = [max(text_h(T(4, a), 'head', 20, tw_, lead=24), text_h(T(4, b), 'body', 14, bw)) + 2 * pad
          for a, b in rows]
    spare = (cb - CT) - sum(hs)
    if spare < 0:
        warn(f'slide 4 rows over by {-spare:.2f}')
    hs = [h_ + max(0, spare) / len(hs) for h_ in hs]
    y = CT
    line(sl, M, y, W - M, y)
    for i, ((a, b), h_) in enumerate(zip(rows, hs)):
        last = i == len(rows) - 1
        top = y + (h_ - (max(text_h(T(4, a), 'head', 20, tw_, lead=24), text_h(T(4, b), 'body', 14, bw)))) / 2
        if last:
            rect(sl, M, y + 0.1, CW, h_ - 0.1, fill=PERI, radius=0.4, name='Highlighted risk')
            top += 0.05
        pill(sl, nx, top, f'{i + 1:02d}', size=10, h=0.3, w=0.56,
             fill=BLUE if last else None, border=None if last else ASH, color=PARCH if last else INK)
        tbox(sl, tx, top - 0.02, tw_, h_ - 2 * pad, [T(4, a)], size=20, kind='head', lead=24)
        tbox(sl, bx, top, bw, h_ - 2 * pad, T(4, b), size=14)
        y += h_
        if not last:
            line(sl, M, y, W - M, y)

# =================================================================== 5 · benefits
def s5():
    n = 5
    sl = new_slide(5)
    header(sl, '03 · 2027 йил режаси', sentence(T(5, 1)))
    cb = cb_of(footer(sl, n, T(5, 2)))
    k = 5
    cw = (CW - (k - 1) * GAP) / k
    items = [(4, 5), (7, 8), (10, 11), (13, 14), (16, 17)]
    th = max(text_h(T(5, a), 'head', 20, cw, lead=23) for a, _ in items)
    bh = max(text_h(T(5, b), 'body', 14, cw) for _, b in items)
    t = T(5, 19)
    lab, body = t.split(': ', 1)
    body = body[0].upper() + body[1:]
    iw = CW - 0.6 - 1.25
    hh = text_h(body, 'body', 14, iw)
    ch = hh + 0.44
    cy = cb - ch
    if CT + 0.45 + th + 0.12 + bh + GAP > cy:
        warn(f'slide 5 over by {CT + 0.45 + th + 0.12 + bh + GAP - cy:.2f}')
    for i, (a, b) in enumerate(items):
        x = M + i * (cw + GAP)
        last = i == k - 1
        pill(sl, x, CT, f'{i + 1:02d}', size=10, w=0.56, fill=BLUE if last else None,
             border=None if last else ASH, color=PARCH if last else INK)
        tbox(sl, x, CT + 0.45, cw, th, [T(5, a)], size=20, kind='head', lead=23)
        tbox(sl, x, CT + 0.45 + th + 0.12, cw, bh, T(5, b), size=14)
        if i:
            line(sl, x - GAP / 2, CT, x - GAP / 2, CT + 0.45 + th + 0.12 + bh)
    rect(sl, M, cy, CW, ch, fill=PERI, radius=0.4, name='Positioning card')
    pill(sl, M + 0.3, cy + 0.19, lab, size=10)
    tbox(sl, M + 0.3 + 1.25, cy + 0.22, iw, hh, body, size=14)

# =================================================================== 6 · quarters (dark)
def s6():
    n = 6
    sl = new_slide(6, dark=True)
    header(sl, '03 · 2027 йил режаси', sentence(T(6, 1)), dark=True)
    cb = cb_of(footer(sl, n, T(6, 2), dark=True))
    tbox(sl, M, CT, CW, 0.26, T(6, 3), size=14, color=ASH)
    k = 5
    cw = (CW - (k - 1) * GAP) / k
    cols = [(5, 8, 9, 10), (12, 15, 16, 17), (19, 22, 23, 24), (26, 29, 30, 31), (33, 35, 36, 37)]
    py = CT + 0.5
    rh = max(text_h(T(6, r), 'body', 14, cw) for _, r, _, _ in cols)
    for i, (p, r, l, v) in enumerate(cols):
        x = M + i * (cw + GAP)
        a, b = T(6, p).split('\n')
        pill(sl, x, py, f'{a} · {b}', size=10, color=PARCH, border=ASH, w=cw, h=0.32)
        if i:
            line(sl, x - GAP, py + 0.16, x, py + 0.16, color=ASH)
        tbox(sl, x, py + 0.5, cw, rh, T(6, r), size=14, color=PARCH)
        ly = py + 0.5 + rh + 0.22
        tbox(sl, x, ly, cw, 0.2, T(6, l).upper(), size=10, color=ASH)
        tbox(sl, x, ly + 0.26, cw, 0.56, [T(6, v)], size=38, kind='head', color=PARCH, lead=40)
    ctext = T(6, 39)
    cwid = 6.4
    ch = text_h(ctext, 'body', 14, cwid)
    yy = cb - ch
    check_bottom(n, ly + 0.26 + 0.56 + 0.15, yy)
    tbox(sl, W - M - cwid, yy, cwid, ch, ctext, size=14, color=PARCH, align='r', name='Control point')
    oval(sl, W - M - tw(ctext, 'body', 14) - 0.22, yy + 0.125, 0.16, BLUE, name='Control point marker')

# =================================================================== 7 · 13 exhibits timeline
def s7():
    n = 7
    sl = new_slide(7)
    header(sl, '03 · 2027 йил режаси', sentence(T(7, 1)))
    cb = cb_of(footer(sl, n, T(7, 2)))
    months = [T(7, j) for j in range(4, 33, 2)]
    mw = CW / len(months)
    X = lambda m: M + m * mw
    for i, mth in enumerate(months):
        tbox(sl, X(i), CT, mw, 0.2, mth.upper(), size=10, color=GRAPH if i >= 3 else SMOKE, align='c')
    line(sl, M, CT + 0.3, W - M, CT + 0.3)
    line(sl, X(3), CT - 0.05, X(3), CT + 0.3, color=ASH)
    my = CT + 0.4
    bars_y = my + 0.44
    bh, bg = 0.34, 0.08
    bottom = bars_y + 3 * bh + 2 * bg
    for m, lab in ((6, T(7, 34)), (8, T(7, 36)), (9, T(7, 38))):
        line(sl, X(m), my + 0.32, X(m), bottom, color=ASH, dash=True)
        pill(sl, X(m) - 0.27, my, lab, size=10, w=0.54, h=0.3)
    cx = X(12 + 14 / 31)
    line(sl, cx, my + 0.3, cx, bottom, color=ASH, dash=True)
    oval(sl, cx, my + 0.15, 0.16, BLUE, name='Control point marker')
    a, b = T(7, 46).split('\xa0— ')
    tbox(sl, cx + 0.15, my - 0.04, W - M - cx - 0.15, 0.4, [a + ' —', b.upper()], size=10, lead=12.5,
         check=False)
    bars = [(0, 9, T(7, 40), None, ASH), (2, 9, T(7, 42), PERI, None), (9, 15, T(7, 44), None, ASH)]
    for i, (m0, m1, lab, fill, border) in enumerate(bars):
        y = bars_y + i * (bh + bg)
        rect(sl, X(m0), y, X(m1) - X(m0), bh, fill=fill, line=border, radius=bh / 2)
        tbox(sl, X(m0) + 0.16, y, X(m1) - X(m0) - 0.3, bh, [lab], size=14, anchor='m')
    y = bottom + 0.42
    line(sl, M, y - 0.2, W - M, y - 0.2)
    k = 3
    cw = (CW - (k - 1) * GAP) / k
    lists = [(48, 50), (52, 54), (56, 58)]
    lh = max(text_h(T(7, b), 'body', 14, cw) for _, b in lists)
    check_bottom(n, y + 0.5 + lh, cb)
    for i, (a, b) in enumerate(lists):
        x = M + i * (cw + GAP)
        pill(sl, x, y, T(7, a), size=10, name=f'Wave {i + 1}')
        tbox(sl, x, y + 0.5, cw, lh, T(7, b), size=14)
        if i:
            line(sl, x - GAP / 2, y, x - GAP / 2, y + 0.5 + lh)

# =================================================================== 8 · revenue x2.3
def s8():
    n = 8
    sl = new_slide(8)
    picture(sl, A('blob-revenue.png'), 0, 0, W, H, descr='', decorative=True, name='Gradient')
    header(sl, '03 · 2027 йил режаси', sentence(T(8, 1)))
    cb = cb_of(footer(sl, n, T(8, 2)))
    t1 = TB(8, 13)
    lw = 3.6
    tbox(sl, M, CT + 0.1, lw, 0.2, 'МУЗЕЙ ТУШУМИ · 2027 / 2026', size=10, color=GRAPH)
    tbox(sl, M - 0.05, CT + 0.45, lw + 0.3, 1.9, ['×2,3'], size=130, kind='head', color=BLUE, lead=130,
         name='Key figure')
    tbox(sl, M, CT + 2.45, lw, 0.45, f'{t1[2][2]} → {t1[2][3]} МЛН СЎМ', size=11, color=GRAPH)
    rx = M + lw + GAP_L
    rw = W - M - rx
    colw = [2.55, 1.3, 1.3, 1.45, rw - 2.55 - 1.3 - 1.3 - 1.45]
    hdr = ['', T(8, 4), T(8, 6), T(8, 8), T(8, 12)]
    rows = [hdr] + t1
    rows = [[({'t': c, 'fill': PERI} if j == 3 else c) for j, c in enumerate(r)] for r in rows]
    aligns = ['l', 'r', 'r', 'r', 'r']
    th, _ = table(sl, rx, CT, colw, rows, size=14, aligns=aligns, name='Revenue table')
    y = CT + th + 0.4
    tbox(sl, rx, y, rw, 0.2, T(8, 14).upper(), size=10, color=GRAPH)
    t2 = TB(8, 15)
    qw = (rw - colw[0]) / 4
    th2, _ = table(sl, rx, y + 0.3, [colw[0]] + [qw] * 4, t2, size=14, aligns=['l', 'r', 'r', 'r', 'r'],
                   name='Quarterly plan')
    check_bottom(n, y + 0.3 + th2, cb)

# =================================================================== 9 · budget
def head_body(t):
    """'Тавсия: А. …' -> ('Тавсия: А', '…'); 'Гуруҳ … таъсир: …' -> ('Гуруҳ … таъсир', '…')"""
    a, b = t.split(': ', 1)
    if a.startswith('Тавсия'):
        x, rest = b.split('. ', 1)
        return f'{a}: {x}', rest
    return a, b[0].upper() + b[1:]

def s9():
    n = 9
    sl = new_slide(9)
    header(sl, '04 · Бюджет', sentence(T(9, 1)))
    cb = cb_of(footer(sl, n, T(9, 2)))
    lw = 7.3
    t = TB(9, 3)
    colw = [1.25, 1.35, 1.3, 2.0, lw - 1.25 - 1.35 - 1.3 - 2.0]
    rows = [r[:] for r in t]
    rows[-1] = [{'t': c, 'color': BLUE if j == 1 else INK} for j, c in enumerate(rows[-1])]
    th, _ = table(sl, M, CT, colw, rows, size=14, aligns=['l', 'r', 'r', 'r', 'r'], name='Budget table')
    # consolidated effect for the group (under the table)
    gh, gb = head_body(T(9, 8))
    y = CT + th + GAP
    tbox(sl, M, y, lw, 0.3, [gh], size=20, kind='head', lead=23)
    bh = text_h(gb, 'body', 14, lw)
    tbox(sl, M, y + 0.42, lw, bh, gb, size=14)
    check_bottom(n, y + 0.42 + bh, cb)
    # composition of the development budget (right)
    rx = M + lw + GAP_L
    rw = W - M - rx
    comp = T(9, 5)
    lab, rest = comp.replace('+\xa0', '+ ').split(': ', 1)
    expr, note = rest.split('\xa0млн\xa0сўм. ', 1)
    parts, total = expr.split(' = ')
    names = []
    for part in parts.split(' + '):
        nm, val = part.rsplit(' ', 1)
        names.append((nm.replace('\xa0', ' '), val))
    tbox(sl, rx, CT, rw, 0.2, (lab + ', млн сўм').upper(), size=10, color=GRAPH)
    rows = [[nm, v] for nm, v in names] + [['=', total]]
    rows = [['', '']] + rows
    th2, _ = table(sl, rx, CT + 0.28, [rw - 1.2, 1.2], rows[1:], hdr=0, size=14, aligns=['l', 'r'],
                   name='Budget composition', pady=0.015)
    y2 = CT + 0.28 + th2 + 0.12
    # recommendation card
    rh_, rb = head_body(T(9, 6))
    rb = rb.split('. ')[-1]          # keeps: "А вариантда энг паст заҳира — … (3,6 ойлик жорий харажат)."
    bh2 = text_h(rb, 'body', 14, rw - 0.56)
    ch = 0.2 + 0.42 + bh2 + 0.2
    cy = cb - ch
    if cy < y2:
        warn(f'slide 9 right column over by {y2 - cy:.2f}')
    rect(sl, rx, cy, rw, ch, fill=PERI, radius=0.4, name='Recommendation')
    tbox(sl, rx + 0.28, cy + 0.18, rw - 0.56, 0.36, [rh_], size=22, kind='head', lead=24)
    tbox(sl, rx + 0.28, cy + 0.2 + 0.42, rw - 0.56, bh2, rb, size=14)
    # 39 % note between composition and card
    nt = T(9, 4).split('). ', 1)[1]
    nh = text_h(nt, 'body', 12, rw)
    if y2 + nh + 0.1 <= cy:
        tbox(sl, rx, y2, rw, nh, nt, size=12, color=GRAPH)
    else:
        warn(f'slide 9: 39 % note dropped (no room) y2={y2:.2f} nh={nh:.2f} cy={cy:.2f}')

# =================================================================== 10 · monitoring
def s10():
    n = 10
    sl = new_slide(10)
    header(sl, '05 · Ижро ва назорат', sentence(T(10, 1)))
    cb = cb_of(footer(sl, n, T(10, 2)))
    c1w, c2w = 3.3, 4.0
    c3w = CW - c1w - c2w - 2 * GAP
    # col 1 — responsibility chain
    nodes = [T(10, j).split('\n') for j in (4, 6, 8, 10, 12, 14, 16)]
    y = CT
    dx = M + 0.07
    ys = []
    for i, (t1, t2) in enumerate(nodes):
        ind = 0.0 if i < 3 else 0.32
        if i == 3:
            yb = y + 0.02
            y += 0.16
        x = M + 0.3 + ind
        w_ = c1w - 0.3 - ind
        hh = text_h(t2, 'body', 12, w_)
        tbox(sl, x, y, w_, 0.3, [t1], size=18, kind='head', lead=20)
        tbox(sl, x, y + 0.29, w_, hh, t2, size=12, color=GRAPH)
        ys.append((y + 0.15, ind))
        y += 0.29 + hh + 0.07
    check_bottom(n, y - 0.07, cb)
    line(sl, dx, ys[0][0], dx, yb)
    line(sl, dx, yb, dx + 0.32, yb)
    line(sl, dx + 0.32, yb, dx + 0.32, ys[-1][0])
    for yy, ind in ys:
        oval(sl, dx + ind, yy, 0.12, PARCH, line=GRAPH)
    # col 2 — monthly report mock-up
    x2 = M + c1w + GAP
    tbox(sl, x2, CT, c2w, 0.4, T(10, 25).upper(), size=10, color=GRAPH)
    t = TB(10, 26)
    colw = [1.6, 1.0, 0.75, c2w - 3.35]
    th, _ = table(sl, x2, CT + 0.32, colw, t, size=14, name='Monthly report')
    check_bottom(n, CT + 0.32 + th, cb)
    # col 3 — control point card
    x3 = x2 + c2w + GAP
    rect(sl, x3, CT, c3w, cb - CT, fill=PERI, radius=0.4, name='Control point card')
    ix, iw = x3 + 0.28, c3w - 0.56
    date, lab = T(10, 29).split('\xa0— ')
    tbox(sl, ix, CT + 0.27, iw, 0.45, [date], size=28, kind='head', color=BLUE, lead=30)
    tbox(sl, ix, CT + 0.77, iw, 0.2, lab, size=10, color=GRAPH)
    cond = T(10, 30)
    chh = text_h(cond, 'body', 14, iw, after=3)
    tbox(sl, ix, CT + 1.08, iw, chh, cond, size=14, after=3)
    yy = CT + 1.08 + chh + 0.16
    line(sl, ix, yy, ix + iw, yy)
    rt = T(10, 31)
    rh = text_h(rt, 'body', 14, iw)
    tbox(sl, ix, yy + 0.16, iw, rh, rt, size=14)
    check_bottom(n, yy + 0.16 + rh + 0.25, cb)

# =================================================================== 11 · risks table
def s11():
    n = 11
    sl = new_slide(11)
    header(sl, '05 · Ижро ва назорат', sentence(T(11, 1)))
    cb = cb_of(footer(sl, n, T(11, 2)))
    t = TB(11, 3)
    colw = [2.9, 1.6, 5.75, CW - 2.9 - 1.6 - 5.75]
    rows = [t[0]]
    for i, r in enumerate(t[1:]):
        row = [{'t': c} for c in r]
        if i == 0:
            for c in row:
                c['fill'] = PERI
            row[1]['color'] = BLUE
        rows.append(row)
    th, _ = table(sl, M, CT, colw, rows, size=14, pady=0.055, name='Risk table')
    check_bottom(n, CT + th, cb)

# =================================================================== 12–13 · six decisions (table, 2 parts)
def decisions(n, part):
    sl = new_slide(12 if part == 1 else None)
    header(sl, f'06 · Қарорлар · {part}/2', sentence(T(12, 1)))
    cb = cb_of(footer(sl, n, T(12, 2)))
    t = TB(12, 4)
    body = t[1:4] if part == 1 else t[4:7]
    colw = [0.5, 5.6, 2.55, 2.55, CW - 0.5 - 5.6 - 2.55 - 2.55]
    th, _ = table(sl, M, CT, colw, [t[0]] + body, size=16, hdr_size=11, pady=0.12,
                  aligns=['l', 'l', 'l', 'l', 'r'], name='Decisions table')
    check_bottom(n, CT + th, cb)

def s12():
    decisions(12, 1)

def s13():
    decisions(13, 2)

# =================================================================== 14 · draft resolution (dark, final)
def s14():
    n = 14
    sl = new_slide(None, dark=True)
    picture(sl, A('blob-final.png'), 0, 0, W, H, descr='', decorative=True, name='Gradient')
    pill(sl, M, PILL_Y, '06 · Қарорлар', size=10, color=PARCH, border=ASH, name='Section')
    footer(sl, n, dark=True)
    t = T(12, 3)
    head, rest = t.split(': ', 1)
    items = [s_.strip() for s_ in rest.split(';')]
    tbox(sl, M, 1.45, 8.4, 0.9, [head], size=60, kind='head', color=PARCH, name='Title')
    y = 2.85
    for it in items:
        num, body = it.split(')', 1)
        body = body.strip().rstrip('.').replace('\xa0', ' ').replace('2027 йил', '2027\xa0йил')
        body = body.replace('А вариант', 'А\xa0вариант')
        body = body[0].upper() + body[1:]
        hh = text_h(body, 'head', 28, 7.6, lead=33)
        tbox(sl, M, y + 0.06, 0.8, 0.3, [num.zfill(2)], size=11, color=ASH, check=False)
        tbox(sl, M + 0.8, y, 7.6, hh, [body], size=28, kind='head', color=PARCH, lead=33)
        y += hh + 0.3
        line(sl, M, y - 0.15, M + 8.4, y - 0.15, color=GRAPH)
    wt = T(12, 5)
    wx = M + 8.4 + GAP_L + 0.3
    ww = W - M - wx
    wh = text_h(wt, 'body', 14, ww)
    tbox(sl, wx, 2.85, ww, wh, wt, size=14, color=ASH, name='Without decisions')
    logo_card(sl, W - M - 2.9, FB - 0.2 - 0.3 - 1.24)

# =================================================================== appendices
def app_header(sl, k, s):
    header(sl, f'{k}-илова', sentence(T(s, 1), strip_prefix=True))

def s15():
    n = 15
    sl = new_slide(13)
    app_header(sl, 1, 13)
    cb = cb_of(footer(sl, n, T(13, 2)))
    t = TB(13, 3)
    colw = [0.8, 3.6, 3.0, 1.8, CW - 0.8 - 3.6 - 3.0 - 1.8]
    rows = [r[:] for r in t]
    rows[-1] = [{'t': c, 'color': BLUE if j == 4 else INK} for j, c in enumerate(rows[-1])]
    th, _ = table(sl, M, CT, colw, rows, size=12, pady=0.03, aligns=['l', 'l', 'l', 'l', 'r'],
                  name='Exhibits table')
    check_bottom(n, CT + th, cb)

def s16():
    n = 16
    sl = new_slide(14)
    app_header(sl, 2, 14)
    cb = cb_of(footer(sl, n, T(14, 2)))
    t = TB(14, 3)
    colw = [2.2, 2.2, 2.3, 2.2, CW - 2.2 - 2.2 - 2.3 - 2.2]
    rows = [[({'t': c, 'fill': PERI} if j == 2 else c) for j, c in enumerate(r)] for r in t]
    rows[1][2]['color'] = BLUE
    th, _ = table(sl, M, CT, colw, rows, size=12, name='Scenarios table')
    y = CT + th + GAP
    ft = T(14, 4)
    fh = text_h(ft, 'body', 14, CW)
    tbox(sl, M, y, CW, fh, ft, size=14)
    check_bottom(n, y + fh, cb)

def s17():
    n = 17
    sl = new_slide(15)
    app_header(sl, 3, 15)
    cb = cb_of(footer(sl, n, T(15, 2)))
    t = TB(15, 3)
    colw = [3.2] + [(CW - 3.2) / 5] * 5
    th, _ = table(sl, M, CT, colw, t, size=12, pady=0.045, name='KPI table')
    check_bottom(n, CT + th, cb)

def s18():
    n = 18
    sl = new_slide(16)
    app_header(sl, 4, 16)
    cb = cb_of(footer(sl, n, T(16, 2)))
    t = TB(16, 3)
    mw = 0.78
    colw = [1.3] + [mw] * 12 + [CW - 1.3 - 12 * mw]
    th, _ = table(sl, M, CT, colw, t, size=12, hdr_size=10, padx=0.05, aligns=['l'] + ['r'] * 13,
                  name='Monthly budget')
    y = CT + th + 0.4
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    ch_src = src.slides[15].shapes[4].chart
    cd = CategoryChartData()
    cd.categories = list(ch_src.plots[0].categories)
    for s_ in ch_src.plots[0].series:
        cd.add_series(s_.name, list(s_.values), number_format='#,##0.0')
    chw = 6.3
    gf = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, E(M), E(y), E(chw), E(cb - y), cd)
    set_name(gf, 'Budget chart')
    style_chart(gf.chart, ch_src.chart_title.text_frame.text)
    rx = M + chw + GAP_L
    rw = W - M - rx
    tbox(sl, rx, y, rw, 0.2, T(16, 5).upper(), size=10, color=GRAPH)
    t2 = TB(16, 6)
    cw2 = [1.85] + [(rw - 1.85) / 4] * 4
    th2, _ = table(sl, rx, y + 0.3, cw2, t2, size=12, padx=0.06, pady=0.04, aligns=['l', 'r', 'r', 'r', 'r'],
                   name='Reserve table')
    yy = y + 0.3 + th2 + 0.25
    hw = (rw - GAP) / 2
    for i, (lj, vj) in enumerate(((7, 8), (9, 10))):
        x = rx + i * (hw + GAP)
        lh = text_h(T(16, lj).upper(), 'body', 10, hw)
        tbox(sl, x, yy, hw, lh, T(16, lj).upper(), size=10, color=GRAPH)
        tbox(sl, x, yy + lh + 0.08, hw, 0.4, [T(16, vj)], size=22, kind='head', lead=24)
        check_bottom(n, yy + lh + 0.08 + 0.4, cb)

def style_chart(chart, title):
    from pptx.enum.chart import XL_LEGEND_POSITION
    chart.has_title = True
    chart.chart_title.text_frame.text = title
    r = chart.chart_title.text_frame.paragraphs[0].runs[0]
    _style_run(r, 11, 'body', INK)
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.TOP
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(10); chart.legend.font.name = BODY_FONT
    chart.legend.font.color.rgb = RGBColor.from_string(GRAPH)
    plot = chart.plots[0]
    plot.gap_width = 60; plot.overlap = -10
    for s_, col in zip(plot.series, (BLUE, ASH)):
        s_.format.fill.solid(); s_.format.fill.fore_color.rgb = RGBColor.from_string(col)
        s_.format.line.fill.background()
    va, ca = chart.value_axis, chart.category_axis
    for ax in (va, ca):
        ax.tick_labels.font.size = Pt(10); ax.tick_labels.font.name = BODY_FONT
        ax.tick_labels.font.color.rgb = RGBColor.from_string(SMOKE)
        ax.format.line.color.rgb = RGBColor.from_string(ASH)
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor.from_string(ASH)
    va.major_gridlines.format.line.width = Pt(0.75)
    va.format.line.fill.background()
    va.tick_labels.number_format = '#,##0'; va.tick_labels.number_format_is_linked = False
    ca.has_major_gridlines = False

def s19():
    n = 19
    sl = new_slide(17)
    app_header(sl, 5, 17)
    cb = cb_of(footer(sl, n, T(17, 2)))
    t = TB(17, 3)
    raw = src.slides[16].shapes[3].table
    wk = 0.5
    colw = [0.45, CW - 0.45 - 13 * wk] + [wk] * 13
    rows = []
    for ri, r in enumerate(t):
        row = []
        for ci, c in enumerate(r):
            d = {'t': c}
            if ri == 0 and ci >= 2:
                d.update(size=9, align='c', upper=False)
            if ri > 0 and ci >= 2:
                tcpr = raw.cell(ri, ci)._tc.tcPr
                if tcpr is not None and tcpr.find(qn('a:pattFill')) is not None:
                    d.update(pattern=SMOKE, fill=PARCH)
            row.append(d)
        rows.append(row)
    th, _ = table(sl, M, CT, colw, rows, size=12, padx=0.06, pady=0.04, name='First 90 days')
    y = CT + th + GAP
    st = T(17, 4)
    sh = text_h(st, 'body', 14, CW)
    tbox(sl, M, y, CW, sh, st, size=14)
    check_bottom(n, y + sh, cb)

def s20():
    n = 20
    sl = new_slide(18)
    app_header(sl, 6, 18)
    cb = cb_of(footer(sl, n, T(18, 2)))
    cols = ((4, 5), (7, 8), (10, 11))
    avail = cb - (CT + 0.55)
    # widths proportional to the text each column must hold
    free = CW - 2 * GAP
    best = None
    for a in [x / 20 for x in range(50, 120)]:
        for b in [x / 20 for x in range(40, 100)]:
            c = free - a - b
            if c < 2.0:
                continue
            ws_ = [a, b, c]
            hs_ = [text_h(T(18, bj), 'body', 11, w_ - 0.2, after=3) for (_, bj), w_ in zip(cols, ws_)]
            if best is None or max(hs_) < best[0]:
                best = (max(hs_), ws_, hs_)
    _, ws, hs = best
    x = M
    for (hj, bj), w_, h_ in zip(cols, ws, hs):
        tbox(sl, x, CT, w_, 0.32, [T(18, hj)], size=20, kind='head', lead=22)
        line(sl, x, CT + 0.4, x + w_, CT + 0.4)
        tbox(sl, x, CT + 0.55, w_, h_, T(18, bj), size=11, after=3, bullets=True)
        check_bottom(n, CT + 0.55 + h_, cb)
        x += w_ + GAP

for f in (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15, s16, s17, s18, s19, s20):
    f()

# ---- speaker notes: copied verbatim (XML paragraphs) ----------------------------------
for sl, si in SLIDES:
    if si is None:
        continue
    s_src = src.slides[si - 1]
    if not s_src.has_notes_slide:
        continue
    src_tx = s_src.notes_slide.notes_placeholder._element.find(qn('p:txBody'))
    ph = sl.notes_slide.notes_placeholder
    dst_tx = ph._element.find(qn('p:txBody'))
    for p_ in dst_tx.findall(qn('a:p')):
        dst_tx.remove(p_)
    for p_ in src_tx.findall(qn('a:p')):
        dst_tx.append(copy.deepcopy(p_))

# ---- theme: palette colours + Cambria/Consolas, so nothing off-palette is left ----------
import re as _re
THEME_COLORS = {'dk1': INK, 'lt1': PARCH, 'dk2': GRAPH, 'lt2': ASH, 'accent1': BLUE, 'accent2': PERI,
                'accent3': SMOKE, 'accent4': SKY, 'accent5': MINT, 'accent6': CORAL,
                'hlink': BLUE, 'folHlink': GRAPH}
for part in prs.part.package.iter_parts():
    if str(part.partname).startswith('/ppt/theme/'):
        x = part.blob.decode('utf-8')
        for k, v in THEME_COLORS.items():
            x = _re.sub(rf'<a:{k}>.*?</a:{k}>', f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>', x, flags=_re.S)
        x = x.replace('val="000000"', f'val="{INK}"')
        x = _re.sub(r'(<a:majorFont><a:latin typeface=")[^"]*"', r'\1Cambria"', x)
        x = _re.sub(r'(<a:minorFont><a:latin typeface=")[^"]*"', r'\1Consolas"', x)
        x = x.replace('name="Office Theme"', 'name="Monad"', 1).replace('<a:clrScheme name="Office"', '<a:clrScheme name="Monad"')
        x = x.replace('<a:fontScheme name="Office"', '<a:fontScheme name="Monad"')
        if hasattr(part, '_element'):
            from pptx.oxml import parse_xml
            part._element = parse_xml(x.encode('utf-8'))
        else:
            part._blob = x.encode('utf-8')

# ---- master and layouts: stretch the 4:3 template frames to 16:9; parchment background ---
k_ = W / 10.0
for obj in [prs.slide_master] + list(prs.slide_layouts):
    for shp in obj.shapes:
        if shp.left is not None:
            shp.left = int(shp.left * k_); shp.width = int(shp.width * k_)
background(prs.slide_master, PARCH)

# ---- PowerPoint sections -------------------------------------------------------------
P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'
pres_el = prs.part._element
ids = [e.get('id') for e in pres_el.find(qn('p:sldIdLst'))]
SECTIONS = [('Тошкент политехника музейи', [0]), ('01 · Асосий мазмун', [1]), ('02 · Ҳозирги ҳолат', [2, 3]),
            ('03 · 2027 йил режаси', [4, 5, 6, 7]), ('04 · Бюджет', [8]), ('05 · Ижро ва назорат', [9, 10]),
            ('06 · Қарорлар', [11, 12, 13]), ('Иловалар', list(range(14, 20)))]
ext_lst = pres_el.find(qn('p:extLst'))
if ext_lst is None:
    ext_lst = etree.SubElement(pres_el, qn('p:extLst'))
ext = etree.SubElement(ext_lst, qn('p:ext')); ext.set('uri', '{521415D9-36F7-43E2-AB2F-B90AF26B5E84}')
sec_lst = etree.SubElement(ext, f'{{{P14}}}sectionLst', nsmap={'p14': P14})
for name, idx in SECTIONS:
    sec = etree.SubElement(sec_lst, f'{{{P14}}}section'); sec.set('name', name)
    sec.set('id', '{' + str(uuid.uuid4()).upper() + '}')
    sl_ = etree.SubElement(sec, f'{{{P14}}}sldIdLst')
    for i in idx:
        etree.SubElement(sl_, f'{{{P14}}}sldId').set('id', ids[i])

os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs.core_properties.title = sentence(T(1, 2))
prs.core_properties.author = ''
prs.save(OUT)
print('saved', OUT, len(prs.slides), 'slides')
for w_ in WARN:
    print('WARN', w_)
