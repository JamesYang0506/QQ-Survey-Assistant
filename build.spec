# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec - QQ问卷星报名助手
构建命令: pyinstaller build.spec
"""
import os

basedir = r'C:\Users\lenovo\Desktop\QQ报名助手'

a = Analysis(
    ['main.py'],
    pathex=[basedir],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui',
        'playwright', 'playwright.async_api',
        'thefuzz', 'thefuzz.fuzz', 'thefuzz.process',
        'Levenshtein',
        'json', 'logging', 'logging.handlers', 'sqlite3',
    ],
    excludes=['tkinter', 'matplotlib', 'pandas', 'numpy', 'scipy', 'PIL'],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='QQ报名助手',
    debug=False,
    strip=False,
    upx=True,
    console=False,       # 无控制台窗口
    icon=None,
)
