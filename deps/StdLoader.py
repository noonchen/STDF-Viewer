#
# uic_stdLoader.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Sat Oct 03 2026
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



import time, os, sys, logging, uuid
# pyqt5
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QTranslator
# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtCore import Signal, Slot, QTranslator
# pyside6
# from PySide6 import QtCore, QtWidgets
# from PySide6.QtCore import Signal, Slot, QTranslator

import rust_stdf_helper
from deps.DataInterface import DataInterface
from deps.SharedSrc import getSetting, LOG_NAME, get_file_size, mirFieldNames


logger = logging.getLogger(LOG_NAME)

class flags:
    stop = False


def readEarlyFileInfo(stdPaths: list[list[str]]) -> dict:
    '''File Info entries the MIR alone can provide, counters left to the caller'''
    groups = []
    # one value per file, like the database stores them
    meta = {fn: [] for fn in mirFieldNames}
    for fgroup in stdPaths:
        if not fgroup:
            continue
        names, sizes = [], []
        for path in fgroup:
            names.append(os.path.basename(path))
            try:
                sizes.append(get_file_size(path))
            except OSError:
                sizes.append("")
        for path in fgroup:
            mir = rust_stdf_helper.read_MIR(path)
            for fn in mirFieldNames:
                value = mir.get(fn)
                meta[fn].append(str(value) if value is not None else "")
        groups.append({"path": fgroup[0], "names": names, "sizes": sizes})
    # drop the fields no file carries, the database skips those too
    meta = {fn: tuple(v) for fn, v in meta.items() if any(v)}
    return {"groups": groups, "meta": meta,
            "num_files": sum(len(g) for g in stdPaths)}


class signal4Loader(QtCore.QObject):
    # get progress from reader
    progressBarSignal = Signal(int)
    # get `DataInterface` from reader
    dataInterfaceSignal_reader = Signal(object)
    # get close signal
    closeSignal = Signal()
    
    # object signal from parent
    dataInterfaceSignal_parent = None
    # File Info signal from parent
    metadataSignal_parent = None
    # status bar signal from parent
    msgSignal = None
    # status bar signal from parent, used when the message must warn
    statusSignal = None


TestIDTypeDict = {
                "Number + Name": rust_stdf_helper.TestIDType.TestNumberAndName,
                "Number Only": rust_stdf_helper.TestIDType.TestNumberOnly
                }


