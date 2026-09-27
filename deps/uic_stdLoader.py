#
# uic_stdLoader.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Sun Aug 30 2026
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
from .ui.stdfViewer_loadingUI import Ui_loadingUI
# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtCore import Signal, Slot, QTranslator
# from .ui.stdfViewer_loadingUI_side2 import Ui_loadingUI
# pyside6
# from PySide6 import QtCore, QtWidgets
# from PySide6.QtCore import Signal, Slot, QTranslator
# from .ui.stdfViewer_loadingUI_side6 import Ui_loadingUI

import rust_stdf_helper
from deps.DataInterface import DataInterface
from deps.SharedSrc import (getSetting, LOG_NAME, get_file_size, mirDict,
                            mirFieldNames, buildFileMetaData, join_cells)


logger = logging.getLogger(LOG_NAME)


COUNTER_LABELS = ["Yield", "DUTs Tested", "DUTs Passed", "DUTs Failed",
                  "DUTs Superseded", "DUTs Unknown"]


# joined per file; getFileInfo shows only the first occurrence
JOINED_FIELDS = ("SETUP_T", "START_T", "FINISH_T", "SBLOT_ID")


def header_info_fields(groups: list) -> dict:
    """Collect the header fields of every group into per-group cells.

    Mirrors `DatabaseFetcherRust.getFileInfo()`: within one group a field maps
    to its value when it occurs once, to the joined `#1 → v1\\n#2 → v2` form for
    `JOINED_FIELDS`, and to the first occurrence for every other field. Across
    groups the values stay separate cells, as the finished table shows them.
    """
    fields = {}
    for group in groups:
        names = group.get("paths") or group.get("names") or []
        n = max(1, len(names))
        meta = group.get("meta") or {}
        for key, value in meta.items():
            if key in ("ATR", "SDR", "WIR"):
                continue
            name = {"BYTE_ORDER": "BYTE_ORD", "STDF_VER": "STDF Version"}.get(
                key, key)
            per_file = [str(v) for v in value] if isinstance(value, (list, tuple)) \
                else [str(value)] * n
            per_file = [v for v in per_file if v != ""]
            if not per_file:
                cell = ""
            elif len(per_file) == 1:
                cell = per_file[0]
            elif name in JOINED_FIELDS:
                cell = join_cells(per_file)
            else:
                cell = per_file[0]
            fields.setdefault(name, []).append(cell)
    # the database writes this unconditionally, once per file
    for group in groups:
        names = group.get("paths") or group.get("names") or []
        n = max(1, len(names))
        if "FINISH_T" not in (group.get("meta") or {}):
            fields.setdefault("FINISH_T", []).append(
                join_cells(["1970-01-01 08:00:00 (UTC+08:00)"] * n))
    for name, cells in fields.items():
        while len(cells) < len(groups):
            cells.append("")
    return {name: tuple(cells) for name, cells in fields.items()}


def format_header_info(payload: object,
                       dut_count_dict: dict = None) -> list:
    """Build the early File Info rows from the header payload.

    Goes through the same `buildFileMetaData()` the database path uses, so the
    table layout cannot drift between "still building" and "done". `payload` is
    what the loader emits: `{"groups": [{"names", "paths", "sizes", "meta"}]}`.
    """
    if not isinstance(payload, dict):
        return []
    groups = payload.get("groups") or []
    if not groups:
        return []
    # one entry per group, joined the same way the database path joins them
    file_names = [join_cells(g.get("names") or [g.get("name", "")])
                  for g in groups]
    file_paths = [g.get("paths") or [g.get("path", "")] for g in groups]
    file_sizes = [join_cells(g.get("sizes") or [""]) for g in groups]
    return buildFileMetaData(file_names, file_paths, file_sizes,
                             dut_count_dict or {}, header_info_fields(groups))

