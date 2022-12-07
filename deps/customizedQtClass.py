#
# customQtClass.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 26th 2021
# -----
# Last Modified: Thu Dec 08 2022
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



from PyQt5 import QtCore, QtWidgets, QtGui, QtSql
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt, QModelIndex, QSortFilterProxyModel, QAbstractProxyModel
from deps.SharedSrc import *
import numpy as np



class StyleDelegateForTable_List(QStyledItemDelegate):
    """
    Customize highlight style for ListView & TableView
    """
    
    def __init__(self, parent):
        super().__init__()
        self.parentWidget = parent
        self.highlightColor = QtGui.QColor("#0096FF")

    def paint(self, painter, option: QtWidgets.QStyleOptionViewItem, index):
        # this line causes text color flicking
        # self.initStyleOption(option, index)
        if (option.state & QtWidgets.QStyle.StateFlag.State_Selected and 
            option.state & QtWidgets.QStyle.StateFlag.State_Active):
            # get foreground color
            fg = self.getColor(index, isBG = False)
            # get background color
            bg = self.getColor(index, isBG = True)
            # set highlight color
            if fg:
                # if fg is None, do not set color
                option.palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, 
                                        self.mixColors(fg))
            option.palette.setColor(QtGui.QPalette.ColorRole.Highlight, 
                                    self.mixColors(bg))
        QStyledItemDelegate.paint(self, painter, option, index)

    def getColor(self, index: QModelIndex, isBG = True):
        model = self.parentWidget.model()
        dataRole = Qt.ItemDataRole.BackgroundRole if isBG else Qt.ItemDataRole.ForegroundRole
        
        # TableView
        if isinstance(self.parentWidget, QtWidgets.QTableView):
            if (isinstance(model, QSortFilterProxyModel) or     # dut summary
                isinstance(model, FlippedProxyModel) or         # dut data table
                isinstance(model, NormalProxyModel)):           # dut data table
                # proxy model
                sourceIndex = model.mapToSource(index)
                return model.sourceModel().data(sourceIndex, dataRole)
            
            elif (isinstance(model, TestDataTableModel) or      # test data table
                  isinstance(model, TestStatisticTableModel) or # test stat table
                  isinstance(model, BinWaferTableModel)):       # bin/wafer table
                # abstract table model
                return model.data(index, dataRole)

        # ListView
        if isinstance(self.parentWidget, QtWidgets.QListView):
            if isinstance(model, QSortFilterProxyModel):
                # all of listView uses proxyModel
                sourceIndex = model.mapToSource(index)
                return model.sourceModel().data(sourceIndex, dataRole)
        
        return None
        
    def mixColors(self, src) -> QtGui.QColor:
        if isinstance(src, QtGui.QColor):
            r = int(src.red()*0.7   + self.highlightColor.red()*0.3)
            g = int(src.green()*0.7 + self.highlightColor.green()*0.3)
            b = int(src.blue()*0.7  + self.highlightColor.blue()*0.3)
            return QtGui.QColor(r, g, b)
        else:
            return self.highlightColor


def getHS(text: str):
    seglist = text.split(" ")
    head, site = [int(ele) for ele in seglist if ele.isdigit()]
    return head << 8 | site


class DutSortFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hsFilterString = QtCore.QRegularExpression(r".*")
        self.dutIndexInd = 0
        self.fidColInd = 1
        self.pidColInd = 2
        self.hsColInd = 3
        self.tcntColInd = 4
        self.ttimColInd = 5
        self.hbinColInd = 6
        self.sbinColInd = 7
        self.widColInd = 8
        self.xyColInd = 9
        self.flagColInd = 10
        
    
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        if left.column() == right.column():
            # get text in the cell
            textLeft = self.sourceModel().data(left, Qt.ItemDataRole.DisplayRole)
            textRight = self.sourceModel().data(right, Qt.ItemDataRole.DisplayRole)
            try:
                if (left.column() == self.fidColInd or 
                    left.column() == self.pidColInd):
                    # sort file id || part id
                    return int(textLeft) < int(textRight)
                    
                elif left.column() == self.hsColInd:
                    # sort head - site
                    return getHS(textLeft) < getHS(textRight)
                
                elif left.column() == self.tcntColInd:
                    # sort test count
                    return int(textLeft) < int(textRight)
                
                elif left.column() == self.ttimColInd:
                    # sort test time
                    return int(textLeft.strip("ms")) < int(textRight.strip("ms"))
                
                elif (left.column() == self.hbinColInd or 
                      left.column() == self.sbinColInd):
                    # sort hbin / sbin
                    return int(textLeft.split(" ")[-1]) < int(textRight.split(" ")[-1])

                elif (left.column() == self.widColInd or 
                      left.column() == self.xyColInd or 
                      left.column() == self.flagColInd):
                    # sort flag, wafer id, (X, Y)
                    pass
                
            except ValueError:
                # use default string compare
                pass
            
        return super().lessThan(left, right)
    
    
    def updateHeadsSites(self, selHeads: list, selSites: list):
        if len(selHeads) != 0 and len(selSites) != 0:
            headNums = "|".join([str(i) for i in selHeads])
            
            if -1 in selSites:
                self.hsFilterString.setPattern(fr"\b[A-Za-z]+\s({headNums})\s-\s[A-Za-z]+\s[0-9]+\b")
            else:
                siteNums = "|".join([str(i) for i in selSites])
                self.hsFilterString.setPattern(fr"\b[A-Za-z]+\s({headNums})\s-\s[A-Za-z]+\s({siteNums})\b")
        else:
            # https://stackoverflow.com/a/56074681/10490375
            # do not match anything
            self.hsFilterString.setPattern("$-")
        
        self.invalidateFilter()

    
    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        hsIndex = self.sourceModel().index(source_row, self.hsColInd, source_parent)
        
        hsMatched = self.hsFilterString.match(self.sourceModel().data(hsIndex, Qt.ItemDataRole.DisplayRole)).hasMatch()
        
        return hsMatched
    
    
class FlippedProxyModel(QAbstractProxyModel):
    '''
    For transposing tableView display, modified from:
    https://www.howtobuildsoftware.com/index.php/how-do/bgJv/pyqt-pyside-qsqltablemodel-qsqldatabase-qsqlrelationaltablemodel-with-qsqlrelationaldelegate-not-working-behind-qabstractproxymodel
    '''
    def __init__(self, parent=None):
        super().__init__(parent)

    def mapFromSource(self, index):
        return self.createIndex(index.column(), index.row())

    def mapToSource(self, index):
        return self.sourceModel().index(index.column(), index.row(), QModelIndex())

    def columnCount(self, parent = QModelIndex()):
        return self.sourceModel().rowCount(parent)

    def rowCount(self, parent = QModelIndex()):
        return self.sourceModel().columnCount(parent)

    def index(self, row, column, parent = QModelIndex()):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def data(self, index, role):
        return self.sourceModel().data(self.mapToSource(index), role)

    def item(self, row, column) -> QtGui.QStandardItem:
        return self.sourceModel().item(column, row)
    
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal:
            return self.sourceModel().headerData(section, Qt.Vertical, role)
        if orientation == Qt.Vertical:
            return self.sourceModel().headerData(section, Qt.Horizontal, role)


