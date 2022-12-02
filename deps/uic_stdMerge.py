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
                             QAbstractItemView, QTableView, QDialog)
from PyQt5.QtCore import QTranslator, Qt


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
        
        self.dataModel = MergeTableModel()
        setTableStyle(self.mergeUI.filetable1, self.dataModel)
        
        
    def showUI(self):
        #TODO clear all contents
        # self.mergeUI
        self.exec()


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
        view = self.mergeUI.filetable1
        model = self.dataModel
        
        model.addFiles(d)
        model.layoutChanged.emit()
        # hide columns that contains no data
        autoHideResize(view, model)
    
    
    def onRemoveFiles(self):
        pass
    
    
    def onMoveUp(self):
        pass
    
    
    def onMoveDown(self):
        pass
    
    
    def onAddGroup(self):
        pass
    
    
    def onRemoveGroup(self):
        pass
    
    
    def onConfirm(self):
        paths = []
        allGroupValid = True
        
        for gid in range(self.mergeUI.toolBox.count()):
            groupList = self.dataModel.getFilePaths()
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