def read_group_headers(paths: list) -> dict:
    """Read the header of every file of one group into per-file values.

    MIR fields are collected once per file (`{"SETUP_T": [v1, v2]}`) because the
    database keeps one value per file. FAR-derived fields (`BYTE_ORDER`,
    `STDF_VER`) describe the file group, not a single file, so only the first
    file contributes them.
    """
    meta = {}
    for index, path in enumerate(paths):
        file_meta = {}
        try:
            file_meta.update(rust_stdf_helper.read_MIR(path))
        except Exception:
            logger.exception("cannot read MIR of %s", path)
        try:
            extra = rust_stdf_helper.read_header_extra(path)
            if isinstance(extra, dict):
                if index == 0:
                    file_meta.update(extra)
                else:
                    # keep the group-level FAR info out of the per-file values
                    for key in ("BYTE_ORDER", "STDF_VER"):
                        extra.pop(key, None)
                    file_meta.update(extra)
        except Exception:
            logger.exception("cannot read extra header info of %s", path)
        for key, value in file_meta.items():
            meta.setdefault(key, []).append(str(value))
    return meta


class flags:
    stop = False


class signal4Loader(QtCore.QObject):
    # get progress from reader
    progressBarSignal = Signal(int)
    # progressive DUT counts (so far) from the Rust helper
    statsSignal = Signal(object)
    # get `DataInterface` from reader
    dataInterfaceSignal_reader = Signal(object)
    # get close signal
    closeSignal = Signal(bool)
    # early metadata (MIR) from loader, before the database is ready
    metadataSignal = Signal(object)
    # emitted when a new load starts; the main window should clear old UI
    loadStartedSignal = Signal()
    
    # object signal from parent
    dataInterfaceSignal_parent = None
    # early metadata signal from parent (main window)
    metadataSignal_parent = None
    # parent signal used to clear the old UI when a new load starts
    loadStartedSignal_parent = None
    # status bar signal from parent
    msgSignal = None


TestIDTypeDict = {
                "Number + Name": rust_stdf_helper.TestIDType.TestNumberAndName,
                "Number Only": rust_stdf_helper.TestIDType.TestNumberOnly
                }


