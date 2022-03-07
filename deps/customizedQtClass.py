#
# customQtClass.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: May 26th 2021
# -----
# Last Modified: Tue Mar 01 2022
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



from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt, QModelIndex, QSortFilterProxyModel, QAbstractProxyModel



class StyleDelegateForTable_List(QStyledItemDelegate):
    """
    Customize highlight style for ListView & TableView
    """
    color_default = QtGui.QColor("#0096ff")

    def paint(self, painter, option, index):
        if option.state & QtWidgets.QStyle.State_Selected:
            # font color, foreground color
            # fgcolor = self.getColor(option, index, "FG")
            option.palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
            # background color
            bgcolor = self.combineColors(self.getColor(option, index, "BG"), self.color_default)
            option.palette.setColor(QtGui.QPalette.Highlight, bgcolor)    # change color for listView
            painter.fillRect(option.rect, bgcolor)    # change color for tableView
        QStyledItemDelegate.paint(self, painter, option, index)

    def getColor(self, option, index, pos):
        qitem = None
        parentWidget = self.parent()
        model = parentWidget.model()
        # TableView
        if isinstance(parentWidget, QtWidgets.QTableView):
            if isinstance(model, QtCore.QSortFilterProxyModel) or \
               isinstance(model, FlippedProxyModel) or \
               isinstance(model, NormalProxyModel):
                sourceIndex = model.mapToSource(index)
                qitem = model.sourceModel().itemFromIndex(sourceIndex)
            else:
                qitem = self.parent().model().itemFromIndex(index)

        # ListView
        if isinstance(parentWidget, QtWidgets.QListView):
            sourceIndex = model.mapToSource(index)
            row = sourceIndex.row()
            qitem = self.parent().model().sourceModel().item(row)   # my listView uses proxyModel
        
        if qitem:
            if pos == "BG":
                if qitem.background() != QtGui.QBrush():
                        return qitem.background().color()
            if pos == "FG":
                if qitem.foreground() != QtGui.QBrush():
                        return qitem.foreground().color()
        return option.palette.color(QtGui.QPalette.Base)

    def combineColors(self, c1, c2):
        c3 = QtGui.QColor()
        c3.setRed(int(c1.red()*0.7 + c2.red()*0.3))
        c3.setGreen(int(c1.green()*0.7 + c2.green()*0.3))
        c3.setBlue(int(c1.blue()*0.7 + c2.blue()*0.3))
        return c3



def getHS(text: str):
    l = text.split(" ")
    head, site = [int(ele) for ele in l if ele.isdigit()]
    return head << 8 | site

def tryInt(text: str) -> int:
    try:
        return int(text)
    except ValueError:
        return 0

def getNum(text: str):
    return tryInt(text.split(" ")[-1])    

class DutSortFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hsFilterString = QtCore.QRegularExpression(r".*")
        
    
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        if left.column() == right.column():
            # get text in the cell
            textLeft = self.sourceModel().itemData(left)[QtCore.Qt.DisplayRole]
            textRight = self.sourceModel().itemData(right)[QtCore.Qt.DisplayRole]
            if left.column() == 0:
                # sort part id
                try:
                    # assume part id is numerice data
                    return int(textLeft) < int(textRight)
                except ValueError:
                    # use default string compare
                    pass
                
            elif left.column() == 1:
                # sort head - site
                return getHS(textLeft) < getHS(textRight)
            
            elif left.column() == 2:
                # sort test count
                return tryInt(textLeft) < tryInt(textRight)
            
            elif left.column() == 3:
                # sort test time
                return tryInt(textLeft.strip("ms")) < tryInt(textRight.strip("ms"))
            
            elif left.column() == 4 or left.column() == 5:
                # sort hbin / sbin
                return getNum(textLeft) < getNum(textRight)

            elif left.column() == 6 or left.column() == 7 or left.column() == 8:
                # sort flag, wafer id, (X, Y)
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
        hsIndex = self.sourceModel().index(source_row, 1, source_parent)
        
        hsMatched = self.hsFilterString.match(self.sourceModel().data(hsIndex)).hasMatch()
        
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
    