# PyInstaller: pyinstaller IjroNazorati.spec  ->  dist/IjroNazorati.exe (bitta fayl)
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["run_ijro.py"],
    pathex=["."],
    datas=[("ijro/templates", "ijro/templates"), ("ijro/static", "ijro/static")],
    hiddenimports=collect_submodules("waitress"),
    excludes=["tkinter", "numpy", "pandas", "matplotlib", "PIL"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="IjroNazorati",
    console=True,       # oyna ochiq turadi: holat ko'rinadi, yopilsa dastur to'xtaydi
    upx=False,          # antiviruslar UPX bilan siqilgan fayllarni ko'proq shubha qiladi
)
