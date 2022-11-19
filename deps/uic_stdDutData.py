#
# uic_stdDutData.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 20th 2020
# -----
# Last Modified: Sun Nov 20 2022
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



import subprocess, os, platform
from .customizedQtClass import (StyleDelegateForTable_List, 
                                FlippedProxyModel, 
                                NormalProxyModel, 
                                TestDataTableModel)
# pyqt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QFileDialog, QPushButton
from PyQt5.QtCore import pyqtSignal as Signal, QTranslator, Qt
from .ui.stdfViewer_loadingUI import Ui_loadingUI
from .ui.stdfViewer_dutDataUI import Ui_dutData
# pyside2
# from PySide2 import QtCore, QtWidgets, QtGui
# from PySide2.QtWidgets import QAbstractItemView, QApplication, QFileDialog
# from PySide2.QtCore import Signal, QTranslator
# from .ui.stdfViewer_loadingUI_side2 import Ui_loadingUI
# from .ui.stdfViewer_dutDataUI_side2 import Ui_dutData
# pyside6
# from PySide6 import QtCore, QtWidgets, QtGui
# from PySide6.QtWidgets import QAbstractItemView, QApplication, QFileDialog
# from PySide6.QtCore import Signal, QTranslator
# from .ui.stdfViewer_loadingUI_side6 import Ui_loadingUI
# from .ui.stdfViewer_dutDataUI_side6 import Ui_dutData


        
class DutDataDisplayer(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.UI = Ui_dutData()
        self.UI.setupUi(self)
        self.translator = QTranslator(self)
        self.sd = StyleDelegateForTable_List(self)
        self.textFont = QtGui.QFont()
        self.floatFormat = "%f"
        
        self.transposeBtn = QPushButton("T")
        self.transposeBtn.setFixedSize(QtCore.QSize(25, 25))
        self.transposeBtn.setShortcut("t")
        self.UI.horizontalLayout.insertWidget(0, self.transposeBtn)
        self.transposeBtn.clicked.connect(self.onTransposeTable)
        
        self.UI.save.clicked.connect(self.onSave_csv)
        self.UI.save_xlsx.clicked.connect(self.onSave_xlsx)
        self.UI.close.clicked.connect(self.close)
        self.init_Table()
        
        
    def setTextFont(self, font: QtGui.QFont):
        self.textFont = font
        
        
    def setFloatFormat(self, floatFormat: str):
        self.floatFormat = floatFormat
        
        
    def setContent(self, content: dict):
        '''
        see StdfFile.py -> DataInterface -> getDutSummaryWithTestDataCore
        for details of `content`
        '''
        self.tmodel.setTestData(content["Data"])
        self.tmodel.setTestInfo(content["TestInfo"])
        self.tmodel.setDutIndexMap(content["dut2ind"])
        self.tmodel.setDutInfoMap(content["dutInfo"])
        self.tmodel.setTestLists(content["TestLists"])
        self.tmodel.setHHeaderBase([self.tr("File ID"), self.tr("Part ID"), self.tr("Test Head - Site"), 
                                    self.tr("Tests Executed"), self.tr("Test Time"), self.tr("Hardware Bin"), 
                                    self.tr("Software Bin"), self.tr("Wafer ID"), self.tr("(X, Y)"), self.tr("DUT Flag")])
        self.tmodel.setVHeaderBase([self.tr("Test Number"), self.tr("HLimit"), self.tr("LLimit"), self.tr("Unit")])
        self.tmodel.setVHeaderExt(content["VHeader"])
        self.tmodel.setFont(self.textFont)
        self.tmodel.setFloatFormat(self.floatFormat)
        # emit signal to show data
        self.tmodel.layoutChanged.emit()
        
    
    def showUI(self):
        self.exec_()
        
        
    def init_Table(self):
        self.tmodel = TestDataTableModel()
        # proxy model for normal display & transpose
        # self.flipModel = FlippedProxyModel()
        # self.normalModel = NormalProxyModel()
        # self.flipModel.setSourceModel(self.tmodel)
        # self.normalModel.setSourceModel(self.tmodel)
        # use normal model as default
        # self.activeModel = self.normalModel
        self.UI.tableView_dutData.setModel(self.tmodel)
        self.UI.tableView_dutData.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.UI.tableView_dutData.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)    
        self.sd.setParent(self.UI.tableView_dutData)
        self.UI.tableView_dutData.setItemDelegate(self.sd)    

        
    def onTransposeTable(self):
        if self.activeModel == self.normalModel:
            self.activeModel = self.flipModel
        else:
            self.activeModel = self.normalModel
        self.activeModel.layoutAboutToBeChanged.emit()
        self.UI.tableView_dutData.setModel(self.activeModel)
        self.activeModel.layoutChanged.emit()
    
    
    def onSave_csv(self):
        outPath, _ = QFileDialog.getSaveFileName(None, caption=self.tr("Save Report As"), filter=self.tr("CSV file (*.csv)"))
        checkComma = lambda text: '"' + text + '"' if "," in text else text
        if outPath:
            rowTotal = self.activeModel.rowCount()
            columnTotal = self.activeModel.columnCount()
            # if comma is in the string, needs to close with ""
            hh = [checkComma(self.activeModel.headerData(i, Qt.Horizontal, Qt.DisplayRole)) for i in range(columnTotal)]
            vh = [checkComma(self.activeModel.headerData(i, Qt.Vertical, Qt.DisplayRole)) for i in range(rowTotal)]
            with open(outPath, "w") as f:
                f.write(",".join([""] + hh)+"\n")
                for row in range(rowTotal):
                    rowDataList = [checkComma(self.activeModel.data(self.activeModel.index(row, col), Qt.DisplayRole)) for col in range(columnTotal)]
                    f.write(",".join([vh[row]] + rowDataList)+"\n")
            msgbox = QtWidgets.QMessageBox(None)
            msgbox.setText(self.tr("Completed"))
            msgbox.setInformativeText(self.tr("File is saved in %s") % outPath)
            revealBtn = msgbox.addButton(self.tr(" Reveal in folder "), QtWidgets.QMessageBox.ApplyRole)
            openBtn = msgbox.addButton(self.tr("Open..."), QtWidgets.QMessageBox.ActionRole)
            okBtn = msgbox.addButton(self.tr("OK"), QtWidgets.QMessageBox.YesRole)
            msgbox.setDefaultButton(okBtn)
            msgbox.exec_()
            if msgbox.clickedButton() == revealBtn:
                self.revealFile(outPath)
            elif msgbox.clickedButton() == openBtn:
                self.openFileInOS(outPath)
            
    
    def onSave_xlsx(self):
        outPath, _ = QFileDialog.getSaveFileName(None, caption=self.tr("Save Report As"), filter=self.tr("Excel file (*.xlsx)"))
        
        if outPath:
            def write_row(sheet, row, scol, dataL, styleList):
                # write as number in default, otherwise as string
                for i in range(len(dataL)):
                    try:
                        sheet.write_number(row, scol+i, float(dataL[i]), styleList[i])
                    except (TypeError, ValueError):
                        sheet.write_string(row, scol+i, dataL[i], styleList[i])
            
            import xlsxwriter as xw
            with xw.Workbook(outPath) as wb:
                noStyle = wb.add_format({"align": "center"})
                failStyle = wb.add_format({"bg_color": "#CC0000", "bold": True, "align": "center"})
                sheetOBJ = wb.add_worksheet(self.tr("DUT Data"))
                
                rowTotal = self.activeModel.rowCount()
                columnTotal = self.activeModel.columnCount()
                colHeader = [""] + [self.activeModel.headerData(i, Qt.Horizontal, Qt.DisplayRole) for i in range(columnTotal)]
                vh = [self.activeModel.headerData(i, Qt.Vertical, Qt.DisplayRole) for i in range(rowTotal)]
                
                write_row(sheetOBJ, 0, 0, colHeader, [noStyle] * (columnTotal + 1))
                col_width = [len(s) for s in colHeader]     # get max string len to adjust cell width
                
                for row in range(rowTotal):
                    rowDataList = [vh[row]]     # row header
                    rowStyleList = [noStyle]    # no style for row header
                    if len(vh[row]) > col_width[0]: col_width[0] = len(vh[row])
                    
                    for col in range(columnTotal):
                        qitem = self.activeModel.item(row, col)
                        data = qitem.text()
                        color = qitem.background().color().name().lower()
                        rowDataList.append(data)
                        rowStyleList.append(failStyle if color=="#cc0000" else noStyle)
                        if len(data) > col_width[col+1]: col_width[col+1] = len(data)
                    write_row(sheetOBJ, row + 1, 0, rowDataList, rowStyleList)
                [sheetOBJ.set_column(col, col, strLen * 1.1) for col, strLen in enumerate(col_width)]
                
            msgbox = QtWidgets.QMessageBox(None)
            msgbox.setText(self.tr("Completed"))
            msgbox.setInformativeText(self.tr("File is saved in %s") % outPath)
            revealBtn = msgbox.addButton(self.tr(" Reveal in folder "), QtWidgets.QMessageBox.ApplyRole)
            openBtn = msgbox.addButton(self.tr("Open..."), QtWidgets.QMessageBox.ActionRole)
            okBtn = msgbox.addButton(self.tr("OK"), QtWidgets.QMessageBox.YesRole)
            msgbox.setDefaultButton(okBtn)
            msgbox.exec_()
            if msgbox.clickedButton() == revealBtn:
                self.revealFile(outPath)
            elif msgbox.clickedButton() == openBtn:
                self.openFileInOS(outPath)
            
    
    def openFileInOS(self, filepath):
        # https://stackoverflow.com/a/435669
        filepath = os.path.normpath(filepath)
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', filepath))
        elif platform.system() == 'Windows':    # Windows
            subprocess.call(f'cmd /c start "" "{filepath}"', creationflags = \
                subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
        else:                                   # linux variants
            subprocess.call(('xdg-open', filepath))        
            

    def revealFile(self, filepath):
        filepath = os.path.normpath(filepath)
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', '-R', filepath))
        elif platform.system() == 'Windows':    # Windows
            subprocess.call(f'explorer /select,"{filepath}"', creationflags = \
                subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
        else:                                   # linux variants
            subprocess.call(('xdg-open', os.path.dirname(filepath)))

    
    
