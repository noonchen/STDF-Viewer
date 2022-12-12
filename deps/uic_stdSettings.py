#
# uic_stdSettings.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: August 11th 2020
# -----
# Last Modified: Mon Dec 12 2022
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



from deps.SharedSrc import *
# pyqt5
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTranslator
from .ui.stdfViewer_settingsUI import Ui_Setting
# pyside2
# from PySide2 import QtWidgets, QtGui
# from PySide2.QtCore import QTranslator
# from .ui.stdfViewer_settingsUI_side2 import Ui_Setting
# pyside6
# from PySide6 import QtWidgets, QtGui
# from PySide6.QtCore import QTranslator
# from .ui.stdfViewer_settingsUI_side6 import Ui_Setting


indexDic_sigma = {0: "",
                  1: "3", 
                  2: "3, 6", 
                  3: "3, 6, 9"}
indexDic_sigma_reverse = {v:k for k, v in indexDic_sigma.items()}

indexDic_notation = {0: "G",
                     1: "F",
                     2: "E"}
indexDic_notation_reverse = {v:k for k, v in indexDic_notation.items()}

indexDic_lang = {0: "English",
                 1: "简体中文"}
indexDic_lang_reverse = {v:k for k, v in indexDic_lang.items()}

indexDic_sortby = {0: "Original",
                   1: "Number",
                   2: "Name"}
indexDic_sortby_reverse = {v:k for k, v in indexDic_sortby.items()}

indexDic_ppqq = {0: "Data Quantiles",
                 1: "Data Percentiles",
                 2: "Normal Quantiles",
                 3: "Normal Percentiles"}
indexDic_ppqq_reverse = {v:k for k, v in indexDic_ppqq.items()}


class colorBtn(QtWidgets.QWidget):
    def __init__(self, parent=None, name="", num=None):
        super().__init__(parent=parent)
        self.name = name
        self.num = num
        self.setObjectName(self.name)
        self.hLayout = QtWidgets.QHBoxLayout(self)
        self.hLayout.setSpacing(5)
        fontsize = 12 if isMac else 10
        squaresize = 25 if isMac else 20
        # label
        self.label = QtWidgets.QLabel(self)
        self.label.setText(self.name)
        self.label.setStyleSheet("font: {0}pt".format(fontsize))
        self.hLayout.addWidget(self.label)
        # color square
        self.square = QtWidgets.QWidget(self)
        self.square.setFixedSize(squaresize, squaresize)
        self.square.setStyleSheet("border:1px solid #000000;")
        self.hLayout.addWidget(self.square)
        self.square.mouseReleaseEvent = self.showPalette
        # spacer to avoid label from leaving button when resizing
        spacerItem = QtWidgets.QSpacerItem(0, 0, 
                                           QtWidgets.QSizePolicy.Policy.Expanding, 
                                           QtWidgets.QSizePolicy.Policy.Expanding)
        self.hLayout.addItem(spacerItem)
        
    def setColor(self, qcolor: QtGui.QColor):
        self.square.setStyleSheet("border:1px solid #000000; background-color:%s;"%str(qcolor.name()))
    
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


class SymbolBtn(QtWidgets.QWidget):
    def __init__(self, parent, name: str, fid: int):
        super().__init__(parent=parent)
        self.name = name
        self.fid = fid
        self.setObjectName(self.name)
        self.hLayout = QtWidgets.QHBoxLayout(self)
        self.hLayout.setSpacing(5)
        # label
        self.label = QtWidgets.QLabel(self)
        self.label.setText(self.name)
        self.label.setStyleSheet("font: {0}pt".format(12 if isMac else 10))
        self.hLayout.addWidget(self.label)
        # combobox
        self.cb = QtWidgets.QComboBox(self)
        self.cb.setStyleSheet("font: {0}pt".format(20 if isMac else 18))
        self.cb.setFixedSize(50, 30)
        self.cb.addItems(symbolChar)
        # self.cb.setStyleSheet("QComboBox::drop-down {border-width: 0px;}\
        #     QComboBox::down-arrow {image: url(noimg); border-width: 0px;}")
        self.hLayout.addWidget(self.cb)
        # spacer to avoid label from leaving button when resizing
        spacerItem = QtWidgets.QSpacerItem(0, 0, 
                                           QtWidgets.QSizePolicy.Policy.Expanding, 
                                           QtWidgets.QSizePolicy.Policy.Expanding)
        self.hLayout.addItem(spacerItem)
        
    def getSymbolName(self) -> str:
        return symbolChar2Name[self.cb.currentText()]
    
    def setSymbolName(self, s: str):
        ind = symbolName.index(s)
        self.cb.setCurrentText(symbolChar[ind])


