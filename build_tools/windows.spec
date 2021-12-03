# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

root = os.path.abspath(os.path.join(SPECPATH, ".."))
a = Analysis([os.path.join(root, 'STDF-Viewer.py')],
             pathex=[],
             binaries=[],
             datas=[(os.path.join(root, 'fonts', '*.ttf'), 'fonts')],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='STDF-Viewer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon=os.path.join(root, 'build_tools', 'windows.ico'))

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=False,
               upx_exclude=[],
               name='STDF-Viewer')