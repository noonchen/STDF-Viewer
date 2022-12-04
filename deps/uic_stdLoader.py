#
# uic_stdLoader.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Thu Dec 01 2022
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


logger = logging.getLogger("STDF Viewer")

class flags:
    stop = False


class signal4Loader(QtCore.QObject):
    # get progress from reader
    progressBarSignal = Signal(int)
    # get `DataInterface` from reader
    dataInterfaceSignal_reader = Signal(object)
    # get close signal
    closeSignal = Signal(bool)
    
    # object signal from parent
    dataInterfaceSignal_parent = None
    # status bar signal from parent
    msgSignal = None



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
        self.signals.msgSignal = getattr(parentSignal, "statusSignal", None)
        
        self.loaderUI = Ui_loadingUI()
        self.loaderUI.setupUi(self)
        self.loaderUI.progressBar.setMaximum(10000)     # 100 (default max value) * 10^precision
        
    def loadFile(self, stdPaths: list[list[str]]):
        self.closeEventByThread = False    # init at new file
        self.loaderUI.progressBar.setFormat("0.00%%")
        self.loaderUI.progressBar.setValue(0)
        # create new thread and move stdReader to the new thread
        self.thread = QtCore.QThread(parent=self)
        self.reader = stdReader(self.signals)
        self.reader.readThis(stdPaths)
        
        # self.reader.readBegin()
        self.reader.moveToThread(self.thread)
        self.thread.started.connect(self.reader.readBegin)
        self.thread.start()
        # blocking parent if it's not finished
        self.exec_()
    
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
        self.closeSignal = self.QSignals.closeSignal
        self.dataInterfaceSignal = self.QSignals.dataInterfaceSignal_reader
        self.msgSignal = self.QSignals.msgSignal
        self.flag = flags()     # used for stopping parser
        
    def readThis(self, stdPaths: list[list[str]]):
        self.stdPaths = stdPaths
        
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
            rust_stdf_helper.generate_database(databasePath, self.stdPaths, self.progressBarSignal, self.flag)
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
        