def isTrendChanged(old, new):
    return not all([getattr(old, attr) == getattr(new, attr) 
                    for attr in ["showHL_trend", "showLL_trend", 
                                 "showHSpec_trend", "showLSpec_trend", 
                                 "showMed_trend", "showMean_trend"]])

def isHistoChanged(old, new):
    return not all([getattr(old, attr) == getattr(new, attr) 
                    for attr in ["showHL_histo", "showLL_histo", 
                                 "showHSpec_histo", "showLSpec_histo", 
                                 "showMed_histo", "showMean_histo",
                                 "showBoxp_histo", "showBoxpOl_histo", 
                                 "showBars_histo", "binCount", "showSigma"]])

def isPPQQChanged(old, new):
    return not all([getattr(old, attr) == getattr(new, attr) 
                    for attr in ["x_ppqq", "y_ppqq"]])

def isGeneralChanged(old, new):
    return not all([getattr(old, attr) == getattr(new, attr) 
                    for attr in ["language", "font", "dataNotation", 
                                 "dataPrecision", "checkCpk", 
                                 "cpkThreshold", "sortTestList", "fileSymbol"]])

def isColorChanged(old, new):
    return not all([getattr(old, attr) == getattr(new, attr) 
                    for attr in ["siteColor", "sbinColor", "hbinColor"]])


