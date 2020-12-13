#
# uic_stdSettings.py - STDF Viewer
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



from copy import copy
from deps.ui.ImgSrc_svg import ImgDict
# pyqt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from deps.ui.stdfViewer_settingsUI import Ui_Setting
# pyside2
# from PySide2 import QtCore, QtWidgets, QtGui
# from PySide2.QtCore import Signal, Slot
# from deps.ui.stdfViewer_settingsUI_side import Ui_Setting

# simulate a Enum in python
class Tab(tuple): __getattr__ = tuple.index
tab = Tab(["Info", "Trend", "Histo", "Bin"])

indexDic_sigma = {0: frozenset(),
                  1: frozenset([3]), 
                  2: frozenset([3, 6]), 
                  3: frozenset([3, 6, 9])}
indexDic_sigma_reverse = {v:k for k, v in indexDic_sigma.items()}

indexDic_notation = {0: "G",
                     1: "F",
                     2: "E"}
indexDic_notation_reverse = {v:k for k, v in indexDic_notation.items()}

class stdfSettings(QtWidgets.QDialog):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.settingsUI = Ui_Setting()
        self.settingsUI.setupUi(self)
        self.settingsUI.Confirm.clicked.connect(self.applySettings)
        self.settingsUI.Cancel.clicked.connect(self.close)
        self.settingsUI.lineEdit_binCount.setValidator(QtGui.QIntValidator(1, 1000, self))
        
        self.settingsUI.settingBox.setItemIcon(0, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_trend"], format = 'SVG'))))
        self.settingsUI.settingBox.setItemIcon(1, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_histo"], format = 'SVG'))))
        self.settingsUI.settingBox.setItemIcon(2, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["table"], format = 'SVG'))))
        
        if parent: 
            self.originalParams = copy(parent.settingParams)
            self.initWithParentParams()

        self.exec_()
        
        
    def initWithParentParams(self):
        # trend
        self.settingsUI.showHL_trend.setChecked(self.originalParams.showHL_trend)
        self.settingsUI.showLL_trend.setChecked(self.originalParams.showLL_trend)
        self.settingsUI.showMedian_trend.setChecked(self.originalParams.showMed_trend)
        self.settingsUI.showMean_trend.setChecked(self.originalParams.showMean_trend)
        # histo
        self.settingsUI.showHL_histo.setChecked(self.originalParams.showHL_histo)
        self.settingsUI.showLL_histo.setChecked(self.originalParams.showLL_histo)
        self.settingsUI.showMedian_histo.setChecked(self.originalParams.showMed_histo)
        self.settingsUI.showMean_histo.setChecked(self.originalParams.showMean_histo)
        self.settingsUI.showGaus_histo.setChecked(self.originalParams.showGaus_histo)
        self.settingsUI.showBoxp_histo.setChecked(self.originalParams.showBoxp_histo)
        self.settingsUI.lineEdit_binCount.setText(str(self.originalParams.binCount))
        self.settingsUI.sigmaCombobox.setCurrentIndex(indexDic_sigma_reverse[self.originalParams.showSigma])
        # table
        self.settingsUI.notationCombobox.setCurrentIndex(indexDic_notation_reverse[self.originalParams.dataNotation])
        self.settingsUI.precisionSlider.setValue(self.originalParams.dataPrecision)
        
        
    def updateSettings(self):
        parent = self.parent()
        # trend
        parent.settingParams.showHL_trend = self.settingsUI.showHL_trend.isChecked()
        parent.settingParams.showLL_trend = self.settingsUI.showLL_trend.isChecked()
        parent.settingParams.showMed_trend = self.settingsUI.showMedian_trend.isChecked()
        parent.settingParams.showMean_trend = self.settingsUI.showMean_trend.isChecked()
        # histo
        parent.settingParams.showHL_histo = self.settingsUI.showHL_histo.isChecked()
        parent.settingParams.showLL_histo = self.settingsUI.showLL_histo.isChecked()
        parent.settingParams.showMed_histo = self.settingsUI.showMedian_histo.isChecked()
        parent.settingParams.showMean_histo = self.settingsUI.showMean_histo.isChecked()
        parent.settingParams.showGaus_histo = self.settingsUI.showGaus_histo.isChecked()
        parent.settingParams.showBoxp_histo = self.settingsUI.showBoxp_histo.isChecked()
        parent.settingParams.binCount = int(self.settingsUI.lineEdit_binCount.text())
        parent.settingParams.showSigma = indexDic_sigma[self.settingsUI.sigmaCombobox.currentIndex()]
        # table
        parent.settingParams.dataNotation = indexDic_notation[self.settingsUI.notationCombobox.currentIndex()]
        parent.settingParams.dataPrecision = self.settingsUI.precisionSlider.value()
        
        
    def isTrendChanged(self):
        return not all([self.originalParams.showHL_trend == self.settingsUI.showHL_trend.isChecked(),
                        self.originalParams.showLL_trend == self.settingsUI.showLL_trend.isChecked(),
                        self.originalParams.showMed_trend == self.settingsUI.showMedian_trend.isChecked(),
                        self.originalParams.showMean_trend == self.settingsUI.showMean_trend.isChecked()])
        
        
    def isHistoChanged(self):
        return not all([self.originalParams.showHL_histo == self.settingsUI.showHL_histo.isChecked(),
                        self.originalParams.showLL_histo == self.settingsUI.showLL_histo.isChecked(),
                        self.originalParams.showMed_histo == self.settingsUI.showMedian_histo.isChecked(),
                        self.originalParams.showMean_histo == self.settingsUI.showMean_histo.isChecked(),
                        self.originalParams.showGaus_histo == self.settingsUI.showGaus_histo.isChecked(),
                        self.originalParams.showBoxp_histo == self.settingsUI.showBoxp_histo.isChecked(),
                        self.originalParams.binCount == int(self.settingsUI.lineEdit_binCount.text()),
                        self.originalParams.showSigma == indexDic_sigma[self.settingsUI.sigmaCombobox.currentIndex()]])
        
        
    def isTableChanged(self):
        return not all([self.originalParams.dataNotation == indexDic_notation[self.settingsUI.notationCombobox.currentIndex()],
                        self.originalParams.dataPrecision == self.settingsUI.precisionSlider.value()])


    def applySettings(self):
        parent = self.parent()
        if parent:
            self.updateSettings()
            if self.isTrendChanged() and (parent.ui.tabControl.currentIndex() == tab.Trend): 
                parent.updateTabContent(forceUpdate=True)
                
            if self.isHistoChanged() and (parent.ui.tabControl.currentIndex() == tab.Histo): 
                parent.updateTabContent(forceUpdate=True)
                
            if self.isTableChanged() and (parent.ui.tabControl.currentIndex() != tab.Bin): 
                parent.updateTableContent()
                parent.updateCursorPrecision()
                # if raw data table is active, update as well
                if (parent.ui.tabControl.currentIndex() == tab.Info) and (parent.ui.infoBox.currentIndex() == 2):
                    parent.updateTabContent(forceUpdate=True)
        self.close()
    
    def closeEvent(self, event):
        event.accept()
           
           
           
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication([])
    test = stdfSettings()
    sys.exit(app.exec_())
    
    
