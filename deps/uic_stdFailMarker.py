#
# uic_stdFailMarker.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Fri Nov 25 2022
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
from PyQt5.QtWidgets import QApplication
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
    def __init__(self, parent):
        super().__init__()
        self.UI = Ui_loadingUI()
        self.UI.setupUi(self)
        self._parent = parent
        self.translator = QtCore.QTranslator(self)
                
        self.setWindowTitle(self.tr("Searching Failed Items"))
    
    def start(self):
        self.UI.progressBar.setFormat("%p%")
        self.UI.progressBar.setValue(0)
        self.stopFlag = False   # init at start
        self.show()
        start_time = time.time()
        
        self.sim = self._parent.sim_list
        self.total = self.sim.rowCount()
        failCount = 0
        cpkFailCount = 0
        
        for i in range(self.total):
            if self.stopFlag: 
                end_time = time.time()
                self._parent.signals.statusSignal.emit(self.tr("Fail Marker aborted, time elapsed %.2f sec.") % (end_time - start_time), False, False, False)
                return
            
            self.updateProgressBar(int(100 * (i+1) / self.total))
            QApplication.processEvents()    # force refresh UI to update progress bar
            
            qitem = self.sim.item(i)
            status = self._parent.isTestFail(qitem.text())
            if status == "Fail":
                failCount += 1
                qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
            elif status == "cpkFail":
                cpkFailCount += 1
                qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
            
        end_time = time.time()
        msg = ""
        if failCount == 0 and cpkFailCount == 0:
            msg = self.tr("No failed test item found, ")
        else:
            if failCount != 0:
                msg += self.tr("%d failed test items found, ") % failCount
            if cpkFailCount != 0:
                msg += self.tr("%d passed test items found with low Cpk, ") % cpkFailCount
        self._parent.signals.statusSignal.emit(self.tr("%stime elapsed %.2f sec.") % (msg, end_time - start_time), False, False, False)
        self.close()
        
    def closeEvent(self, event):
        # close by clicking X
        self.stopFlag = True
        event.accept()
             
    def updateProgressBar(self, num):
        self.UI.progressBar.setValue(num)
      
    
