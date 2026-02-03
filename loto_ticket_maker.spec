# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file cho Loto Ticket Maker
Đóng gói thành executable Windows (.exe)
"""

a = Analysis(
    ['entrypoint.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets', 'assets'),  # Copy toàn bộ folder assets (ảnh, preset)
        ('src/loto_ticket_maker/ui/style.qss', 'loto_ticket_maker/ui'),  # Copy stylesheet
    ],
    hiddenimports=[
        'loto_ticket_maker',
        'loto_ticket_maker.ui',
        'loto_ticket_maker.core',
        'loto_ticket_maker.render',
        'loto_ticket_maker.export',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LotoTicketMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Không hiển thị console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
