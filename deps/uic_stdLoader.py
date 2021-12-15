#
# uic_stdLoader.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Wed Dec 15 2021
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



import time, os, sys, logging
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

from .cystdf import stdfDataRetriever     # cython version


logger = logging.getLogger("STDF Viewer")

class flags:
    stop = False


class signal4Loader(QtCore.QObject):
    # get progress from reader
    progressBarSignal = Signal(int)
    # get parse status from reader
    parseStatusSignal_reader = Signal(bool)
    # get close signal
    closeSignal = Signal(bool)
    
    # parse status signal from parent
    parseStatusSignal_parent = None
    # status bar signal from parent
    msgSignal = None



class stdfLoader(QtWidgets.QDialog):
    
    def __init__(self, parentSignal = None, parent = None):
        super().__init__(parent)
        self.translator = QTranslator(self)
        self.closeEventByThread = False    # used to determine the source of close event
        
        self.signals = signal4Loader()
        self.signals.progressBarSignal.connect(self.updateProgressBar)
        self.signals.parseStatusSignal_reader.connect(self.sendParseSignal)
        self.signals.closeSignal.connect(self.closeLoader)
        
        self.signals.parseStatusSignal_parent = getattr(parentSignal, "parseStatusSignal", None)
        self.signals.msgSignal = getattr(parentSignal, "statusSignal", None)
        
        self.loaderUI = Ui_loadingUI()
        self.loaderUI.setupUi(self)
        self.loaderUI.progressBar.setMaximum(10000)     # 100 (default max value) * 10^precision
        
    def loadFile(self, stdPath):
        self.closeEventByThread = False    # init at new file
        # create new thread and move stdReader to the new thread
        self.thread = QtCore.QThread(parent=self)
        self.reader = stdReader(self.signals)
        self.reader.readThis(stdPath)
        
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
            close = QtWidgets.QMessageBox.question(self, "QUIT", "Are you sure want to stop reading?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if close == QtWidgets.QMessageBox.Yes:
                # if user clicked yes, change thread flag and close window
                self.reader.flag.stop = True
                # self.thread.quit()
                # self.thread.wait()
                # event.accept()
            # else:
            """
            lesson learned: do not enable the code above, as it would nullify the sender in the thread, causing the slot is not invoked
            we should simply ingnore the close event, let the thread finish its job and send close signal.
            """
            event.ignore()

    @Slot(int)
    def updateProgressBar(self, num):
        if num == 10000:
            self.loaderUI.progressBar.setFormat("Updating GUI...")
            self.loaderUI.progressBar.setValue(num)
        else:
            # e.g. num is 1234, num/100 is 12.34, the latter is the orignal number
            self.loaderUI.progressBar.setFormat("%.02f%%" % (num/100))
            self.loaderUI.progressBar.setValue(num)
        
    @Slot(bool)
    def sendParseSignal(self, parseStatus):
        # parse parse status from reader to mainUI
        self.signals.parseStatusSignal_parent.emit(parseStatus)
    
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
        self.parseStatus = True     # default success
        if (QSignal is None or
            QSignal.parseStatusSignal_reader is None or
            QSignal.msgSignal is None):
            raise ValueError("Qsignal is invalid, parse is terminated")
        
        self.QSignals = QSignal
        self.progressBarSignal = self.QSignals.progressBarSignal
        self.closeSignal = self.QSignals.closeSignal
        self.parseStatusSignal = self.QSignals.parseStatusSignal_reader
        self.msgSignal = self.QSignals.msgSignal
        self.flag = flags()     # used for stopping parser
        
    def readThis(self, stdPath):
        self.stdPath = stdPath
        
    @Slot()
    def readBegin(self):
        try:
            if self.msgSignal: self.msgSignal.emit("Loading STD file...", False, False, False)
            start = time.time()
            databasePath = os.path.join(sys.rootFolder, "logs", "tmp.db")
            stdfDataRetriever(filepath=self.stdPath, dbPath=databasePath, QSignal=self.progressBarSignal, flag=self.flag)
            end = time.time()
            print(end - start)
            if self.flag.stop:
                # user terminated
                self.parseStatus = False
                if self.msgSignal: self.msgSignal.emit("Loading cancelled by user", False, False, False)
            else:
                self.parseStatus = True
                if self.msgSignal: self.msgSignal.emit("Load completed, process time %.3f sec"%(end - start), False, False, False)
            self.parseStatusSignal.emit(self.parseStatus)
                
        except Exception as e:
            self.parseStatus = False
            self.parseStatusSignal.emit(self.parseStatus)
            logger.exception("\nError occurred when parsing the file")
            if self.msgSignal: self.msgSignal.emit(str(e), False, True, False)
            
        finally:
            # parse signal cannot be emitted in finally block
            # since it will execute before except block
            self.closeSignal.emit(True)     # close loaderUI
        

    
    