# For normal tableView display
class NormalProxyModel(QAbstractProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mapFromSource(self, index):
        return self.createIndex(index.row(), index.column())

    def mapToSource(self, index):
        return self.sourceModel().index(index.row(), index.column(), QModelIndex())

    def columnCount(self, parent = QModelIndex()):
        return self.sourceModel().columnCount(parent)

    def rowCount(self, parent = QModelIndex()):
        return self.sourceModel().rowCount(parent)

    def index(self, row, column, parent = QModelIndex()):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def data(self, index, role):
        return self.sourceModel().data(self.mapToSource(index), role)

    def item(self, row, column) -> QtGui.QStandardItem:
        return self.sourceModel().item(column, row)
    
    def headerData(self, section, orientation, role):
        return self.sourceModel().headerData(section, orientation, role)

    
class ColorSqlQueryModel(QtSql.QSqlQueryModel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        
    def data(self, index: QtCore.QModelIndex, role: int):
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            # change default aligment to center
            return QtCore.Qt.AlignmentFlag.AlignCenter
        
        if (role == QtCore.Qt.ItemDataRole.ForegroundRole or 
            role == QtCore.Qt.ItemDataRole.BackgroundColorRole or 
            role == QtCore.Qt.ItemDataRole.ToolTipRole):
            # set row background, font color and tooltips according to flag status
            
            # get dut flag string, which is the 
            # right most element of current row
            dutFlagIndex = super().index(index.row(), super().columnCount()-1)
            dutFlag = super().data(dutFlagIndex, QtCore.Qt.ItemDataRole.DisplayRole)
            if isinstance(dutFlag, str):
                if role == QtCore.Qt.ItemDataRole.ForegroundRole:
                    if dutFlag.startswith("Fail") or dutFlag.startswith("Supersede"):
                        # set to font color to white
                        return QtGui.QColor(WHITE_COLOR)
                
                elif role == QtCore.Qt.ItemDataRole.BackgroundColorRole:
                    # mark fail row as red
                    if dutFlag.startswith("Fail"): return QtGui.QColor(FAIL_DUT_COLOR)
                    # mark superseded row as gray
                    elif dutFlag.startswith("Supersede"): return QtGui.QColor(OVRD_DUT_COLOR)
                    # mark unknown as orange
                    elif dutFlag.startswith("Unknown"): return QtGui.QColor(UNKN_DUT_COLOR)
                
                elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
                    if not dutFlag.startswith("Pass"): 
                        # get flag number
                        flag_str = dutFlag.split("-")[-1]
                        tip = dut_flag_parser(flag_str)
                        if dutFlag.startswith("Supersede"):
                            tip = "This dut is replaced by other dut\n" + tip
                        return tip
                
                else:
                    pass
        # return original data otherwise
        return super().data(index, role)


class DatalogSqlQueryModel(QtSql.QSqlQueryModel):
    def __init__(self, parent, fontsize: int) -> None:
        super().__init__(parent)
        self.defaultFont = QtGui.QFont()
        self.defaultFont.setPointSize(fontsize)
        
    def data(self, index: QtCore.QModelIndex, role: int):        
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 2:
                # left align `Value` column for better display
                return QtCore.Qt.AlignmentFlag.AlignLeft
            else:
                # change default aligment to center
                return QtCore.Qt.AlignmentFlag.AlignCenter
        
        if role == QtCore.Qt.ItemDataRole.FontRole:
            # set default font and size
            return self.defaultFont
        
        # return original data otherwise
        return super().data(index, role)
    
    
class TestDataTableModel(QtCore.QAbstractTableModel):
    '''
    Model for TestDataTable and DutDataTable
    '''
    def __init__(self):
        super().__init__()
        self.testData = {}
        self.testInfo = {}
        self.dutIndMap = {}
        self.dutInfoMap = {}
        self.hheader_base = []
        self.vheader_base = []
        self.testLists = []
        self.vheader_ext = []
        self.font = QtGui.QFont()
        self.floatFormat = "%f"
        
    def setTestData(self, testData: dict):
        self.testData = testData
        
    def setTestInfo(self, testInfo: dict):
        self.testInfo = testInfo
        
    def setDutIndexMap(self, dutIndMap: dict):
        self.dutIndMap = dutIndMap
        
    def setDutInfoMap(self, dutInfo: dict):
        self.dutInfoMap = dutInfo
        
    def setHHeaderBase(self, hheaderBase: list):
        self.hheader_base = hheaderBase
        
    def setVHeaderBase(self, vheaderBase: list):
        self.vheader_base = vheaderBase
        
    def setTestLists(self, testLists: list):
        self.testLists = testLists
        
    def setVHeaderExt(self, vheader_ext: list):
        self.vheader_ext = vheader_ext
        
    def setFont(self, font: QtGui.QFont):
        self.font = font
        
    def setFloatFormat(self, floatFormat: str):
        self.floatFormat = floatFormat
        
    def data(self, index: QModelIndex, role: int):
        '''
        divide table into 4 sections
        blank    | test info (limit/unit)
        ------------------------------
        dut info | test data
        '''
        try:
            # upper left corner contains no info
            if index.row() < len(self.vheader_base) and index.column() < len(self.hheader_base):
                # prevent fall below
                return None
            
            # upper right corner contains test info
            if index.row() < len(self.vheader_base):
                if role == Qt.ItemDataRole.DisplayRole:
                    test_index = index.column() - len(self.hheader_base)
                    if index.row() == 0:
                        # test number
                        return "%d" % self.testInfo[self.testLists[test_index]][1]
                    if index.row() == 1:
                        # high limit
                        hl = self.testInfo[self.testLists[test_index]][2]
                        return "N/A" if np.isnan(hl) else self.floatFormat % hl
                    if index.row() == 2:
                        # low limit
                        ll = self.testInfo[self.testLists[test_index]][3]
                        return "N/A" if np.isnan(ll) else self.floatFormat % ll
                    if index.row() == 3:
                        # unit
                        return self.testInfo[self.testLists[test_index]][4]
                if role == Qt.ItemDataRole.BackgroundRole:
                    return QtGui.QColor("#0F80FF7F")
                if role == Qt.ItemDataRole.TextAlignmentRole:
                    return Qt.AlignmentFlag.AlignCenter
                return None

            # lower left contains dut info
            if index.row() >= len(self.vheader_base) and index.column() < len(self.hheader_base):
                fileStr, dutIndStr = self.vheader_ext[index.row() - len(self.vheader_base)].split(" ")
                fid = int(fileStr.strip("File"))
                dutIndex = int(dutIndStr.strip("#"))
                # dut info can be 3-element or 10-element
                # depending on which table is using this model
                dutInfoTup = self.dutInfoMap[fid][dutIndex]
                # flag string is always the last element
                flagStr = dutInfoTup[-1]
                
                if role == Qt.ItemDataRole.DisplayRole:
                    return dutInfoTup[index.column()]

                if role == Qt.ItemDataRole.ForegroundRole:
                    if flagStr.startswith("Fail") or flagStr.startswith("Supersede"):
                        # set to font color to white
                        return QtGui.QColor(WHITE_COLOR)

                if role == Qt.ItemDataRole.BackgroundRole:
                    # mark fail row as red
                    if flagStr.startswith("Fail"): return QtGui.QColor(FAIL_DUT_COLOR)
                    # mark superseded row as gray
                    elif flagStr.startswith("Supersede"): return QtGui.QColor(OVRD_DUT_COLOR)
                    # mark unknown as orange
                    elif flagStr.startswith("Unknown"): return QtGui.QColor(UNKN_DUT_COLOR)
                
                if role == Qt.ItemDataRole.FontRole:
                    return self.font
                if role == Qt.ItemDataRole.TextAlignmentRole:
                    return Qt.AlignmentFlag.AlignCenter
                if role == Qt.ItemDataRole.ToolTipRole:
                    if not flagStr.startswith("Pass"): 
                        # get flag number
                        numStr = flagStr.split("-")[-1]
                        tip = dut_flag_parser(numStr)
                        if flagStr.startswith("Supersede"):
                            tip = "This dut is replaced by other dut\n" + tip
                        return tip
                return None
                    
            # lower right contains test data
            if index.row() >= len(self.vheader_base):
                # get test data indexes
                test_index = index.column() - len(self.hheader_base)
                fileStr, dutIndStr = self.vheader_ext[index.row() - len(self.vheader_base)].split(" ")
                fid = int(fileStr.strip("File"))
                dutIndex = int(dutIndStr.strip("#"))
                # dict is empty if current fid doesn't contains `self.testLists[test_index]`
                data_test_file: dict = self.testData[self.testLists[test_index]][fid]
                data_ind = self.dutIndMap[fid].get(dutIndex, -1)
                
                if role == Qt.ItemDataRole.DisplayRole:
                    if data_ind == -1 or len(data_test_file) == 0:
                        # test not exist in current file
                        return "Not Tested"
                    recHeader = data_test_file["recHeader"]
                    if recHeader == REC.FTR:
                        data = data_test_file["dataList"][data_ind]
                        return "Not Tested" if np.isnan(data) or data < 0 else f"Test Flag: {int(data)}"
                    elif recHeader == REC.PTR:
                        data = data_test_file["dataList"][data_ind]
                        return "Not Tested" if np.isnan(data) else self.floatFormat % data
                    else:
                        # MPR
                        if data_test_file["dataList"].size == 0:
                            # No PMR related and no test data in MPR, use test flag instead
                            flag = data_test_file["flagList"][data_ind]
                            return "Not Tested" if flag < 0 else f"Test Flag: {flag}"
                        else:
                            data = data_test_file["dataList"][data_ind]
                            return "Not Tested" if np.isnan(data) else self.floatFormat % data
                
                if role == Qt.ItemDataRole.ForegroundRole:
                    # only if failed
                    if (data_ind != -1 and 
                        len(data_test_file) != 0 and 
                        not isPass(data_test_file["flagList"][data_ind])):
                        return QtGui.QColor(WHITE_COLOR)
                
                if role == Qt.ItemDataRole.BackgroundRole:
                    # only if failed
                    if (data_ind != -1 and 
                        len(data_test_file) != 0 and 
                        not isPass(data_test_file["flagList"][data_ind])):
                        return QtGui.QColor(FAIL_DUT_COLOR)
                
                if role == Qt.ItemDataRole.TextAlignmentRole:
                    return Qt.AlignmentFlag.AlignCenter
                
                if role == Qt.ItemDataRole.ToolTipRole:
                    if data_ind == -1 or len(data_test_file) == 0:
                        return None
                    recHeader = data_test_file["recHeader"]
                    flag = data_test_file["flagList"][data_ind]
                    flagTip = test_flag_parser(flag)
                    if recHeader == REC.MPR:
                        RTNStat = data_test_file["stateList"][data_ind]
                        statTip = return_state_parser(RTNStat)
                        return "\n".join([t for t in [statTip, flagTip] if t])
                    else:
                        # PTR & FTR
                        if flagTip:
                            return flagTip
        
        except (IndexError, KeyError):
            pass
            
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.row() >= len(self.vheader_base):
            # dut info + data section
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        elif index.column() >= len(self.hheader_base):
            # test info section
            return Qt.ItemFlag.ItemIsEnabled
        else:
            return Qt.ItemFlag.NoItemFlags
        
    def rowCount(self, parent=None) -> int:
        return len(self.vheader_base) + len(self.vheader_ext)
    
    def columnCount(self, parent=None) -> int:
        # test names use as column header
        return len(self.hheader_base) + len(self.testLists)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        
        try:
            addPadding = lambda s: f"  {s}  "
            if orientation == Qt.Orientation.Horizontal:
                if section < len(self.hheader_base):
                    return addPadding(self.hheader_base[section])
                else:
                    # get test name index by minus base length
                    test_index = section - len(self.hheader_base)
                    test_name = self.testInfo[self.testLists[test_index]][0]
                    return addPadding(test_name)
                    
            if orientation == Qt.Orientation.Vertical:
                if section < len(self.vheader_base):
                    return self.vheader_base[section]
                else:
                    ext_index = section - len(self.vheader_base)
                    return self.vheader_ext[ext_index]
            
        except (IndexError, KeyError):
            return ""


class TestStatisticTableModel(QtCore.QAbstractTableModel):
    '''
    content: 2D list of strings, contains data like test num, cpk, etc.
    '''
    def __init__(self):
        super().__init__()
        self.content = []
        self.hheader = []
        self.vheader = []
        self.colLen = 0
        self.indexOfFail = 0
        self.indexOfCpk = 0
        self.cpkThreshold = 0.0
        
    def setContent(self, content: list):
        self.content = content
        
    def setFailCpkIndex(self, failInd: int, CpkInd: int):
        self.indexOfFail = failInd
        self.indexOfCpk = CpkInd
        
    def setCpkThreshold(self, threshold: float):
        self.cpkThreshold = threshold
        
    def setColumnCount(self, colLen: int):
        self.colLen = colLen
        
    def setHHeader(self, hheader: list):
        self.hheader = hheader
        
    def setVHeader(self, vheader: list):
        self.vheader = vheader
        
    def data(self, index: QModelIndex, role: int):
        dataString = ""
        try:
            dataString: str = self.content[index.row()][index.column()]
        except IndexError:
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            return dataString
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        
        if role == Qt.ItemDataRole.BackgroundRole:
            if index.column() == self.indexOfFail and dataString != "0": 
                return QtGui.QColor(FAIL_DUT_COLOR)
            if index.column() == self.indexOfCpk and (dataString not in ["N/A", "∞"]) and float(dataString) < self.cpkThreshold:
                return QtGui.QColor(UNKN_DUT_COLOR)
        
        if role == Qt.ItemDataRole.ForegroundRole:
            if index.column() == self.indexOfFail and dataString != "0": 
                return QtGui.QColor(WHITE_COLOR)
            if index.column() == self.indexOfCpk and (dataString not in ["N/A", "∞"]) and float(dataString) < self.cpkThreshold:
                return QtGui.QColor(WHITE_COLOR)
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        try:
            _ = self.content[index.row()][index.column()]
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        except IndexError:
            return Qt.ItemFlag.NoItemFlags
        
    def rowCount(self, parent=None) -> int:
        return len(self.content)
    
    def columnCount(self, parent=None) -> int:
        return self.colLen
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        
        if orientation == Qt.Orientation.Horizontal:
            header = self.hheader
        else:
            header = self.vheader
            
        try:
            return header[section]
        except IndexError:
            return ""


class BinWaferTableModel(QtCore.QAbstractTableModel):
    '''
    content: 2D list of tuple ("Display String", bin_number, isHBIN), 
            if bin_num is -1, indicating it's not related to HBIN or SBIN, 
            use default background color, 
            otherwise use HBIN or SBIN color stored in color_dict.
    '''
    def __init__(self):
        super().__init__()
        self.content = []
        self.hheader = []
        self.vheader = []
        self.hbin_color = {}
        self.sbin_color = {}
        self.colLen = 0
        
    def setContent(self, content: list):
        self.content = content
        
    def setColorDict(self, hbin_color: dict, sbin_color: dict):
        self.hbin_color = hbin_color
        self.sbin_color = sbin_color
    
    def setColumnCount(self, colLen: int):
        self.colLen = colLen
        
    def setHHeader(self, hheader: list):
        self.hheader = hheader
        
    def setVHeader(self, vheader: list):
        self.vheader = vheader
        
    def data(self, index: QModelIndex, role: int):
        try:
            item: tuple = self.content[index.row()][index.column()]
        except IndexError:
            return None
        # unpack
        dataString, bin_num, isHbin = item
        
        if role == Qt.ItemDataRole.DisplayRole:
            return dataString
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        
        if role == Qt.ItemDataRole.BackgroundRole:
            if bin_num != -1:
                color_dict = self.hbin_color if isHbin else self.sbin_color
                return QtGui.QColor(color_dict[bin_num])
        
        if role == Qt.ItemDataRole.ForegroundRole:
            if bin_num != -1:
                color_dict = self.hbin_color if isHbin else self.sbin_color
                background = QtGui.QColor(color_dict[bin_num])
                return getProperFontColor(background)
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        try:
            _ = self.content[index.row()][index.column()]
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        except IndexError:
            return Qt.ItemFlag.NoItemFlags
        
    def rowCount(self, parent=None) -> int:
        return len(self.content)
    
    def columnCount(self, parent=None) -> int:
        return self.colLen
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        
        if orientation == Qt.Orientation.Horizontal:
            header = self.hheader
        else:
            header = self.vheader
            
        try:
            return header[section]
        except IndexError:
            return ""
        
    
class MergeTableModel(QtCore.QAbstractTableModel):
    '''
    For displaying STDF MIR records in merge panel
    Contents: dict of MIR records
    '''
    def __init__(self):
        super().__init__()
        self.contents = []
        
    def addFiles(self, data):
        if isinstance(data, dict):
            self.contents.append(data)
        elif isinstance(data, list):
            self.contents.extend(data)
        else:
            raise TypeError("expect dict or list")
        
    def removeFile(self, index: int):
        try:
            self.contents.pop(index)
        except IndexError:
            pass
        
    def moveFile(self, srcIndex: int, up: bool):
        try:
            desIndex = srcIndex - 1 if up else srcIndex + 1
            src = self.contents[srcIndex]
            des = self.contents[desIndex]
            # switch
            self.contents[srcIndex] = des
            self.contents[desIndex] = src
        except IndexError:
            pass
    
    def getFilePaths(self) -> list:
        paths = []
        for row in range(self.rowCount()):
            paths.append(self.data(self.index(row, 0), Qt.ItemDataRole.DisplayRole))
        return paths
        
    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            try:
                fileInfoDict = self.contents[row]
                if col == 0:
                    data = fileInfoDict["Path"]
                else:
                    data = fileInfoDict.get(mirFieldNames[col], None)
            except IndexError:
                data = None
            return data
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        
        return None

    def rowCount(self, parent=None) -> int:
        return len(self.contents)
    
    def columnCount(self, parent=None) -> int:
        return len(mirFieldNames)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole or self.rowCount() == 0:
            return None
        
        if orientation == Qt.Orientation.Horizontal:
            if section == 0:
                # change first element to file path
                header = "File Path"
            else:
                header = mirDict[mirFieldNames[section]]
        else:
            header = section
            
        return header



__all__ = ["StyleDelegateForTable_List", "DutSortFilter", 
           "FlippedProxyModel", "NormalProxyModel", 
           "ColorSqlQueryModel", "DatalogSqlQueryModel", 
           "TestDataTableModel", "TestStatisticTableModel", 
           "BinWaferTableModel", "MergeTableModel", 
           ]

