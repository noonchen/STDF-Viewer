#
# uic_stdLoader.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Sun Dec 20 2020
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



import time
# pyqt5
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from deps.ui.stdfViewer_loadingUI import Ui_loadingUI
# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtCore import Signal, Slot
# from deps.ui.stdfViewer_loadingUI_side import Ui_loadingUI

from deps.stdfOffsetRetriever import stdfDataRetriever, stdfSummarizer


class flags:
    stop = False


class signal4Loader(QtCore.QObject):
     # get data from reader
    dataTransSignal = Signal(stdfSummarizer)
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
        self.summarizer = None
        
        self.signals = signal4Loader()
        self.signals.dataTransSignal.connect(self.getSummarizer)
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
                self.thread.quit()
                self.thread.wait()
                event.accept()
            else:
                event.ignore()

    @Slot(int)
    def updateProgressBar(self, num):
        # e.g. num is 1234, num/100 is 12.34, the latter is the orignal number
        self.loaderUI.progressBar.setFormat("%.02f%%" % (num/100))
        self.loaderUI.progressBar.setValue(num)
        
    @Slot(stdfSummarizer)
    def getSummarizer(self, smz):
        self.summarizer = smz
        if self.signals.dataTransToParent: self.signals.dataTransToParent.emit(self.summarizer)
        
    @Slot(bool)
    def closeLoader(self, closeUI):
        self.closeEventByThread = closeUI
        if closeUI:
            self.thread.quit()
            self.thread.wait()
            self.close()
                 
        
        
class stdReader(QtCore.QObject):
    def __init__(self, QSignal):
        super().__init__()
        self.summarizer = stdfSummarizer(None)
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
            if self.msgSignal: self.msgSignal.emit("Loading STD file...")
            start = time.time()
            self.summarizer = stdfDataRetriever(self.std, QSignal=self.progressBarSignal, flag=self.flag)()
            end = time.time()
            # print(end - start)
            if self.flag.stop:
                if self.msgSignal: self.msgSignal.emit("Loading cancelled by user")
            else:
                if self.msgSignal: self.msgSignal.emit("Load completed, process time %.3f sec"%(end - start))
                
        except Exception as e:
            if self.msgSignal: self.msgSignal.emit("Load Error: " + repr(e))
            pass
        
        finally:
            self.dataTransSignal.emit(self.summarizer)
            self.closeSignal.emit(True)     # close loaderUI
        
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication([])
    path1 = "Test Path"
    test = stdfLoader(path1)
    sys.exit(app.exec_())
    
    
