#
# uic_stdMerge.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 3rd 2022
# -----
# Last Modified: Sat Dec 03 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
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



from .ui.stdfViewer_mergeUI import Ui_mergeDialog
from .customizedQtClass import *
from .SharedSrc import *
import rust_stdf_helper

from PyQt5.QtWidgets import (QFileDialog, QMessageBox, QHeaderView, 
                             QAbstractItemView, QTableView, QDialog,
                             QWidget, QVBoxLayout)
from PyQt5.QtCore import QTranslator, Qt, QItemSelectionModel


def setTableStyle(view: QTableView, model: MergeTableModel):
    view.setModel(model)
    view.setItemDelegate(StyleDelegateForTable_List(view))
    view.setStyleSheet("QTableView :: item {padding: 20px}")
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)


def autoHideResize(view: QTableView, model: MergeTableModel):
    for col in range(model.columnCount()):
        hide = True
        for row in range(model.rowCount()):
            data = model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
            if isinstance(data, str) and data != "":
                hide = False
                break
        if hide:
            view.hideColumn(col)
        else:
            view.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)


class MergePanel(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.mergeUI = Ui_mergeDialog()
        self.mergeUI.setupUi(self)
        self.mainUI = parent
        self.box = self.mergeUI.toolBox
        self.translator = QTranslator(self)
        self.translator_code = QTranslator(self)
        # connect btns
        self.mergeUI.addf.clicked.connect(self.onAddFiles)
        self.mergeUI.removef.clicked.connect(self.onRemoveFiles)
        self.mergeUI.addg.clicked.connect(self.onAddGroup)
        self.mergeUI.removeg.clicked.connect(self.onRemoveGroup)
        self.mergeUI.moveUp.clicked.connect(self.onMoveUp)
        self.mergeUI.moveDown.clicked.connect(self.onMoveDown)
        self.mergeUI.confirm.clicked.connect(self.onConfirm)
        self.mergeUI.cancel.clicked.connect(self.close)
        # used for naming new merge group
        self.newGroupIndex = 0
        self.selectMode = QItemSelectionModel.SelectionFlag.Rows | QItemSelectionModel.SelectionFlag.Select
        # add model for default page
        defaultModel = MergeTableModel()
        setTableStyle(self.mergeUI.defaultTable, defaultModel)
        
        
    def showUI(self):
        self.show()


    def onAddFiles(self):
        files, _ = QFileDialog.getOpenFileNames(self, 
                                                caption=self.tr("Select STDF Files To Open"), 
                                                directory=getSetting().recentFolder, 
                                                filter=self.tr(FILE_FILTER),)
        if len(files) == 0:
            return
        
        d = []
        for f in files:
            try:
                infoDict = rust_stdf_helper.read_MIR(f)
                infoDict["Path"] = f
                d.append(infoDict)
            except OSError as e:
                QMessageBox.warning(None, self.tr("Warning"), str(e))
            except LookupError as e:
                QMessageBox.warning(None, self.tr("Warning"), str(e))
        
        updateRecentFolder(files[-1])
        # get active table view and model
        view, model = self.getCurrentViewModel()
        
        model.addFiles(d)
        model.layoutChanged.emit()
        # hide columns that contains no data
        autoHideResize(view, model)
    
    
    def onRemoveFiles(self):
        view, model = self.getCurrentViewModel()
        index2Removes = view.selectionModel().selectedRows()
        if index2Removes:
            row2Removes = [ind.row() for ind in index2Removes]
            # remove in reverse order to ensure
            # index validity
            for r in sorted(row2Removes, reverse=True):
                model.removeFile(r)
            model.layoutChanged.emit()
            autoHideResize(view, model)
    
    
    def onMoveUp(self):
        view, model = self.getCurrentViewModel()
        rows = [ind.row() for ind in view.selectionModel().selectedRows()]
        if rows:
            # clear previous selection and 
            # select moved rows
            selectionModel = view.selectionModel()
            selectionModel.clearSelection()
            
            for row in rows:
                # move if it's not 1st row
                if row > 0:
                    model.moveFile(row, up=True)
                    row_new = row - 1
                else:
                    row_new = row
                selectionModel.select(model.index(row_new, 0), self.selectMode)
            model.layoutChanged.emit()
    
    
    def onMoveDown(self):
        view, model = self.getCurrentViewModel()
        rows = [ind.row() for ind in view.selectionModel().selectedRows()]
        if rows:
            selectionModel = view.selectionModel()
            selectionModel.clearSelection()
            
            for row in sorted(rows):
                # move if it's not last row
                if row != model.rowCount() - 1:
                    model.moveFile(row, up=False)
                    row_new = row + 1
                else:
                    row_new = row
                selectionModel.select(model.index(row_new, 0), self.selectMode)
            model.layoutChanged.emit()
    
    
    def onAddGroup(self):
        self.newGroupIndex += 1
        # new page
        newpage = QWidget()
        vlayout = QVBoxLayout(newpage)
        tableview = QTableView(newpage)
        vlayout.addWidget(tableview)
        self.box.addItem(newpage, f"Merge Group {self.newGroupIndex}")
        # new model
        model = MergeTableModel()
        setTableStyle(tableview, model)
    
    
    def onRemoveGroup(self):
        activeIndex = self.box.currentIndex()
        if activeIndex > 0:
            msg = QMessageBox.information(None, "", 
                                    self.tr("Are you sure to remove this group?"), 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
            if msg == QMessageBox.StandardButton.Yes:
                activePage = self.box.widget(activeIndex)
                deleteWidget(activePage)
        else:
            QMessageBox.information(None, "", self.tr("Default merge group cannot be removed"))
    
    
    def onConfirm(self):
        paths = []
        allGroupValid = True
        
        for gid in range(self.box.count()):
            _, model = self.getViewModelFromPage(gid)
            groupList = model.getFilePaths()
            allGroupValid = allGroupValid and (len(groupList) > 0)
            paths.append(groupList)
            
        if paths and allGroupValid:
            # clear all data
            self.hide()
            self.mainUI.callFileLoader(paths)
            self.close()
        else:
            QMessageBox.information(None, self.tr("Empty group detected"), 
                                    self.tr("Add at lease one STDF file into each group to continue..."))
    
    
    def getViewModelFromPage(self, groupId: int) -> tuple:
        page = self.box.widget(groupId)
        tableview = page.layout().itemAt(0).widget()
        model = tableview.model()
        
        return tableview, model


    def getCurrentViewModel(self) -> tuple:
        gid = self.box.currentIndex()
        return self.getViewModelFromPage(gid)
