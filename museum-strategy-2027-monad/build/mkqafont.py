# Builds QA-only stand-in fonts (never shipped): DejaVu outlines scaled horizontally
# to approximate Consolas (exact mono advance) and Cambria (+~7% slack) widths.
import os, sys
OUT = os.path.expanduser('~/.fonts'); os.makedirs(OUT, exist_ok=True)
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
def make(src, dst, family, sx=None, mono_adv=None):
    f=TTFont(src); gs=f.getGlyphSet(); glyf=f['glyf']; hmtx=f['hmtx']; upm=f['head'].unitsPerEm
    if mono_adv: sx=mono_adv/hmtx['zero'][0]
    for gn in f.getGlyphOrder():
        pen=TTGlyphPen(gs); gs[gn].draw(TransformPen(pen,(sx,0,0,1,0,0)))
        g=pen.glyph(); glyf[gn]=g
        adv,lsb=hmtx[gn]
        g.recalcBounds(glyf)
        hmtx[gn]=(mono_adv if (mono_adv and adv>0) else round(adv*sx), getattr(g,'xMin',0))
    for k in ('GPOS','kern','hdmx','LTSH','VDMX'):
        if k in f: del f[k]
    for rec in f['name'].names:
        if rec.nameID in (1,16): rec.string=family
        elif rec.nameID==4: rec.string=family
        elif rec.nameID==6: rec.string=family.replace(' ','')+'-Regular'
    f['OS/2'].xAvgCharWidth=round(f['OS/2'].xAvgCharWidth*sx)
    f.save(dst)
make('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',os.path.join(OUT, 'QA-Consolas.ttf'),'Consolas',mono_adv=1126)
make('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',os.path.join(OUT, 'QA-Cambria.ttf'),'Cambria',sx=0.84)
os.system('fc-cache -f >/dev/null 2>&1')
