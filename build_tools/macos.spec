# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

root = os.path.abspath(os.path.join(SPECPATH, ".."))
a = Analysis([os.path.join(root, 'STDF-Viewer.py')],
             pathex=[root],
             binaries=[],
             datas=[(os.path.join(root, 'fonts/*.ttf'), 'fonts')],
             hiddenimports=[],
             hookspath=[],
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
          upx=True,
          console=False , icon=os.path.join(root, 'build_tools/macos.icns'))
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='STDF-Viewer')
app = BUNDLE(coll,
            name='STDF Viewer.app',
            icon=os.path.join(root, 'build_tools/macos.icns'),
            bundle_identifier=None,
            info_plist={
                'NSPrincipalClass': 'NSApplication',
                'NSAppleScriptEnabled': False,
                'CFBundleDocumentTypes': [
                    {
                        'CFBundleTypeName': 'Standard Test Data Format',
                        'CFBundleTypeIconFile': 'macos.icns',
                        'CFBundleTypeExtensions': ['std', 'stdf', 'std*'],
                        'CFBundleTypeRole': 'Viewer'
                        }
                    ]
                },
            )
