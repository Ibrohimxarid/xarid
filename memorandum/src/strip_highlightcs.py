# docx-js emits <w:highlightCs>, which is not in the OOXML schema; drop it.
import re, sys, zipfile, shutil
src = sys.argv[1]; tmp = src + ".tmp"
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        if info.filename.startswith("word/") and info.filename.endswith(".xml"):
            data = re.sub(rb"<w:highlightCs [^>]*/>", b"", data)
        zout.writestr(info, data)
shutil.move(tmp, src)
