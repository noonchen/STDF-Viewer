#
# uic_stdDutData.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 20th 2020
# -----
# Last Modified: Tue Feb 16 2021
# Modified By: noonchen
# -----
# Copyright (c) 2021 noonchen
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



# pyqt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QFileDialog
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from deps.ui.stdfViewer_loadingUI import Ui_loadingUI
from deps.ui.stdfViewer_dutDataUI import Ui_dutData
# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtWidgets import QApplication
# from deps.ui.stdfViewer_loadingUI_side import Ui_loadingUI
# from PySide2.QtCore import Signal, Slot



class signal(QtCore.QObject):
    hideSignal = Signal()
    
    

class DutDataReader(QtWidgets.QWidget):
    def __init__(self, parent, selectedDutIndex, styleDelegate):
        super().__init__()
        self.UI = Ui_loadingUI()
        self.UI.setupUi(self)
        self.parent = parent
        self.selectedDutIndex = selectedDutIndex      # selected indexes of dut info table
        self.sd = styleDelegate
                
        self.setWindowTitle("Reading DUT data")
        self.UI.progressBar.setFormat("%p%")
        self.stopFlag = False
        self.signal = signal()
        self.signal.hideSignal.connect(self.hide)
        
        self.show()
        self.start()
    
    
    def start(self):
        self.test_number_List = sorted([int(ele.split("\t")[0]) for ele in self.parent.completeTestList])
        self.total = len(self.test_number_List)
        dutInfo = self.parent.prepareDataForDUTSummary(siteList=[], selectedDutIndex=self.selectedDutIndex)
        dutData = []
        dutStat = []
        dutFlagInfo = []
        for i, test_num in enumerate(self.test_number_List):
            if self.stopFlag: return

            dutData_perTest, stat_perTest, flagInfo_perTest = self.parent.prepareDataForDUTSummary(siteList=[], selectedDutIndex=self.selectedDutIndex, test_num=test_num, exportTestFlag=True)
            dutData.append(dutData_perTest)
            dutStat.append(stat_perTest)
            dutFlagInfo.append(flagInfo_perTest)
            
            self.updateProgressBar(int(100 * (i+1) / self.total))
            QApplication.processEvents()    # force refresh UI to update progress bar
        self.UI.progressBar.setFormat("Filling table with data...")
        QApplication.processEvents()
        dutDataDisplayer(self, (dutInfo, dutData, dutStat, dutFlagInfo), self.sd, self.signal.hideSignal)
        self.close()
            
        
    def closeEvent(self, event):
        # close by clicking X
        self.stopFlag = True
        event.accept()
             
                    
    def updateProgressBar(self, num):
        self.UI.progressBar.setValue(num)
      
        
        
class dutDataDisplayer(QtWidgets.QDialog):
    def __init__(self, parent, content, styleDelegate, hideSignal):
        super().__init__()
        self.UI = Ui_dutData()
        self.UI.setupUi(self)
        self.parent = parent
        self.dutInfo, self.dutData, self.dutStat, self.dutFlagInfo = content
        self.sd = styleDelegate
        self.hideSignal = hideSignal
        
        self.UI.save.clicked.connect(self.onSave)
        self.UI.close.clicked.connect(self.close)
        self.init_Table()
        self.parent.parent.updateStatus("Please wait for data filling in the table...")
        self.refresh_Table()
        self.hideSignal.emit()
        self.parent.parent.updateStatus("")
        self.exec_()
        
        
    def init_Table(self):
        self.tmodel = QtGui.QStandardItemModel()
        self.UI.tableView_dutData.setModel(self.tmodel)
        self.UI.tableView_dutData.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.UI.tableView_dutData.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)    
        self.sd.setParent(self.UI.tableView_dutData)
        self.UI.tableView_dutData.setItemDelegate(self.sd)    


    def refresh_Table(self):
        # clear
        self.tmodel.removeColumns(0, self.tmodel.columnCount())
        self.tmodel.removeRows(0, self.tmodel.rowCount())
        # header
        self.hh = ["Part ID", "Test Site", "Tests Executed", "Test Time", "Hardware Bin", "Software Bin", "DUT Flag"] + [tmp[0] for tmp in self.dutData]
        vh_base = ["Test Number", "HiLimit", "LoLimit", "Unit"]
        self.vh = vh_base + ["#%d"%(i+1) for i in range(len(self.dutInfo))]
        vh_len = len(vh_base)

        # append value
        # get dut pass/fail list
        statIndex = self.hh.index("DUT Flag")
        dutStatus = [True] * vh_len + [dutInfo_perDUT[statIndex].split(" ", 1)[0] != "Failed" for dutInfo_perDUT in self.dutInfo]
        for col_tuple in zip(*self.dutInfo):
            tmpCol = ["N/A"] * vh_len + list(col_tuple)
            qitemCol = []
            for i, (item, flag) in enumerate(zip(tmpCol, dutStatus)):
                qitem = QtGui.QStandardItem(item)
                qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                if i < vh_len: qitem.setData(QtGui.QColor("#0F80FF7F"), QtCore.Qt.BackgroundRole)   # add bgcolor for non-data cell
                if not flag: 
                    qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                    qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                qitemCol.append(qitem)                        
            self.tmodel.appendColumn(qitemCol)
        
        for dataCol, statCol, flagInfoCol in zip(self.dutData, self.dutStat, self.dutFlagInfo):
            qitemCol = []
            for i, (item, stat, flagInfo) in enumerate(zip(dataCol, statCol, flagInfoCol)):    # remove 1st element: test name
                if i == 0: continue     # skip test name
                qitem = QtGui.QStandardItem(item)
                qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                if stat == False:
                    qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                    qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                if flagInfo != "":
                    qitem.setToolTip(flagInfo)
                if i <= vh_len: qitem.setData(QtGui.QColor("#0F80FF7F"), QtCore.Qt.BackgroundRole)
                qitemCol.append(qitem)                        
            self.tmodel.appendColumn(qitemCol)
        
        self.tmodel.setHorizontalHeaderLabels(self.hh)
        self.tmodel.setVerticalHeaderLabels(self.vh)
        self.UI.tableView_dutData.horizontalHeader().setVisible(True)
        self.UI.tableView_dutData.verticalHeader().setVisible(True)        
        # resize cells
        header = self.UI.tableView_dutData.horizontalHeader()
        for column in range(header.model().columnCount()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        
        
    def onSave(self):
        outPath, _ = QFileDialog.getSaveFileName(None, caption="Save Report As", filter="CSV file (*.csv)")
        if outPath:
            with open(outPath, "w") as f:
                f.write(",".join([""] + self.hh)+"\n")
                for row in range(self.tmodel.rowCount()):
                    rowDataList = [self.tmodel.data(self.tmodel.index(row, col)) for col in range(self.tmodel.columnCount())]
                    f.write(",".join([self.vh[row]] + rowDataList)+"\n")
            QtWidgets.QMessageBox.information(None, "Completed", "File is saved in %s"%outPath, QtWidgets.QMessageBox.Ok)
    
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication([])
    path1 = "Test path"
    test = dutDataDisplayer()
    sys.exit(app.exec_())
    
    
