#
# uic_stdSettings.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Mon Feb 15 2021
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



from random import choice
from copy import deepcopy
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

rHEX = lambda: "#"+"".join([choice('0123456789ABCDEF') for j in range(6)])

class colorBtn(QtWidgets.QWidget):
    def __init__(self, parent=None, name="", num=None):
        super().__init__(parent=parent)
        self.name = name
        self.num = num
        self.setObjectName(self.name)
        self.hLayout = QtWidgets.QHBoxLayout(self)
        self.hLayout.setSpacing(5)
        # label
        self.label = QtWidgets.QLabel(self)
        self.label.setText(self.name)
        self.label.setStyleSheet("font: 12pt Courier")
        self.hLayout.addWidget(self.label)
        # color square
        self.square = QtWidgets.QWidget(self)
        self.square.setFixedSize(25, 25)
        self.square.setStyleSheet("border:1px solid #000000;")
        self.hLayout.addWidget(self.square)
        self.square.mouseReleaseEvent = self.showPalette
        # spacer to avoid label from leaving button when resizing
        spacerItem = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.hLayout.addItem(spacerItem)
        
    def setColor(self, qcolor):
        self.square.setStyleSheet("border:1px solid #000000; background-color:%s;"%str(qcolor.name()))
        # palette = self.square.palette()
        # palette.setColor(QtGui.QPalette.Background, qcolor)
        # self.square.setPalette(palette)
        # self.square.setAutoFillBackground(True)        
    
    def getHEXColor(self):
        qcolor = self.square.palette().button().color()
        return str(qcolor.name())
    
    def setName(self, name):
        self.name = name
        self.label.setText(self.name)
        
    def setNum(self, num):
        self.num = num
        
    def showPalette(self, event):
        currentColor = self.square.palette().button().color()
        color = QtWidgets.QColorDialog.getColor(parent=self, initial=currentColor)
        if color.isValid():
            self.setColor(color)
        else:
            self.setColor(currentColor)


