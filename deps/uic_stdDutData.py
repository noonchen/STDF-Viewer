#
# uic_stdDutData.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 20th 2020
# -----
# Last Modified: Mon Dec 05 2022
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



from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet
from .customizedQtClass import *
from .SharedSrc import *
# pyqt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QAbstractItemView, QFileDialog, QPushButton
from PyQt5.QtCore import QTranslator, Qt
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
        self.textFont = QtGui.QFont()
        self.floatFormat = "%f"
        
        self.sd = StyleDelegateForTable_List(self.UI.tableView_dutData)
        self.UI.tableView_dutData.setItemDelegate(self.sd)
        
        self.transposeBtn = QPushButton("T")
        self.transposeBtn.setFixedSize(QtCore.QSize(25, 25))
        self.transposeBtn.setShortcut("t")
        self.transposeBtn.setStyleSheet("QPushButton { background-color: #FE7B00; }")
        self.transposeBtn.setToolTip(self.tr("Transpose table"))
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
        self.flipModel = FlippedProxyModel()
        self.normalModel = NormalProxyModel()
        self.flipModel.setSourceModel(self.tmodel)
        self.normalModel.setSourceModel(self.tmodel)
        # use normal model as default
        self.activeModel = self.normalModel
        self.UI.tableView_dutData.setModel(self.tmodel)
        self.UI.tableView_dutData.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.UI.tableView_dutData.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        
    def onTransposeTable(self):
        if self.activeModel is self.normalModel:
            self.activeModel = self.flipModel
        else:
            self.activeModel = self.normalModel
        self.activeModel.layoutAboutToBeChanged.emit()
        self.UI.tableView_dutData.setModel(self.activeModel)
        self.activeModel.layoutChanged.emit()
    
    
    def onSave_csv(self):
        def checkComma(text: str) -> str:
            # if comma is in the string, needs to close with ""
            if isinstance(text, str):
                if "," in text:
                    return f'"{text}"'
                else:
                    return text
            else:
                if text is None:
                    return ""
                else:
                    return f"{text}"
        
        outPath, _ = QFileDialog.getSaveFileName(None, caption=self.tr("Save Report As"), filter=self.tr("CSV file (*.csv)"))
        if outPath:
            rowTotal = self.activeModel.rowCount()
            columnTotal = self.activeModel.columnCount()
            hh = [checkComma(self.activeModel.headerData(i, 
                                                         Qt.Orientation.Horizontal, 
                                                         Qt.ItemDataRole.DisplayRole)) 
                  for i in range(columnTotal)]
            vh = [checkComma(self.activeModel.headerData(i, 
                                                         Qt.Orientation.Vertical, 
                                                         Qt.ItemDataRole.DisplayRole)) 
                  for i in range(rowTotal)]
            
            with open(outPath, "w") as f:
                f.write(",".join([""] + hh)+"\n")
                for row in range(rowTotal):
                    rowDataList = [checkComma(self.activeModel.data(self.activeModel.index(row, col), 
                                                                    Qt.ItemDataRole.DisplayRole)) for col in range(columnTotal)]
                    f.write(",".join([vh[row]] + rowDataList)+"\n")
            
            showCompleteMessage(self.tr, outPath)
            
    
    def onSave_xlsx(self):
        outPath, _ = QFileDialog.getSaveFileName(None, caption=self.tr("Save Report As"), filter=self.tr("Excel file (*.xlsx)"))
        
        if outPath:
            def write_row(sheet: Worksheet, row: int, scol: int, dataL: list, styleList: list):
                # write as number in default, otherwise as string
                for i, (data, style) in enumerate(zip(dataL, styleList)):
                    try:
                        sheet.write_number(row, scol+i, float(data), style)
                    except (TypeError, ValueError):
                        sheet.write_string(row, scol+i, data, style)
            
            with Workbook(outPath) as wb:
                noStyle = wb.add_format({"align": "center"})
                boldStyle = wb.add_format({"bold": True, "align": "center"})
                failStyle = wb.add_format({"font_color": "FFFFFF", "bg_color": "#CC0000", "bold": True, "align": "center"})
                supersedeStyle = wb.add_format({"bg_color": "#D0D0D0", "bold": True, "align": "center"})
                unknownStyle = wb.add_format({"bg_color": "#FE7B00", "bold": True, "align": "center"})
                sheetOBJ = wb.add_worksheet(self.tr("DUT Data"))
                
                rowTotal = self.activeModel.rowCount()
                columnTotal = self.activeModel.columnCount()
                colHeader = [""] + [self.activeModel.headerData(i, 
                                                                Qt.Orientation.Horizontal, 
                                                                Qt.ItemDataRole.DisplayRole) 
                                    for i in range(columnTotal)]
                vh = [self.activeModel.headerData(i, 
                                                  Qt.Orientation.Vertical, 
                                                  Qt.ItemDataRole.DisplayRole) 
                      for i in range(rowTotal)]
                write_row(sheetOBJ, 0, 0, colHeader, [boldStyle] * (columnTotal + 1))
                col_width = [len(s) for s in colHeader]     # get max string len to adjust cell width
                
                for row in range(rowTotal):
                    # row header
                    rowDataList = [vh[row]]
                    rowStyleList = [boldStyle]
                    col_width[0] = max(len(vh[row]), col_width[0])
                    
                    for col in range(columnTotal):
                        modelIndex = self.activeModel.index(row, col)
                        data = self.activeModel.data(modelIndex, 
                                                     Qt.ItemDataRole.DisplayRole)
                        bgcolor = self.activeModel.data(modelIndex, 
                                                        Qt.ItemDataRole.BackgroundRole)
                        # replace None with empty string
                        data = data if data is not None else ""
                        # choose cell style by background color
                        if isinstance(bgcolor, QtGui.QColor):
                            hexcolor = bgcolor.name().lower()
                            if hexcolor.startswith("#cc0000"):
                                cellStyle = failStyle
                            elif hexcolor.startswith("#d0d0d0"):
                                cellStyle = supersedeStyle
                            elif hexcolor.startswith("#fe7b00"):
                                cellStyle = unknownStyle
                            else:
                                cellStyle = noStyle
                        else:
                            cellStyle = noStyle
                        
                        rowDataList.append(data)
                        rowStyleList.append(cellStyle)
                        col_width[col + 1] = max(len(str(data)), col_width[col + 1])
                    write_row(sheetOBJ, row + 1, 0, rowDataList, rowStyleList)
                
                # resize columns
                _ = [sheetOBJ.set_column(col, col, strLen * 1.1) for col, strLen in enumerate(col_width)]
                
            showCompleteMessage(self.tr, outPath)

