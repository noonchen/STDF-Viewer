#
# fileAssoc.py - STDF Viewer
#
# Claim the .stdf and .std extensions for this program on Windows.
#
# Linux and macOS do not need this: the deb ships a .desktop file with a
# MimeType and the app bundle carries CFBundleDocumentTypes, so the package
# manager already owns the association there.
#

import os
import sys

# a stable ProgID, so repeated registrations never pile up new keys
PROG_ID = "STDFViewer.stdf"
EXTENSIONS = (".stdf", ".std")
# shown by Explorer in the "Type" column
TYPE_NAME = "STDF Test Data File"

_CLASSES = r"Software\Classes"
# value names under the ProgID recording who owned an extension before us,
# so unregister() can hand it back instead of dropping the association
_PREVIOUS = "_previousOwner_"


def _winreg():
    """Import winreg, or return None on a platform that has no registry."""
    try:
        import winreg
    except ImportError:
        return None
    return winreg


def _launchCommand() -> str:
    """Command line Windows should run when a file is opened."""
    if getattr(sys, "frozen", False):
        # frozen by PyInstaller: the exe is the entry point
        return '"%s" "%%1"' % sys.executable

    # running from source: hand the script to its own interpreter
    return '"%s" "%s" "%%1"' % (sys.executable, os.path.abspath(sys.argv[0]))


def _iconPath() -> str:
    """Only a frozen build has an icon to point at."""
    return sys.executable if getattr(sys, "frozen", False) else ""


def _owner(winreg, ext: str) -> str:
    """ProgID currently claiming `ext`, or an empty string."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLASSES + "\\" + ext) as key:
            return winreg.QueryValueEx(key, "")[0]
    except OSError:
        return ""


def _previousOwners(winreg) -> dict:
    """Who held each extension before this program claimed it."""
    found = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLASSES + "\\" + PROG_ID) as key:
            index = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                if name.startswith(_PREVIOUS):
                    found[name[len(_PREVIOUS):]] = value
    except OSError:
        pass
    return found


def isSupported() -> bool:
    """True where the program can write the association itself."""
    return _winreg() is not None


def isRegistered() -> bool:
    """True when this program is what Windows opens STDF files with."""
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            _CLASSES + "\\" + PROG_ID + r"\shell\open\command") as key:
            recorded = winreg.QueryValueEx(key, "")[0]
    except OSError:
        return False
    if recorded.lower() != _launchCommand().lower():
        return False
    # the extensions have to point at this ProgID as well
    return all(_owner(winreg, ext) == PROG_ID for ext in EXTENSIONS)


def takenExtensions() -> tuple:
    """Extensions another program already owns, so the user can be warned."""
    winreg = _winreg()
    if winreg is None:
        return ()
    return tuple(ext for ext in EXTENSIONS
                 if _owner(winreg, ext) not in ("", PROG_ID))


def register() -> str:
    """Claim the STDF extensions for this program. Returns a result code."""
    winreg = _winreg()
    if winreg is None:
        # Linux and macOS get their association from the package
        return "unsupported"

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              _CLASSES + "\\" + PROG_ID) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, TYPE_NAME)
            winreg.SetValueEx(key, "FriendlyTypeName", 0, winreg.REG_SZ, TYPE_NAME)
            # remember the current owner, so unregister() can give it back
            for ext in EXTENSIONS:
                before = _owner(winreg, ext)
                winreg.SetValueEx(key, _PREVIOUS + ext, 0, winreg.REG_SZ,
                                  "" if before == PROG_ID else before)
        icon = _iconPath()
        if icon:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  _CLASSES + "\\" + PROG_ID + r"\DefaultIcon") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon + ",0")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              _CLASSES + "\\" + PROG_ID + r"\shell\open\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _launchCommand())
        for ext in EXTENSIONS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  _CLASSES + "\\" + ext) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, PROG_ID)
    except OSError:
        return "failed"
    return "ok"


def unregister() -> str:
    """Drop what register() wrote, leaving other programs' keys alone."""
    winreg = _winreg()
    if winreg is None:
        return "unsupported"

    previous = _previousOwners(winreg)
    mine = False
    for ext in EXTENSIONS:
        if _owner(winreg, ext) != PROG_ID:
            continue
        mine = True
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLASSES + "\\" + ext,
                                0, winreg.KEY_SET_VALUE) as key:
                before = previous.get(ext, "")
                if before:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, before)
                else:
                    # nobody claimed it before us, so leave no value behind
                    winreg.DeleteValue(key, "")
        except FileNotFoundError:
            pass
        except OSError:
            return "failed"

    for path in (r"\shell\open\command", r"\shell\open", r"\shell", r"\DefaultIcon", ""):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _CLASSES + "\\" + PROG_ID + path)
        except FileNotFoundError:
            pass
        except OSError:
            # a leftover subkey means the parent is still in use
            return "failed"
    return "ok" if mine else "nothing"
