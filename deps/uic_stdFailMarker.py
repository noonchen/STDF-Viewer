#
# uic_stdFailMarker.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Sun Dec 13 2020
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
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from deps.ui.stdfViewer_loadingUI import Ui_loadingUI
# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtWidgets import QApplication
# from deps.ui.stdfViewer_loadingUI_side import Ui_loadingUI
# from PySide2.QtCore import Signal, Slot



class FailMarker(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        self.UI = Ui_loadingUI()
        self.UI.setupUi(self)
        self.parent = parent
                
        self.setWindowTitle("Searching Failed Items")
        self.UI.progressBar.setFormat("%p%")
        self.stopFlag = False
        
        self.show()
        self.start()
        self.close()
    
    def start(self):
        start_time = time.time()
        
        self.sim = self.parent.sim_list
        self.total = self.sim.rowCount()
        failCount = 0
        
        for i in range(self.total):
            if self.stopFlag: 
                end_time = time.time()
                self.parent.signals.statusSignal.emit("Fail Marker aborted, time elapsed %.2f sec."%(end_time - start_time))
                return
            
            self.updateProgressBar(int(100 * (i+1) / self.total))
            QApplication.processEvents()    # force refresh UI to update progress bar
            
            qitem = self.sim.item(i)
            test_num = int(qitem.text().split("\t")[0])
            
            isFail = self.parent.isTestFail(test_num, -1)
            if isFail: 
                failCount += 1
                qitem.setData(QtGui.QColor(QtGui.QColor(255, 255, 255)), QtCore.Qt.ForegroundRole)
                qitem.setData(QtGui.QColor(QtGui.QColor(204, 0, 0)), QtCore.Qt.BackgroundRole)
            
        end_time = time.time()
        msg = "No failed test item found" if failCount == 0 else "%d failed test items found"%failCount
        self.parent.signals.statusSignal.emit("%s, time elapsed %.2f sec."%(msg, end_time - start_time))

    
        
    def closeEvent(self, event):
        # close by clicking X
        self.stopFlag = True
        event.accept()
             
                    
    def updateProgressBar(self, num):
        self.UI.progressBar.setValue(num)
      
        
        
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication([])
    path1 = "Test path"
    test = FailMarker()
    sys.exit(app.exec_())
    
    
