#
# customQtClass.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 26th 2021
# -----
# Last Modified: Sat Nov 19 2022
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
from deps.SharedSrc import (dut_flag_parser, 
                            test_flag_parser, 
                            return_state_parser, 
                            getProperFontColor, REC, isPass)
import numpy as np



class StyleDelegateForTable_List(QStyledItemDelegate):
    """
    Customize highlight style for ListView & TableView
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        self.color_default = QtGui.QColor("#0096ff")

    def paint(self, painter, option: QtWidgets.QStyleOptionViewItem, index):
        # if option.state and QtWidgets.QStyle.State_Selected:
        #     # font color
        #     fgcolor = self.getColor(index, "FG")
        #     if fgcolor:
        #         option.palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, fgcolor)
        #     # background color
        #     bgcolor = self.combineColors(self.getColor(index, "BG"), self.color_default)
        #     # option.palette.setColor(QtGui.QPalette.Highlight, bgcolor)    # change color for listView
        #     painter.fillRect(option.rect, bgcolor)    # change color for tableView
        QStyledItemDelegate.paint(self, painter, option, index)

    def getColor(self, index, pos):
        parentWidget = self.parent()
        model = parentWidget.model()
        dataRole = QtCore.Qt.BackgroundRole if pos == "BG" else QtCore.Qt.ForegroundRole
        
        # TableView
        if isinstance(parentWidget, QtWidgets.QTableView):
            if isinstance(model, QtCore.QSortFilterProxyModel) or \
               isinstance(model, FlippedProxyModel) or \
               isinstance(model, NormalProxyModel):
                sourceIndex = model.mapToSource(index)
                return model.sourceModel().data(sourceIndex, dataRole)
            else:
                return self.parent().model().data(index, dataRole)

        # ListView
        if isinstance(parentWidget, QtWidgets.QListView):
            # my listView uses proxyModel
            sourceIndex = model.mapToSource(index)
            return self.parent().model().sourceModel().data(sourceIndex, dataRole)
        
    def combineColors(self, c1: QtGui.QColor, c2: QtGui.QColor) -> QtGui.QColor:
        c3 = QtGui.QColor()
        c3.setRed(int(c1.red()*0.7 + c2.red()*0.3))
        c3.setGreen(int(c1.green()*0.7 + c2.green()*0.3))
        c3.setBlue(int(c1.blue()*0.7 + c2.blue()*0.3))
        return c3



def getHS(text: str):
    l = text.split(" ")
    head, site = [int(ele) for ele in l if ele.isdigit()]
    return head << 8 | site


class DutSortFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hsFilterString = QtCore.QRegularExpression(r".*")
        self.fidColInd = 0
        self.pidColInd = 1
        self.hsColInd = 2
        self.tcntColInd = 3
        self.ttimColInd = 4
        self.hbinColInd = 5
        self.sbinColInd = 6
        self.widColInd = 7
        self.xyColInd = 8
        self.flagColInd = 9
        
    
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        if left.column() == right.column():
            # get text in the cell
            textLeft = self.sourceModel().data(left, QtCore.Qt.DisplayRole)
            textRight = self.sourceModel().data(right, QtCore.Qt.DisplayRole)
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
        
        hsMatched = self.hsFilterString.match(self.sourceModel().data(hsIndex, QtCore.Qt.DisplayRole)).hasMatch()
        
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
                        return QtGui.QColor("#FFFFFF")                        
                
                elif role == QtCore.Qt.ItemDataRole.BackgroundColorRole:
                    # mark fail row as red
                    if dutFlag.startswith("Fail"): return QtGui.QColor("#CC0000")
                    # mark superseded row as gray
                    elif dutFlag.startswith("Supersede"): return QtGui.QColor("#D0D0D0")
                    # mark unknown as orange
                    elif dutFlag.startswith("Unknown"): return QtGui.QColor("#FE7B00")
                
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
        self.fontsize = fontsize
        
    def data(self, index: QtCore.QModelIndex, role: int):        
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 1:
                return QtCore.Qt.AlignmentFlag.AlignLeft
            else:
                # change default aligment to center
                return QtCore.Qt.AlignmentFlag.AlignCenter
        
        if role == QtCore.Qt.ItemDataRole.FontRole:
            # set default font and size
            return QtGui.QFont("Courier New", self.fontsize)
        
        # return original data otherwise
        return super().data(index, role)
    
    
class TestDataTableModel(QtCore.QAbstractTableModel):
    '''
    Model for TestDataTable
    '''
    def __init__(self):
        super().__init__()
        self.testData = {}
        self.testInfo = {}
        self.dutIndMap = []
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
        
    def setDutIndexMap(self, dutIndMap: list):
        self.dutIndMap = dutIndMap
        
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
                if role == Qt.ItemDataRole.DisplayRole:
                    return ""
                if role == Qt.ItemDataRole.BackgroundRole:
                    return QtGui.QColor("#0F80FF7F")
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

            #TODO lower left contains dut info
            if index.row() >= len(self.vheader_base) and index.column() < len(self.hheader_base):
                if role == Qt.ItemDataRole.DisplayRole:
                    if index.column() == 0:
                        # part id
                        return "test id"
                    if index.column() == 1:
                        # head-site
                        return "head-site"
                if role == Qt.ItemDataRole.ForegroundRole:
                    # red only if failed
                    return QtGui.QColor("#000000")
                if role == Qt.ItemDataRole.BackgroundRole:
                    # red only if failed
                    return QtGui.QColor("#FFFFFF")
                if role == Qt.ItemDataRole.FontRole:
                    return self.font
                if role == Qt.ItemDataRole.TextAlignmentRole:
                    return Qt.AlignmentFlag.AlignCenter
                if role == Qt.ItemDataRole.ToolTipRole:
                    return None
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
                        return "Not Tested" if np.isnan(data) else f"Test Flag: {int(data)}"
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
                        return QtGui.QColor("#FFFFFF")
                
                if role == Qt.ItemDataRole.BackgroundRole:
                    # only if failed
                    if (data_ind != -1 and 
                        len(data_test_file) != 0 and 
                        not isPass(data_test_file["flagList"][data_ind])):
                        return QtGui.QColor("#CC0000")
                
                if role == Qt.ItemDataRole.TextAlignmentRole:
                    return Qt.AlignmentFlag.AlignCenter
                
                if role == Qt.ItemDataRole.ToolTipRole:
                    if data_ind == -1 or len(data_test_file) == 0:
                        return None
                    recHeader = data_test_file["recHeader"]
                    flag = data_test_file["flagList"][data_ind]
                    flagTip = test_flag_parser(flag)
                    if recHeader == REC.MPR:
                        RTNStat = data_test_file["statesList"][data_ind]
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
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        else:
            return Qt.ItemFlag.ItemIsEnabled
        
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
                return QtGui.QColor("#CC0000")
            if index.column() == self.indexOfCpk and (dataString not in ["N/A", "∞"]) and float(dataString) < self.cpkThreshold:
                return QtGui.QColor("#FE7B00")
        
        if role == Qt.ItemDataRole.ForegroundRole:
            if index.column() == self.indexOfFail and dataString != "0": 
                return QtGui.QColor("#FFFFFF")
            if index.column() == self.indexOfCpk and (dataString not in ["N/A", "∞"]) and float(dataString) < self.cpkThreshold:
                return QtGui.QColor("#FFFFFF")
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        try:
            self.content[index.row()][index.column()]
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
        item = ("", -1, False)
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
            self.content[index.row()][index.column()]
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
        
    
if __name__ == '__main__':
    testStrings = ['Site 1', 'Site 10', 'Site 100', 'Site 2', 'Site 22']
    
    siteFilterString = QtCore.QRegularExpression(r"\b[A-Za-z]+\s(0|1|2)\b")
    result = []
    for s in testStrings:
        result.append(siteFilterString.match(s).hasMatch())
    print(result)

    siteFilterString.setPattern("")
    result = []
    for s in testStrings:
        result.append(siteFilterString.match(s).hasMatch())
    print(result)

    siteFilterString.setPattern("$-")
    result = []
    for s in testStrings:
        result.append(siteFilterString.match(s).hasMatch())
    print(result)
    