class StdfLoader(QtCore.QObject):
    
    def __init__(self, parentSignal = None, parent = None):
        super().__init__(parent)
        self.translator = QTranslator(self)
        self.abandoned = False
        
        self.signals = signal4Loader()
        self.signals.dataInterfaceSignal_reader.connect(self.sendDataInterface)
        self.signals.closeSignal.connect(self.closeLoader)
        
        self.signals.dataInterfaceSignal_parent = getattr(parentSignal, "dataInterfaceSignal", None)
        self.signals.metadataSignal_parent = getattr(parentSignal, "metadataSignal", None)
        self.signals.msgSignal = getattr(parentSignal, "loadStatusSignal", None)
        # errors keep the shared status signal, they raise a dialog as well
        self.signals.statusSignal = getattr(parentSignal, "statusSignal", None)
        
    def loadFile(self, stdPaths: list[list[str]]):
        # ignore a new request while the previous one runs
        curThread = self.__dict__.get("thread")
        if curThread is not None and curThread.isRunning():
            return
        self.abandoned = False
        self.setParentLoading(True)
        self.sendEarlyFileInfo(stdPaths)
        # create new thread and move StdfReader to the new thread
        self.thread = QtCore.QThread(parent=self)
        self.reader = StdfReader(self.signals)
        self.reader.readThis(stdPaths)
        
        # read test item identifier from setting
        setting = getSetting()
        if setting.gen.id_type in TestIDTypeDict:
            self.reader.setIDType(TestIDTypeDict[setting.gen.id_type])
        
        self.reader.moveToThread(self.thread)
        self.thread.started.connect(self.reader.readBegin)
        self.thread.start()
    
    def sendEarlyFileInfo(self, stdPaths: list[list[str]]):
        if self.signals.metadataSignal_parent is None:
            return
        try:
            payload = readEarlyFileInfo(stdPaths)
        except Exception:
            logger.exception("Failed to read file info early")
            return
        self.signals.metadataSignal_parent.emit(payload)
    
    def setParentLoading(self, loading: bool):
        setter = getattr(self.parent(), "onLoadState", None)
        if setter is not None:
            setter(loading)
    
    def abandon(self):
        # discard current load at any stages
        self.abandoned = True
        marker = getattr(self.parent(), "markAbandoned", None)
        if marker is not None:
            marker()
        if self.reader is not None:
            self.reader.flag.stop = True

    def askAbandon(self) -> bool:
        return QtWidgets.QMessageBox.question(
            self.parent(), "QUIT", self.tr("Are you sure to give up loading?"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes

    @Slot(object)
    def sendDataInterface(self, di: object):
        # send `DataInterface` from reader to mainUI
        # an abandoned load discard current build even if finished, then restore old db
        self.signals.dataInterfaceSignal_parent.emit(None if self.abandoned else di)
    
    @Slot()
    def closeLoader(self):
        self.thread.quit()
        self.thread.wait()
        self.reader = None
        self.setParentLoading(False)
        
        
        
class StdfReader(QtCore.QObject):
    def __init__(self, QSignal:signal4Loader):
        super().__init__()
        if (QSignal is None or
            QSignal.dataInterfaceSignal_reader is None or
            QSignal.msgSignal is None):
            raise ValueError("Qsignal is invalid, parse is terminated")
        
        self.QSignals = QSignal
        self.progressBarSignal = self.QSignals.progressBarSignal
        self.closeSignal = self.QSignals.closeSignal
        self.dataInterfaceSignal = self.QSignals.dataInterfaceSignal_reader
        self.msgSignal = self.QSignals.msgSignal
        self.statusSignal = self.QSignals.statusSignal
        self.flag = flags()     # used for stopping parser
        self.idType = rust_stdf_helper.TestIDType.TestNumberAndName
        
    def readThis(self, stdPaths: list[list[str]]):
        self.stdPaths = stdPaths
        
    def setIDType(self, idType):
        self.idType = idType
        
    @Slot()
    def readBegin(self):
        di = DataInterface()
        sendDI = True
        showWarning = False
        finalMsg = ""

        try:
            if self.msgSignal: self.msgSignal.emit(self.tr("Loading STD file..."), 0)
            start = time.time()
            # auto generate a database name
            databasePath = os.path.join(sys.rootFolder, "logs", f"{uuid.uuid4().hex}.db")
            rust_stdf_helper.generate_database(databasePath, self.stdPaths, self.idType, self.progressBarSignal, self.flag)
            end = time.time()
            if self.flag.stop:
                # user terminated...
                sendDI = False
                finalMsg = self.tr("Loading cancelled by user")
            else:
                # send Data_interface object
                # sqlite cannot be used between thread
                # thus we need to store the db path and
                # load database in the main thread
                di.dbPath = databasePath
                finalMsg = self.tr("Load completed, process time {:.3f} sec").format(end - start)
                
        except Exception as e:
            # set stop flag to True to stop rust process
            # in case it's an exception from python code
            self.flag.stop = True
            # clean data interface
            di.close()
            logger.exception("\nError occurred when parsing the file")
            sendDI = False
            showWarning = True
            finalMsg = str(e)
            
        self.dataInterfaceSignal.emit(di if sendDI else None)
        if self.msgSignal:
            if showWarning:
                # the error text stays, it tells why nothing was read
                self.statusSignal.emit(finalMsg, False, True, False)
            else:
                self.msgSignal.emit(finalMsg, 4000)
        self.closeSignal.emit()
        

