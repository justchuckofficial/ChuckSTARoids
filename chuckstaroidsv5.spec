# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['chuckstaroidsv5.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include all image files
        ('xwing.gif', '.'),
        ('fire.gif', '.'),
        ('starshot.gif', '.'),
        ('tieshot.gif', '.'),
        ('shot.gif', '.'),
        ('roid.gif', '.'),
        ('tie.gif', '.'),
        ('tieb.gif', '.'),
        ('tiei.gif', '.'),
        ('tiea.gif', '.'),
        ('tiefo.gif', '.'),
        ('spinout.gif', '.'),
        ('smoke.gif', '.'),
        ('stard.gif', '.'),
        ('rebel.gif', '.'),
        ('controls.gif', '.'),
        ('tie fleet.jpg', '.'),
        # Include icon file
        ('xwing.ico', '.'),
        # Include music module
        ('music.py', '.'),
        # Include text files that might be used
        ('*.txt', '.'),
        ('*.md', '.'),
    ],
    hiddenimports=[
        'pygame',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
        'requests',
        'json',
        'threading',
        'music',
        'music.EnhancedMusicPlayer',
        'music.EnhancedAAGACAStyles',
        'pygame.mixer',
        'pygame.mixer_music',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChuckSTARoids_v5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='xwing.ico',
    version=None,
    uac_admin=False,
    uac_uiaccess=False,
)

