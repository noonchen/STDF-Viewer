#
# macOpenFile.py - STDF Viewer
#
# Receive files opened from Finder on macOS.
#
# macOS hands the document to the app as an Apple Event instead of a command
# line argument: a double click leaves sys.argv holding nothing but the
# executable, so an app that only looks at sys.argv never sees the file. The
# paths arrive at the delegate below, and go to the same loader.
#
# Imported from STDF-Viewer.py only on darwin -- the AppKit import is static so
# PyInstaller picks it up, which means this module cannot be imported on other
# platforms.
#

import logging
import sys

import objc
from AppKit import NSApplication, NSObject

from deps.SharedSrc import LOG_NAME

logger = logging.getLogger(LOG_NAME)

# AppKit does not retain the delegate, so keep a reference here
_delegate = None


class _OpenFileDelegate(NSObject):
    """Passes Finder's open requests to the callback given to `install`."""

    def initWithCallback_(self, callback):
        self = objc.super(_OpenFileDelegate, self).init()
        if self is None:
            return None
        self._callback = callback
        return self

    def application_openFiles_(self, application, filenames):
        paths = [str(name) for name in filenames]
        logger.info("opened from Finder: %s", paths)
        self._callback(paths)

    def application_openFile_(self, application, filename):
        path = str(filename)
        logger.info("opened from Finder: %s", path)
        self._callback([path])
        return True


def install(openFunc) -> bool:
    """Ask AppKit to call `openFunc(paths)` when Finder opens documents."""
    if sys.platform != "darwin":
        return False
    global _delegate
    try:
        _delegate = _OpenFileDelegate.alloc().initWithCallback_(openFunc)
        NSApplication.sharedApplication().setDelegate_(_delegate)
    except Exception:
        logger.warning("cannot hook the Finder open event", exc_info=True)
        return False
    return True