class stdfSettings(QtWidgets.QDialog):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.parent = parent
        self.translator = QTranslator(self)
        self.settingsUI = Ui_Setting()
        self.settingsUI.setupUi(self)
        self.settingsUI.Confirm.clicked.connect(self.applySettings)
        self.settingsUI.Cancel.clicked.connect(self.close)
        self.settingsUI.lineEdit_binCount.setValidator(QtGui.QIntValidator(1, 1000, self))
        self.settingsUI.lineEdit_cpk.setValidator(QtGui.QDoubleValidator(self))
        # populate font names
        self.settingsUI.fontComboBox.addItems(getLoadedFontNames())
        # link buttons to stack widget
        self.settingsUI.generalBtn.clicked.connect(lambda: self.settingsUI.stackedWidget.setCurrentIndex(0))
        self.settingsUI.trendBtn.clicked.connect(lambda: self.settingsUI.stackedWidget.setCurrentIndex(1))
        self.settingsUI.histoBtn.clicked.connect(lambda: self.settingsUI.stackedWidget.setCurrentIndex(2))
        self.settingsUI.ppqqBtn.clicked.connect(lambda: self.settingsUI.stackedWidget.setCurrentIndex(3))
        self.settingsUI.colorBtn.clicked.connect(lambda: self.settingsUI.stackedWidget.setCurrentIndex(4))
        # set icon for buttons
        self.settingsUI.generalBtn.setIcon(getIcon("tab_info"))
        self.settingsUI.trendBtn.setIcon(getIcon("tab_trend"))
        self.settingsUI.histoBtn.setIcon(getIcon("tab_hist"))
        self.settingsUI.ppqqBtn.setIcon(getIcon("tab_ppqq"))
        self.settingsUI.colorBtn.setIcon(getIcon("ColorPalette"))
        # hide not implemented functions
        self.settingsUI.ppqqBtn.setHidden(True)
        self.settingsUI.showMean_histo.setHidden(True)
        self.settingsUI.showMedian_histo.setHidden(True)
        self.settingsUI.showBoxp_histo.setHidden(True)
        self.settingsUI.showBpOutlier_histo.setHidden(True)
        self.settingsUI.showBar_histo.setDisabled(True)
        self.settingsUI.sigmaCombobox.setHidden(True)
                
        
    def initWithParentParams(self):
        settings = getSetting()
        # trend
        self.settingsUI.showHL_trend.setChecked(settings.showHL_trend)
        self.settingsUI.showLL_trend.setChecked(settings.showLL_trend)
        self.settingsUI.showHSpec_trend.setChecked(settings.showHSpec_trend)
        self.settingsUI.showLSpec_trend.setChecked(settings.showLSpec_trend)
        self.settingsUI.showMedian_trend.setChecked(settings.showMed_trend)
        self.settingsUI.showMean_trend.setChecked(settings.showMean_trend)
        # histo
        self.settingsUI.showHL_histo.setChecked(settings.showHL_histo)
        self.settingsUI.showLL_histo.setChecked(settings.showLL_histo)
        self.settingsUI.showHSpec_histo.setChecked(settings.showHSpec_histo)
        self.settingsUI.showLSpec_histo.setChecked(settings.showLSpec_histo)
        self.settingsUI.showMedian_histo.setChecked(settings.showMed_histo)
        self.settingsUI.showMean_histo.setChecked(settings.showMean_histo)
        self.settingsUI.showBoxp_histo.setChecked(settings.showBoxp_histo)
        self.settingsUI.showBpOutlier_histo.setChecked(settings.showBoxpOl_histo)
        self.settingsUI.showBar_histo.setChecked(settings.showBars_histo)
        self.settingsUI.lineEdit_binCount.setText(str(settings.binCount))
        self.settingsUI.sigmaCombobox.setCurrentIndex(indexDic_sigma_reverse.get(settings.showSigma, 0))
        # PPQQ
        self.settingsUI.xDataCombobox.setCurrentIndex(indexDic_ppqq_reverse.get(settings.x_ppqq, 2))
        self.settingsUI.yDataCombobox.setCurrentIndex(indexDic_ppqq_reverse.get(settings.y_ppqq, 0))
        # general
        self.settingsUI.langCombobox.setCurrentIndex(indexDic_lang_reverse.get(settings.language, 0))
        self.settingsUI.fontComboBox.setCurrentText(settings.font)
        self.settingsUI.notationCombobox.setCurrentIndex(indexDic_notation_reverse.get(settings.dataNotation, 0))
        self.settingsUI.precisionSlider.setValue(settings.dataPrecision)
        self.settingsUI.checkCpkcomboBox.setCurrentIndex(0 if settings.checkCpk else 1)
        self.settingsUI.lineEdit_cpk.setText(str(settings.cpkThreshold))
        self.settingsUI.sortTestListComboBox.setCurrentIndex(indexDic_sortby_reverse.get(settings.sortTestList, 0))
        # file symbol
        fsLayout = self.settingsUI.gridLayout_file_symbol
        for i in range(fsLayout.count()):
            fsBox: SymbolBtn = fsLayout.itemAt(i).widget()
            fsBox.setSymbolName(settings.fileSymbol.get(i, rSymbol()))
        # color
        for (orig_dict, layout) in [(settings.siteColor, self.settingsUI.gridLayout_site_color),
                                    (settings.sbinColor, self.settingsUI.gridLayout_sbin_color),
                                    (settings.hbinColor, self.settingsUI.gridLayout_hbin_color)]:
            for i in range(layout.count()):
                cB = layout.itemAt(i).widget()
                orig_color = orig_dict.get(cB.num, rHEX())
                cB.setColor(QtGui.QColor(orig_color))
            
    
    def getUserSettings(self) -> SettingParams:
        '''
        Read widgets value and create a new `SettingParams`
        '''
        userSettings = SettingParams()
        # trend
        userSettings.showHL_trend = self.settingsUI.showHL_trend.isChecked()
        userSettings.showLL_trend = self.settingsUI.showLL_trend.isChecked()
        userSettings.showHSpec_trend = self.settingsUI.showHSpec_trend.isChecked()
        userSettings.showLSpec_trend = self.settingsUI.showLSpec_trend.isChecked()
        userSettings.showMed_trend = self.settingsUI.showMedian_trend.isChecked()
        userSettings.showMean_trend = self.settingsUI.showMean_trend.isChecked()
        # histo
        userSettings.showHL_histo = self.settingsUI.showHL_histo.isChecked()
        userSettings.showLL_histo = self.settingsUI.showLL_histo.isChecked()
        userSettings.showHSpec_histo = self.settingsUI.showHSpec_histo.isChecked()
        userSettings.showLSpec_histo = self.settingsUI.showLSpec_histo.isChecked()
        userSettings.showMed_histo = self.settingsUI.showMedian_histo.isChecked()
        userSettings.showMean_histo = self.settingsUI.showMean_histo.isChecked()
        userSettings.showBoxp_histo = self.settingsUI.showBoxp_histo.isChecked()
        userSettings.showBoxpOl_histo = self.settingsUI.showBpOutlier_histo.isChecked()
        userSettings.showBars_histo = self.settingsUI.showBar_histo.isChecked()
        userSettings.binCount = int(self.settingsUI.lineEdit_binCount.text())
        userSettings.showSigma = indexDic_sigma[self.settingsUI.sigmaCombobox.currentIndex()]
        # PPQQ
        userSettings.x_ppqq = self.settingsUI.xDataCombobox.currentText()
        userSettings.y_ppqq = self.settingsUI.yDataCombobox.currentText()
        # General
        userSettings.language = indexDic_lang[self.settingsUI.langCombobox.currentIndex()]
        userSettings.font = self.settingsUI.fontComboBox.currentText()
        userSettings.dataNotation = indexDic_notation[self.settingsUI.notationCombobox.currentIndex()]
        userSettings.dataPrecision = self.settingsUI.precisionSlider.value()
        userSettings.checkCpk = (self.settingsUI.checkCpkcomboBox.currentIndex() == 0)
        userSettings.cpkThreshold = float(self.settingsUI.lineEdit_cpk.text())
        userSettings.sortTestList = indexDic_sortby[self.settingsUI.sortTestListComboBox.currentIndex()]
        # file symbol
        fsLayout = self.settingsUI.gridLayout_file_symbol
        for i in range(fsLayout.count()):
            fsBox = fsLayout.itemAt(i).widget()
            fid = fsBox.fid
            userSettings.fileSymbol[fid] = fsBox.getSymbolName()
        # color
        for (colorDict, layout) in [(userSettings.siteColor, self.settingsUI.gridLayout_site_color), 
                                    (userSettings.sbinColor, self.settingsUI.gridLayout_sbin_color), 
                                    (userSettings.hbinColor, self.settingsUI.gridLayout_hbin_color)]:
            if layout:
                for i in range(layout.count()):
                    cB = layout.itemAt(i).widget()
                    num = cB.num
                    hexColor = cB.getHEXColor()
                    colorDict[num] = hexColor
        
        return userSettings
    
    
    def applySettings(self):
        if self.parent:
            origSettings = getSetting()
            userSettings = self.getUserSettings()
            currentTab = self.parent.ui.tabControl.currentIndex()
            
            refreshTab = False
            refreshTable = False
            refreshList = False
            clearListBG = False
            retranslate = False
            if isTrendChanged(origSettings, userSettings) and (currentTab == tab.Trend): 
                refreshTab = True
            if isHistoChanged(origSettings, userSettings) and (currentTab == tab.Histo): 
                refreshTab = True
            if (origSettings.fileSymbol != userSettings.fileSymbol) and (currentTab in [tab.Trend, tab.PPQQ]):
                refreshTab = True
            if (origSettings.language != userSettings.language or 
                origSettings.font != userSettings.font):
                retranslate = True
            if origSettings.sortTestList != userSettings.sortTestList:
                refreshList = True
            if currentTab != tab.Bin:
                refreshTable = True
                # if cpk threshold changed, clear listView backgrounds
                if (origSettings.cpkThreshold != userSettings.cpkThreshold or 
                    origSettings.checkCpk != userSettings.checkCpk):
                    clearListBG = True
            if isColorChanged(origSettings, userSettings):
                refreshTab = True
                refreshTable = True
                
            # update global settings before updating UI
            updateSetting(**userSettings.__dict__)
            # TODO replace with signals
            if refreshTab: self.parent.updateTabContent()
            if refreshTable: self.parent.updateStatTableContent()
            if refreshList: self.parent.refreshTestList()
            if clearListBG: self.parent.clearTestItemBG()
            if retranslate: self.parent.changeLanguage()
        QtWidgets.QApplication.processEvents()
        self.close()
    
    
    def closeEvent(self, event):
        event.accept()
        
        
    def removeColorBtns(self):
        for layout in [self.settingsUI.gridLayout_site_color,
                       self.settingsUI.gridLayout_sbin_color,
                       self.settingsUI.gridLayout_hbin_color]:
            cBList = []
            for i in range(layout.count()):
                cB = layout.itemAt(i).widget()
                # layout.removeWidget(cB)
                cBList.append(cB)
            deleteWidget(cBList)
    
    
    def initColorBtns(self, availableSites: set, SBIN_dict: dict, HBIN_dict: dict):
        # site color picker
        site_color_group = self.settingsUI.site_groupBox
        site_gridLayout = self.settingsUI.gridLayout_site_color
        for i, siteNum in enumerate([-1]+[i for i in availableSites]):
            siteName = f"Site {siteNum:<2}" if siteNum != -1 else "All Site"
            cB = colorBtn(parent=site_color_group, name=siteName, num=siteNum)
            row = i//3
            col = i % 3
            site_gridLayout.addWidget(cB, row, col)
            
        # sbin color picker
        sbin_color_group = self.settingsUI.sbin_groupBox
        sbin_gridLayout = self.settingsUI.gridLayout_sbin_color
        for i, sbin in enumerate([i for i in sorted(SBIN_dict.keys())]):
            binName = f"SBIN {sbin:<2}"
            cB = colorBtn(parent=sbin_color_group, name=binName, num=sbin)
            row = i//3
            col = i % 3
            sbin_gridLayout.addWidget(cB, row, col)
            
        # hbin color picker
        hbin_color_group = self.settingsUI.hbin_groupBox
        hbin_gridLayout = self.settingsUI.gridLayout_hbin_color
        for i, hbin in enumerate([i for i in sorted(HBIN_dict.keys())]):
            binName = f"HBIN {hbin:<2}"
            cB = colorBtn(parent=hbin_color_group, name=binName, num=hbin)
            row = i//3
            col = i % 3
            hbin_gridLayout.addWidget(cB, row, col)
    
    
    def removeSymbolBtns(self):
        layout = self.settingsUI.gridLayout_file_symbol
        fsList = []
        for i in range(layout.count()):
            fsBox = layout.itemAt(i).widget()
            # layout.removeWidget(fsBox)
            fsList.append(fsBox)
        deleteWidget(fsList)
    
    
    def initSymbolBtns(self, num_files: int):
        symbolGroup = self.settingsUI.symbol_groupBox
        symbolLayout = self.settingsUI.gridLayout_file_symbol
        for i in range(num_files):
            name = f"File {i:<2}"
            cB = SymbolBtn(parent=symbolGroup, name=name, fid=i)
            row = i//3
            col = i % 3
            symbolLayout.addWidget(cB, row, col)
    
    
    def refreshFontList(self):
        self.settingsUI.fontComboBox.clear()
        self.settingsUI.fontComboBox.addItems(getLoadedFontNames())
    
    
    def showUI(self):
        if self.parent: 
            self.initWithParentParams()
            currentTab = self.parent.ui.tabControl.currentIndex()
            if currentTab == tab.Info: 
                self.settingsUI.generalBtn.click()
                
            elif currentTab == tab.Trend: 
                self.settingsUI.trendBtn.click()
                
            elif currentTab == tab.Histo: 
                self.settingsUI.histoBtn.click()
                
            else: 
                self.settingsUI.colorBtn.click()

        self.exec_()
           
           
