#
# uic_stdFailMarker.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Sun Sep 20 2026
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
from PyQt5 import QtCore, QtWidgets, QtGui
from .ui.stdfViewer_loadingUI import Ui_loadingUI
# pyside2
# from PySide2 import QtCore, QtWidgets, QtGui
# from PySide2.QtWidgets import QApplication
# from .ui.stdfViewer_loadingUI_side2 import Ui_loadingUI
# pyside6
# from PySide6 import QtCore, QtWidgets, QtGui
# from PySide6.QtWidgets import QApplication
# from .ui.stdfViewer_loadingUI_side6 import Ui_loadingUI


class FailMarker(QtWidgets.QWidget):
    # Upper bound of scanning time per event-loop tick,
    # slicing the scan work keeps the window responsive.
    BATCH_TIMEOUT_SEC = 0.02

    def __init__(self, parent):
        super().__init__()
        self.UI = Ui_loadingUI()
        self.UI.setupUi(self)
        self._parent = parent
        self.translator = QtCore.QTranslator(self)

        self.scanTimer = QtCore.QTimer(self)
        self.scanTimer.setInterval(0)
        self.scanTimer.timeout.connect(self.processBatch)
        self.currentRow = 0
        self.total = 0
        self.start_time = 0.0
        self.failCount = 0
        self.cpkFailCount = 0
                
        self.setWindowTitle(self.tr("Searching Failed Items"))
    
    def start(self):
        self.UI.progressBar.setFormat("%p%")
        self.UI.progressBar.setValue(0)
        self.stopFlag = False   # init at start
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()
        self.start_time = time.time()
        
        self.sim = self._parent.sim_list
        self.total = self.sim.rowCount()
        self.failCount = 0
        self.cpkFailCount = 0
        self.currentRow = 0
        self.updateProgressBar(0)
        self.scanTimer.start()
    
    def processBatch(self):
        '''
        Colour one time-budgeted slice of the test list, then give the event
        loop back. Driven by `scanTimer` until the whole list is done.
        '''
        if self.stopFlag:
            self.scanTimer.stop()
            self.reportResult(aborted=True)
            return
        
        deadline = time.time() + self.BATCH_TIMEOUT_SEC
        row = self.currentRow
        while row < self.total and time.time() < deadline:
            qitem = self.sim.item(row)
            status = self._parent.isTestFail(qitem.text())
            if status == "Fail":
                self.failCount += 1
                qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
            elif status == "cpkFail":
                self.cpkFailCount += 1
                qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
            row += 1
        self.currentRow = row
        
        self.updateProgressBar(int(100 * self.currentRow / self.total) if self.total else 100)
        if self.currentRow >= self.total:
            self.scanTimer.stop()
            self.reportResult()
    
    def reportResult(self, aborted: bool = False):
        '''emit the final status message, and close when the scan completed'''
        elapsed = time.time() - self.start_time
        if aborted:
            self._parent.signals.statusSignal.emit(self.tr("Fail Marker aborted, time elapsed %.2f sec.") % elapsed, False, False, False)
            return
        msg = ""
        if self.failCount == 0 and self.cpkFailCount == 0:
            msg = self.tr("No failed test item found, ")
        else:
            if self.failCount != 0:
                msg += self.tr("%d failed test items found, ") % self.failCount
            if self.cpkFailCount != 0:
                msg += self.tr("%d passed test items found with low Cpk, ") % self.cpkFailCount
        self._parent.signals.statusSignal.emit(self.tr("%stime elapsed %.2f sec.") % (msg, elapsed), False, False, False)
        self.close()
        
    def closeEvent(self, event):
        # close by clicking X: stop the running scan and report the abort
        if self.scanTimer.isActive():
            self.stopFlag = True
            self.scanTimer.stop()
            self.reportResult(aborted=True)
        event.accept()
              
    def updateProgressBar(self, num):
        self.UI.progressBar.setValue(num)
      
    
