#
# ViewerInstance.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: October 5th 2026
# -----
# Last Modified: Tue Oct 06 2026
# Modified By: noonchen
# -----
# Copyright (c) 2020 noonchen
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

'''
Keep one window per user, and let a later launch hand its files to that window.

Two windows would share the setting file and the working databases under the app
data folder and clear each other's on exit, so the first launch owns the window
and every later one passes its files over and leaves.

The lock settles the election, the local socket carries the files:
`QLocalServer` alone cannot elect, two processes can both end up listening on
the same name (see the notes below). The socket is a Unix domain socket on
macOS/Linux and a named pipe on Windows, it is not a network port.
'''

import json
import logging
import os
import sys
import time

from PyQt5 import QtCore, QtNetwork, QtWidgets
from PyQt5.QtCore import pyqtSignal as Signal
# pyside2
# from PySide2 import QtCore, QtNetwork, QtWidgets
# from PySide2.QtCore import Signal
# pyside6
# from PySide6 import QtCore, QtNetwork, QtWidgets
# from PySide6.QtCore import Signal


from deps.SharedSrc import LOG_NAME

logger = logging.getLogger(LOG_NAME)


class ViewerInstance(QtCore.QObject):
    '''
    This class provides methods that ensuring
    a single app instance, this design is required
    because two or more app process would share the
    config and database and clear each other's on exit.
    
    For Windows & Linux that launches multiple
    instances by default.
    
    macOS only launches a single process for an app.
    '''
    
    # lock file for determining owner of viewer instance
    LOCK_NAME = "STDF-Viewer.lock"
    # timeout (ms) for non-owner waits owner
    HANDOFF_TIMEOUT = 1000
    # delay (s) between consecutive socket.write() attempts
    RETRY_INTERVAL = 0.02

    # signal for owner to open given files
    filesReceived = Signal(list)
    # signal for owner to raise window to front
    activateRequested = Signal()

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._lock = QtCore.QLockFile(os.path.join(sys.appDataFolder, self.LOCK_NAME))
        self._server: QtNetwork.QLocalServer | None = None

    def tryClaim(self) -> bool:
        '''
        Take the ownership of app instance.
        
        Return True if success, otherwise False if it's already taken.
        '''
        if self._isOwner():
            self._startFileListener()
            return True
        return False
    
    def passFilesToOwner(self, files: list[str]):
        '''
        Hand off file paths to current app instance.

        If failed, a warning dialog is shown to the user.
        '''
        # use absolute path to ensure the owner
        # receives correct file locations
        payload = json.dumps([os.path.abspath(path) for path in files])
        payload = payload.encode("utf-8")
        # if multiple viewer app start at same time, the owner
        # that acquires the lock may not have a listener yet.
        #
        # for other launches, wait a short time and try again,
        # until the deadline is reached.
        deadline = time.monotonic() + self.HANDOFF_TIMEOUT / 1000
        warnMsg = self.tr("STDF-Viewer was already running, but new file request "
                          "was not accepted.\nClose it and try again.")
        while True:
            socket = QtNetwork.QLocalSocket()
            socket.connectToServer(ViewerInstance.pipeName())
            if socket.waitForConnected(self.HANDOFF_TIMEOUT):
                wcnt = socket.write(payload)
                # `waitForBytesWritten` drives the payload out before closing
                while socket.bytesToWrite():
                    if not socket.waitForBytesWritten(self.HANDOFF_TIMEOUT):
                        break
                if wcnt == len(payload) and socket.bytesToWrite() == 0:
                    warnMsg = ""
                else:
                    logger.warning(
                        "Files sent to the running STDF-Viewer may not complete: "
                        "%d of %d bytes written, %d still pending, state=%s, %s",
                        wcnt, len(payload), socket.bytesToWrite(),
                        socket.state(), socket.errorString())
                # payload sent complete
                socket.disconnectFromServer()
                break
            if time.monotonic() >= deadline:
                # cannot reach the owner within the timeout,
                # log and show warning dialog.
                logger.warning(
                    f"Cannot send files {files} to the running "
                    f"STDF-Viewer process: {socket.errorString()}")
                break
            time.sleep(self.RETRY_INTERVAL)
        
        if warnMsg:
            QtWidgets.QMessageBox.warning(None, self.tr("Warning"), warnMsg)
    
    @staticmethod
    def pipeName() -> str:
        '''
        Name of the local socket for file paths hand offs.
        '''
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
        return "STDF-Viewer-" + user.replace(" ", "-")

    def _isOwner(self) -> bool:
        '''
        Elect one window per user, an atomic lock settles the race.
        '''
        if self._lock.tryLock(0):
            return True
        # a stale lock left by a killed process is taken over by QLockFile
        # itself, so a failure here means a live window holds the lock
        if self._lock.error() != QtCore.QLockFile.LockError.LockFailedError:
            # the lock file cannot be used at all (e.g. the folder is read only),
            # refusing to start would be worse than running without the guarantee
            logger.warning("Cannot use the instance lock file: %s",
                           self._lock.error())
            return True
        return False

    def _startFileListener(self):
        '''
        Listen for the files from later launches.
        '''
        name = ViewerInstance.pipeName()
        # a previous owner may have crashed before it cleaned up, and the lock
        # above guarantees that no window is answering on this name right now
        QtNetwork.QLocalServer.removeServer(name)
        self._server = QtNetwork.QLocalServer(self)
        if not self._server.listen(name):
            # the window is still usable without hand offs, so keep the lock
            logger.warning("Cannot listen for file hand offs: %s",
                           self._server.errorString())
            self._server = None
            return
        self._server.newConnection.connect(self._acceptHandOff)

    def _acceptHandOff(self):
        '''
        Read what a later launch sent; the sender disconnects when it is done.
        '''
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        payload = bytearray()
        socket.readyRead.connect(lambda: payload.extend(socket.readAll().data()))
        socket.disconnected.connect(lambda: self._openHandOff(socket, payload))

    def _openHandOff(self, socket: QtNetwork.QLocalSocket, payload: bytearray):
        paths = self._decodeHandOff(socket, payload)
        if paths:
            self.filesReceived.emit(paths)
        # a later launch without files just wants the window in front
        self.activateRequested.emit()
        socket.deleteLater()

    def _decodeHandOff(self, socket: QtNetwork.QLocalSocket,
                       payload: bytearray) -> list[str]:
        # whatever is still buffered belongs to the same message
        payload.extend(socket.readAll().data())
        try:
            paths = json.loads(bytes(payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            paths = None
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            if payload:
                logger.warning(f"Ignored an invalid file hand off payload: {paths}")
            return []
        return paths