class stdfLoader(QtWidgets.QDialog):
    
    def __init__(self, parentSignal = None, parent = None):
        super().__init__(parent)
        self.translator = QTranslator(self)
        self.closeEventByThread = False    # used to determine the source of close event
        
        self.signals = signal4Loader()
        self.signals.progressBarSignal.connect(self.updateProgressBar)
        self.signals.dataInterfaceSignal_reader.connect(self.sendDataInterface)
        self.signals.closeSignal.connect(self.closeLoader)
        
        self.signals.dataInterfaceSignal_parent = getattr(parentSignal, "dataInterfaceSignal", None)
        self.signals.metadataSignal_parent = getattr(parentSignal, "metadataSignal", None)
        self.signals.loadStartedSignal_parent = getattr(parentSignal, "loadStartedSignal", None)
        self.signals.msgSignal = getattr(parentSignal, "statusSignal", None)
        
        self.loaderUI = Ui_loadingUI()
        self.loaderUI.setupUi(self)
        self.loaderUI.progressBar.setMaximum(10000)     # 100 (default max value) * 10^precision
        
    def loadFile(self, stdPaths: list[list[str]]):
        # __dict__ because QObject also has a thread() method
        _running_thread = self.__dict__.get("thread")
        if _running_thread is not None and _running_thread.isRunning():
            return
        # clear the previous file UI before reading anything from the new file
        if self.signals.loadStartedSignal_parent is not None:
            self.signals.loadStartedSignal_parent.emit()
        self.closeEventByThread = False    # init at new file
        self.loaderUI.progressBar.setFormat("0.00%%")
        self.loaderUI.progressBar.setValue(0)
        # read headers first so the window can show something immediately
        self.sendEarlyMetadata(stdPaths)
        self.closeEventByThread = False    # init at new file
        self.loaderUI.progressBar.setFormat("0.00%%")
        self.loaderUI.progressBar.setValue(0)
        # create new thread and move stdReader to the new thread
        self.thread = QtCore.QThread(parent=self)
        self.reader = stdReader(self.signals)
        self.reader.readThis(stdPaths)
        
        # read test item identifier from setting
        setting = getSetting()
        if setting.gen.id_type in TestIDTypeDict:
            self.reader.setIDType(TestIDTypeDict[setting.gen.id_type])
        
        # self.reader.readBegin()
        self.reader.moveToThread(self.thread)
        self.thread.started.connect(self.reader.readBegin)
        self.thread.start()
        # the dialog is not shown; progress is rendered in the status bar
    
    def sendEarlyMetadata(self, stdPaths: list[list[str]]):
        """Read the header of every file group and emit it immediately.

        One entry per group, like `DatabaseFetcher.file_paths`, so the early
        File Info shows the same file list as the finished database (groups of
        several files are numbered `#1 → ...` by the shared builder).
        """
        groups = []
        for group in stdPaths:
            if not group:
                continue
            paths = list(group)
            # every file of the group, not just the first: the row lists them all
            names = [os.path.basename(f) for f in paths]
            sizes = []
            for f in paths:
                try:
                    sizes.append(get_file_size(f))
                except OSError:
                    sizes.append("")
            groups.append({"path": paths[0], "name": names[0],
                           "paths": paths, "names": names, "sizes": sizes,
                           "meta": read_group_headers(paths)})
        payload = {"groups": groups, "num_files": sum(len(g) for g in stdPaths)}
        try:
            if self.signals.metadataSignal_parent is not None:
                self.signals.metadataSignal_parent.emit(payload)
        except Exception:
            logger.exception("cannot emit early metadata")

    def closeEvent(self, event):
        if self.closeEventByThread:
            # close by thread
            event.accept()
        else:
            # close by clicking X
            close = QtWidgets.QMessageBox.question(self, "QUIT", "Are you sure want to stop reading?", 
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if close == QtWidgets.QMessageBox.Yes:
                # if user clicked yes, change thread flag and close window
                self.reader.flag.stop = True
                # self.thread.quit()
                # self.thread.wait()
                # event.accept()
            # else:
            # lesson learned: do not enable the code above, as it would nullify the sender in the thread, 
            # causing the slot is not invoked
            # we should simply ingnore the close event, let the thread finish its job and send close signal.
            event.ignore()

    @Slot(int)
    def updateProgressBar(self, num):
        if num == 10000:
            self.loaderUI.progressBar.setFormat("Loading database...")
            self.loaderUI.progressBar.setValue(num)
        else:
            # e.g. num is 1234, num/100 is 12.34, the latter is the orignal number
            self.loaderUI.progressBar.setFormat("%.02f%%" % (num/100))
            self.loaderUI.progressBar.setValue(num)
        
    @Slot(object)
    def sendDataInterface(self, di: object):
        # send `DataInterface` from reader to mainUI
        self.signals.dataInterfaceSignal_parent.emit(di)
    
    @Slot(bool)
    def closeLoader(self, closeUI):
        self.closeEventByThread = closeUI
        if closeUI:
            self.thread.quit()
            self.thread.wait()
            self.reader = None
            self.close()
        
        
        
class stdReader(QtCore.QObject):
    def __init__(self, QSignal:signal4Loader):
        super().__init__()
        if (QSignal is None or
            QSignal.dataInterfaceSignal_reader is None or
            QSignal.msgSignal is None):
            raise ValueError("Qsignal is invalid, parse is terminated")
        
        self.QSignals = QSignal
        self.progressBarSignal = self.QSignals.progressBarSignal
        self.statsSignal = self.QSignals.statsSignal
        self.closeSignal = self.QSignals.closeSignal
        self.dataInterfaceSignal = self.QSignals.dataInterfaceSignal_reader
        self.msgSignal = self.QSignals.msgSignal
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
            if self.msgSignal: self.msgSignal.emit("Loading STD file...", False, False, False)
            start = time.time()
            # auto generate a database name
            databasePath = os.path.join(sys.rootFolder, "logs", f"{uuid.uuid4().hex}.db")
            rust_stdf_helper.generate_database(databasePath, self.stdPaths, self.idType, self.progressBarSignal, self.flag, self.statsSignal)
            end = time.time()
            if self.flag.stop:
                # user terminated...
                sendDI = False
                finalMsg = "Loading cancelled by user"
            else:
                # send Data_interface object
                # sqlite cannot be used between thread
                # thus we need to store the db path and
                # load database in the main thread
                di.dbPath = databasePath
                finalMsg = f"Load completed, process time {end - start :.3f} sec"
                
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
        if self.msgSignal: self.msgSignal.emit(finalMsg, False, showWarning, False)
        self.closeSignal.emit(True)     # close loaderUI
        