class stdfSettings(QtWidgets.QDialog):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.parent = parent
        if self.parent: self.originalParams = deepcopy(self.parent.settingParams)
        self.settingsUI = Ui_Setting()
        self.settingsUI.setupUi(self)
        self.settingsUI.Confirm.clicked.connect(self.applySettings)
        self.settingsUI.Cancel.clicked.connect(self.close)
        self.settingsUI.lineEdit_binCount.setValidator(QtGui.QIntValidator(1, 1000, self))
        self.settingsUI.lineEdit_cpk.setValidator(QtGui.QDoubleValidator(self))
        
        self.settingsUI.settingBox.setItemIcon(0, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_trend"], format = 'SVG'))))
        self.settingsUI.settingBox.setItemIcon(1, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_histo"], format = 'SVG'))))
        self.settingsUI.settingBox.setItemIcon(2, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["table"], format = 'SVG'))))
        self.settingsUI.settingBox.setItemIcon(3, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["color_palette"], format = 'SVG'))))
                
        
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
        self.settingsUI.lineEdit_cpk.setText(str(self.originalParams.cpkThreshold))
        # color
        for (orig_dict, layout) in [(self.originalParams.siteColor, self.settingsUI.gridLayout_site_color),
                                    (self.originalParams.sbinColor, self.settingsUI.gridLayout_sbin_color),
                                    (self.originalParams.hbinColor, self.settingsUI.gridLayout_hbin_color)]:
            for i in range(layout.count()):
                cB = layout.itemAt(i).widget()
                orig_color = orig_dict.get(cB.num, rHEX())
                cB.setColor(QtGui.QColor(orig_color))
            
        
    def currentColorDict(self, get=True, group=""):
        if get:
            # get color dict from current settings
            obj = self.originalParams
        else:
            # apply color dict setting
            obj = self.parent.settingParams
        
        if group == "site": 
            layout = self.settingsUI.gridLayout_site_color
            color_dict = obj.siteColor
        elif group == "sbin": 
            layout = self.settingsUI.gridLayout_sbin_color
            color_dict = obj.sbinColor
        elif group == "hbin": 
            layout = self.settingsUI.gridLayout_hbin_color
            color_dict = obj.hbinColor
        else: 
            layout = None
            color_dict = {}
            
        if layout:
            for i in range(layout.count()):
                cB = layout.itemAt(i).widget()
                num = cB.num
                hex = cB.getHEXColor()
                color_dict[num] = hex
        if get: return color_dict
                            
    
    def updateSettings(self):
        # trend
        self.parent.settingParams.showHL_trend = self.settingsUI.showHL_trend.isChecked()
        self.parent.settingParams.showLL_trend = self.settingsUI.showLL_trend.isChecked()
        self.parent.settingParams.showMed_trend = self.settingsUI.showMedian_trend.isChecked()
        self.parent.settingParams.showMean_trend = self.settingsUI.showMean_trend.isChecked()
        # histo
        self.parent.settingParams.showHL_histo = self.settingsUI.showHL_histo.isChecked()
        self.parent.settingParams.showLL_histo = self.settingsUI.showLL_histo.isChecked()
        self.parent.settingParams.showMed_histo = self.settingsUI.showMedian_histo.isChecked()
        self.parent.settingParams.showMean_histo = self.settingsUI.showMean_histo.isChecked()
        self.parent.settingParams.showGaus_histo = self.settingsUI.showGaus_histo.isChecked()
        self.parent.settingParams.showBoxp_histo = self.settingsUI.showBoxp_histo.isChecked()
        self.parent.settingParams.binCount = int(self.settingsUI.lineEdit_binCount.text())
        self.parent.settingParams.showSigma = indexDic_sigma[self.settingsUI.sigmaCombobox.currentIndex()]
        # table
        self.parent.settingParams.dataNotation = indexDic_notation[self.settingsUI.notationCombobox.currentIndex()]
        self.parent.settingParams.dataPrecision = self.settingsUI.precisionSlider.value()
        self.parent.settingParams.cpkThreshold = float(self.settingsUI.lineEdit_cpk.text())
        # color
        for group in ["site", "sbin", "hbin"]:
            self.currentColorDict(get=False, group=group)
        
        
    def isTrendChanged(self):
        return not all([getattr(self.originalParams, attr) == getattr(self.parent.settingParams, attr) 
                        for attr in ["showHL_trend", "showLL_trend", "showMed_trend", "showMean_trend"]])
        
        
    def isHistoChanged(self):
        return not all([getattr(self.originalParams, attr) == getattr(self.parent.settingParams, attr) 
                        for attr in ["showHL_histo", "showLL_histo", "showMed_histo", "showMean_histo", 
                                     "showGaus_histo", "showBoxp_histo", "binCount", "showSigma"]])
        
         
    def isTableChanged(self):
        return not all([getattr(self.originalParams, attr) == getattr(self.parent.settingParams, attr) 
                        for attr in ["dataNotation", "dataPrecision", "cpkThreshold"]])


    def isColorChanged(self):
        return not all([getattr(self.originalParams, attr) == getattr(self.parent.settingParams, attr) 
                        for attr in ["siteColor", "sbinColor", "hbinColor"]])
    
    
    def applySettings(self):
        if self.parent:
            # write setting to parent settings
            self.updateSettings()
            refreshTab = False
            refreshTable = False
            refreshCursor = False
            if self.isTrendChanged() and (self.parent.ui.tabControl.currentIndex() == tab.Trend): 
                refreshTab = True
                
            if self.isHistoChanged() and (self.parent.ui.tabControl.currentIndex() == tab.Histo): 
                refreshTab = True
                
            if self.isTableChanged() and (self.parent.ui.tabControl.currentIndex() != tab.Bin): 
                refreshTable = True
                refreshCursor = True
                # if raw data table is active, update as well
                if (self.parent.ui.tabControl.currentIndex() == tab.Info) and (self.parent.ui.infoBox.currentIndex() == 2):
                    refreshTab = True
                    
            if self.isColorChanged():
                refreshTab = True
                refreshTable = True
                
            if refreshTab: self.parent.updateTabContent(forceUpdate=True)
            if refreshTable: self.parent.updateTableContent()
            if refreshCursor: self.parent.updateCursorPrecision()
                
            # need to update orignal params after updating parent settings
            self.originalParams = deepcopy(self.parent.settingParams)
        QtWidgets.QApplication.processEvents()
        self.close()
    
    
    def closeEvent(self, event):
        event.accept()
        
        
    def initColorBtns(self):
        # site color picker
        site_color_group = self.settingsUI.site_groupBox
        site_gridLayout = self.settingsUI.gridLayout_site_color
        for i, siteNum in enumerate([-1]+[i for i in self.parent.dataSrc.keys()]):
            siteName = f"Site {siteNum:<2}" if siteNum != -1 else "All Site"
            cB = colorBtn(parent=site_color_group, name=siteName, num=siteNum)
            row = i//3
            col = i % 3
            site_gridLayout.addWidget(cB, row, col)
            
        # sbin color picker
        sbin_color_group = self.settingsUI.sbin_groupBox
        sbin_gridLayout = self.settingsUI.gridLayout_sbin_color
        for i, sbin in enumerate([i for i in sorted(self.parent.dataInfo.sbinDict.keys())]):
            binName = f"SBIN {sbin:<2}"
            cB = colorBtn(parent=sbin_color_group, name=binName, num=sbin)
            row = i//3
            col = i % 3
            sbin_gridLayout.addWidget(cB, row, col)
            
        # hbin color picker
        hbin_color_group = self.settingsUI.hbin_groupBox
        hbin_gridLayout = self.settingsUI.gridLayout_hbin_color
        for i, hbin in enumerate([i for i in sorted(self.parent.dataInfo.hbinDict.keys())]):
            binName = f"HBIN {hbin:<2}"
            cB = colorBtn(parent=hbin_color_group, name=binName, num=hbin)
            row = i//3
            col = i % 3
            hbin_gridLayout.addWidget(cB, row, col)
                
    
    def showUI(self):
        if self.parent: 
            self.originalParams = deepcopy(self.parent.settingParams)
            self.initWithParentParams()
            currentTab = self.parent.ui.tabControl.currentIndex()
            if currentTab == 1:
                # trend tab
                currentIndex = 0
            elif currentTab == 2:
                # histo tab
                currentIndex = 1
            elif currentTab == 0:
                # info tab
                currentIndex = 2
            else:
                # bin & wafer
                currentIndex = 3
            self.settingsUI.settingBox.setCurrentIndex(currentIndex)

        self.exec_()           
           
           
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication([])
    # test = stdfSettings()
    # w = colorBtn(name="All site", num=1)
    # w.show()
    sys.exit(app.exec_())
    
    
