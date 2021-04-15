#
# uic_stdLoader.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Thu Apr 15 2021
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



import time, os, logging
# pyqt5
# from PyQt5 import QtCore, QtWidgets
# from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
# from .ui.stdfViewer_loadingUI import Ui_loadingUI
# pyside2
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Signal, Slot
from deps.ui.stdfViewer_loadingUI_side2 import Ui_loadingUI
# pyside6
# from PySide6 import QtCore, QtWidgets
# from PySide6.QtCore import Signal, Slot
# from deps.ui.stdfViewer_loadingUI_side6 import Ui_loadingUI

from .stdfOffsetRetriever import stdfDataRetriever
# from . import stdfOffsetRetriever_test

from .stdfData import stdfData
from .pystdf.Types import InitialSequenceException

logger = logging.getLogger("STDF Viewer")

class flags:
    stop = False


class signal4Loader(QtCore.QObject):
     # get data from reader
    dataTransSignal = Signal(stdfData)
    # get progress from reader
    progressBarSignal = Signal(int)
    # get close signal
    closeSignal = Signal(bool)
    
    # data transfer signal from parent
    dataTransToParent = None
    # status bar signal from parent
    msgSignal = None



class stdfLoader(QtWidgets.QDialog):
    
    def __init__(self, stdHandle, parentSignal = None, parent = None):
        super().__init__(parent)
        self.closeEventByThread = False    # used to determine the source of close event
        self.std = stdHandle
        
        self.signals = signal4Loader()
        self.signals.dataTransSignal.connect(self.getStdfData)
        self.signals.progressBarSignal.connect(self.updateProgressBar)
        self.signals.closeSignal.connect(self.closeLoader)
        
        self.signals.dataTransToParent = getattr(parentSignal, "dataSignal", None)
        self.signals.msgSignal = getattr(parentSignal, "statusSignal", None)
        
        self.loaderUI = Ui_loadingUI()
        self.loaderUI.setupUi(self)
        self.loaderUI.progressBar.setMaximum(10000)     # 100 (default max value) * 10^precision
        # create new thread and move stdReader to the new thread
        self.thread = QtCore.QThread(parent=self)
        self.reader = stdReader(self.signals)
        self.reader.readThis(self.std)
        
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
        # e.g. num is 1234, num/100 is 12.34, the latter is the orignal number
        self.loaderUI.progressBar.setFormat("%.02f%%" % (num/100))
        self.loaderUI.progressBar.setValue(num)
        
    @Slot(stdfData)
    def getStdfData(self, sdata):
        if self.signals.dataTransToParent: self.signals.dataTransToParent.emit(sdata)
        
    @Slot(bool)
    def closeLoader(self, closeUI):
        self.closeEventByThread = closeUI
        if closeUI:
            self.thread.quit()
            self.thread.wait()
            self.reader = None
            self.close()
                 
        
        
class stdReader(QtCore.QObject):
    def __init__(self, QSignal):
        super().__init__()
        self.sData = stdfData()
        self.QSignals = QSignal
        self.dataTransSignal = self.QSignals.dataTransSignal
        self.progressBarSignal = self.QSignals.progressBarSignal
        self.closeSignal = self.QSignals.closeSignal
        self.msgSignal = self.QSignals.msgSignal
        self.flag = flags()     # used for stopping parser
        
    def readThis(self, stdHandle):
        self.std = stdHandle
        
    @Slot()
    def readBegin(self):
        try:
            if self.msgSignal: self.msgSignal.emit("Loading STD file...", False, False, False)
            start = time.time()
            self.retriver = stdfDataRetriever(self.std, QSignal=self.progressBarSignal, flag=self.flag)
            # self.retriver = stdfOffsetRetriever_test.stdfDataRetriever(self.std, QSignal=self.progressBarSignal, flag=self.flag)
            self.sData = self.retriver.getStdfData()
            end = time.time()
            # print(end - start)
            if self.flag.stop:
                self.sData.testData = {}   # empty its data in order to force fail the content check
                if self.msgSignal: self.msgSignal.emit("Loading cancelled by user", False, False, False)
            else:
                if self.msgSignal: self.msgSignal.emit("Load completed, process time %.3f sec"%(end - start), False, False, False)
                
        except InitialSequenceException:
            if self.msgSignal: self.msgSignal.emit("It is not a standard STDF V4 file.\n\nPath:\n%s" % (os.path.realpath(self.std.name)), False, True, False)
        except Exception:
            logger.exception("Error occurred when parsing the file")
            if self.msgSignal: self.msgSignal.emit("Error occurred when parsing the file", True, False, False)
        finally:
            self.dataTransSignal.emit(self.sData)
            self.closeSignal.emit(True)     # close loaderUI
        

    
    
