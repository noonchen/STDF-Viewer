#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
# -----
# Last Modified: Fri Nov 25 2022
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



import io, os, sys, gc, traceback, toml, atexit
import json, urllib.request as rq
import platform, logging
import numpy as np
from itertools import product
from fontTools import ttLib
from base64 import b64decode
from deps.SharedSrc import tab, REC
import deps.SharedSrc as ss
from deps.ui.ImgSrc_svg import ImgDict
from deps.ui.transSrc import transDict
from deps.DataInterface import DataInterface
from deps.customizedQtClass import (StyleDelegateForTable_List, 
                                    DutSortFilter, 
                                    ColorSqlQueryModel, 
                                    DatalogSqlQueryModel, 
                                    TestDataTableModel, 
                                    TestStatisticTableModel, 
                                    BinWaferTableModel)
from deps.ChartWidgets import (TrendChart)
from deps.uic_stdLoader import stdfLoader
from deps.uic_stdFailMarker import FailMarker
from deps.uic_stdExporter import stdfExporter
from deps.uic_stdSettings import stdfSettings, SettingParams
from deps.uic_stdDutData import DutDataDisplayer
from deps.uic_stdDebug import stdDebugPanel

# pyqt5
from deps.ui.stdfViewer_MainWindows import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets, QtGui, QtSql
from PyQt5.QtWidgets import (QApplication, QFileDialog, 
                             QAbstractItemView, QMessageBox, QHeaderView)
from PyQt5.QtCore import (Qt, QTranslator, 
                          pyqtSignal as Signal, 
                          pyqtSlot as Slot)
# pyside2
# from deps.ui.stdfViewer_MainWindows_side2 import Ui_MainWindow
# from PySide2 import QtCore, QtWidgets, QtGui
# from PySide2.QtWidgets import QApplication, QFileDialog, QAbstractItemView, QMessageBox
# from PySide2.QtCore import Qt, QTranslator, Signal, Slot
# pyside6
# from deps.ui.stdfViewer_MainWindows_side6 import Ui_MainWindow
# from PySide6 import QtCore, QtWidgets, QtGui
# from PySide6.QtWidgets import QApplication, QFileDialog, QAbstractItemView, QMessageBox
# from PySide6.QtCore import Qt, QTranslator, Signal, Slot

# high dpi support
QApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
Version = "V4.0.0"
isMac = platform.system() == 'Darwin'
    
# save config path to sys
rootFolder = os.path.dirname(sys.argv[0])
setattr(sys, "rootFolder", rootFolder)
setattr(sys, "CONFIG_PATH", os.path.join(rootFolder, "STDF-Viewer.config"))

# logger
ss.init_logger(rootFolder)
logger = logging.getLogger("STDF-Viewer")


class FontNames:
    def __init__(self):
        self.Chinese = "Microsoft Yahei"
        self.English = "Tahoma"


class signals4MainUI(QtCore.QObject):
    dataInterfaceSignal = Signal(object)  # get `DataInterface` from loader
    statusSignal = Signal(str, bool, bool, bool)   # status bar


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self, defaultFontNames: FontNames):
        super(MyWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        sys.excepthook = self.onException
        # data_interface for processing requests by GUI 
        # and reading data from database
        self.data_interface = None
        # database for dut summary and GDR/DTR table
        self.db_dut = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        # used for detecting tab changes
        self.preTab = None             
        # used for detecting selection changes
        self.selectionTracker = {}
        # dict to store site/head checkbox objects
        self.site_cb_dict = {}
        self.head_cb_dict = {}
        self.init_SettingParams()
        self.translatorUI = QTranslator(self)
        self.translatorCode = QTranslator(self)
        self.defaultFontNames = defaultFontNames
        self.imageFont = self.defaultFontNames.English
        # init and connect signals
        self.signals = signals4MainUI()
        self.signals.dataInterfaceSignal.connect(self.updateData)
        self.signals.statusSignal.connect(self.updateStatus)
        # sub windows
        self.loader = stdfLoader(self.signals, self)
        self.failmarker = FailMarker(self)
        self.exporter = stdfExporter(self)
        self.settingUI = stdfSettings(self)
        self.dutDataDisplayer = DutDataDisplayer(self)
        self.debugPanel = stdDebugPanel(self)
        # update icons for actions and widgets
        self.updateIcons()
        self.init_TestList()
        self.init_DataTable()
        self.init_Head_SiteCheckbox()
        # enable drop file
        self.enableDragDrop()
        # init actions
        self.ui.actionOpen.triggered.connect(self.openNewFile)
        self.ui.actionFailMarker.triggered.connect(self.onFailMarker)
        self.ui.actionExport.triggered.connect(self.onExportReport)
        self.ui.actionSettings.triggered.connect(self.onSettings)
        self.ui.actionAbout.triggered.connect(self.onAbout)
        self.ui.actionReadDutData_DS.triggered.connect(self.onReadDutData_DS)
        self.ui.actionReadDutData_TS.triggered.connect(self.onReadDutData_TS)
        # init search-related UI
        self.ui.SearchBox.textChanged.connect(self.proxyModel_list.setFilterWildcard)
        self.ui.ClearButton.clicked.connect(self.clearSearchBox)
        # manage tab layout
        self.tab_dict = {tab.Trend: {"scroll": self.ui.scrollArea_trend, "layout": self.ui.verticalLayout_trend},
                         tab.Histo: {"scroll": self.ui.scrollArea_histo, "layout": self.ui.verticalLayout_histo},
                         tab.Bin: {"scroll": self.ui.scrollArea_bin, "layout": self.ui.verticalLayout_bin},
                         tab.Wafer: {"scroll": self.ui.scrollArea_wafer, "layout": self.ui.verticalLayout_wafer}}
        # init callback for UI component
        self.ui.tabControl.currentChanged.connect(self.onSelect)
        self.ui.infoBox.currentChanged.connect(self.updateTestDataTable)
        # add a toolbar action at the right side
        self.spaceWidgetTB = QtWidgets.QWidget()
        self.spaceWidgetTB.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                                               QtWidgets.QSizePolicy.Policy.Expanding))
        self.ui.toolBar.addWidget(self.spaceWidgetTB)
        self.ui.toolBar.addAction(self.ui.actionAbout)
        # disable wafer tab in default
        self.ui.tabControl.setTabEnabled(4, False)
        # clean up before exiting
        atexit.register(self.onExit)
        # set language after initing subwindow & reading config
        self.changeLanguage()
        
        
    def checkNewVersion(self):
        try:
            res = rq.urlopen("https://api.github.com/repos/noonchen/STDF-Viewer/releases/latest")
            resDict = json.loads(res.read())
            latestTag = resDict["tag_name"]
            changeList = resDict["body"]
            releaseLink = resDict["html_url"]
            
            if latestTag > Version:
                # show dialog for updating
                msgBox = QMessageBox(self)
                msgBox.setWindowFlag(Qt.WindowType.FramelessWindowHint)
                msgBox.setTextFormat(Qt.TextFormat.RichText)
                msgBox.setText("<span font-size:20px'>{0}&nbsp;&nbsp;&nbsp;&nbsp;<a href='{2}'>{1}</a></span>".format(self.tr("{0} is available!").format(latestTag),
                                                                                                                      self.tr("→Go to download page←"),
                                                                                                                      releaseLink))
                msgBox.setInformativeText(self.tr("Change List:") + "\n\n" + changeList)
                msgBox.addButton(self.tr("Maybe later"), QMessageBox.ButtonRole.NoRole)
                msgBox.exec_()
            else:
                msgBox = QMessageBox(self)
                msgBox.setWindowFlag(Qt.WindowType.FramelessWindowHint)
                msgBox.setTextFormat(Qt.TextFormat.RichText)
                msgBox.setText(self.tr("You're using the latest version."))
                msgBox.exec_()
            
        except Exception as e:
                # tell user cannot connect to the internet
                msgBox = QMessageBox(self)
                msgBox.setWindowFlag(Qt.WindowType.FramelessWindowHint)
                msgBox.setText(self.tr("Cannot connect to Github"))
                msgBox.setInformativeText(repr(e))
                msgBox.exec_()
        
    
    def showDebugPanel(self):
        self.debugPanel.showUI()
    
    
    def changeLanguage(self):
        _app = QApplication.instance()
        # load language files based on the setting
        curLang = self.settingParams.language
        if curLang == "English":
            self.imageFont = self.defaultFontNames.English
            self.translatorUI.loadFromData(transDict["English"])
            self.translatorCode.loadFromData(transDict["English"])
            self.loader.translator.loadFromData(transDict["English"])
            self.failmarker.translator.loadFromData(transDict["English"])
            self.exporter.translatorUI.loadFromData(transDict["English"])
            self.exporter.translatorCode.loadFromData(transDict["English"])
            self.settingUI.translator.loadFromData(transDict["English"])
            self.dutDataDisplayer.translator.loadFromData(transDict["English"])
            self.debugPanel.translator.loadFromData(transDict["English"])
            self.debugPanel.translator_code.loadFromData(transDict["English"])
            
        elif curLang == "简体中文":
            self.imageFont = self.defaultFontNames.Chinese
            self.translatorUI.loadFromData(transDict["MainUI_zh_CN"])
            self.translatorCode.loadFromData(transDict["MainCode_zh_CN"])
            self.loader.translator.loadFromData(transDict["loadingUI_zh_CN"])
            self.failmarker.translator.loadFromData(transDict["failmarkerCode_zh_CN"])
            self.exporter.translatorUI.loadFromData(transDict["exportUI_zh_CN"])
            self.exporter.translatorCode.loadFromData(transDict["exportCode_zh_CN"])
            self.settingUI.translator.loadFromData(transDict["settingUI_zh_CN"])
            self.dutDataDisplayer.translator.loadFromData(transDict["dutDataUI_zh_CN"])
            self.debugPanel.translator.loadFromData(transDict["debugUI_zh_CN"])
            self.debugPanel.translator_code.loadFromData(transDict["debugCode_zh_CN"])
            
        newfont = QtGui.QFont(self.imageFont)
        _app.setFont(newfont)
        [w.setFont(newfont) if not isinstance(w, QtWidgets.QListView) else None for w in QApplication.allWidgets()]
        # actions is not listed in qapp all widgets, iterate separately
        [w.setFont(newfont) for w in self.ui.toolBar.actions()]
        # retranslate UIs
        # mainUI
        _app.installTranslator(self.translatorUI)
        self.ui.retranslateUi(self)
        # loader
        _app.installTranslator(self.loader.translator)
        self.loader.loaderUI.retranslateUi(self.loader)
        # exporter
        _app.installTranslator(self.exporter.translatorUI)
        self.exporter.exportUI.retranslateUi(self.exporter)
        # settingUI
        _app.installTranslator(self.settingUI.translator)
        self.settingUI.settingsUI.retranslateUi(self.settingUI)
        # dutTableUI
        _app.installTranslator(self.dutDataDisplayer.translator)
        self.dutDataDisplayer.UI.retranslateUi(self.dutDataDisplayer)
        # debugUI
        _app.installTranslator(self.debugPanel.translator)
        self.debugPanel.dbgUI.retranslateUi(self.debugPanel)
        # failmarker
        _app.installTranslator(self.failmarker.translator)
        # exporterCode
        _app.installTranslator(self.exporter.translatorCode)
        # mainCode
        _app.installTranslator(self.translatorCode)
        # debugCode
        _app.installTranslator(self.debugPanel.translator_code)
        # update flag dictionarys
        ss.translate_const_dicts(self.tr)
        # need to rewrite file info table after changing language
        self.updateFileHeader()        
    
    
    def dumpConfigFile(self):
        # save data to toml config
        configData = {"General": {},
                      "Trend Plot": {},
                      "Histo Plot": {},
                      "Color Setting": {}}
        configName = dict(sys.CONFIG_NAME)
        for k, v in self.settingParams.__dict__.items():
            if k in ["language", "recentFolder", "dataNotation", "dataPrecision", "checkCpk", "cpkThreshold", "sortTestList"]:
                # General
                configData["General"][configName[k]] = v
            elif k in ["showHL_trend", "showLL_trend", "showHSpec_trend", "showLSpec_trend", "showMed_trend", "showMean_trend"]:
                # Trend
                configData["Trend Plot"][configName[k]] = v
            elif k in ["showHL_histo", "showLL_histo", "showHSpec_histo", "showLSpec_histo", "showMed_histo", "showMean_histo", "showGaus_histo", "showBoxp_histo", "binCount", "showSigma"]:
                # Histo
                configData["Histo Plot"][configName[k]] = v

            elif k in ["siteColor", "sbinColor", "hbinColor"]:
                # Color
                # change Int key to string, since toml only support string keys
                v = dict([(str(intKey), color) for intKey, color in v.items()])
                configData["Color Setting"][configName[k]] = v

        with open(sys.CONFIG_PATH, "w+", encoding="utf-8") as fd:
            toml.dump(configData, fd)
    
    
    def updateRecentFolder(self, filepath: str):
        dirpath = os.path.dirname(filepath)
        # update settings
        self.settingParams.recentFolder = dirpath
        self.dumpConfigFile()
    

    def openNewFile(self, files: list[str]):
        if not files:
            files, _ = QFileDialog.getOpenFileNames(self, 
                                                  caption=self.tr("Select a STD File To Open"), 
                                                  directory=self.settingParams.recentFolder,
                                                  filter=self.tr("All Supported Files (*.std* *.std*.gz *.std*.bz2 *.std*.zip);;STDF (*.std *.stdf);;Compressed STDF (*.std*.gz *.std*.bz2 *.std*.zip);;All Files (*.*)"),)
        else:
            files = [f for f in map(os.path.normpath, files) if os.path.isfile(f)]
            
        if files:
            # store folder path
            self.updateRecentFolder(files[0])
            # self.callFileLoader([files])
            self.callFileLoader([[f] for f in files])
              
    
    def onFailMarker(self):
        if self.data_interface is not None:
            self.failmarker.start()
        else:
            # no data is found, show a warning dialog
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No file is loaded."))
                
    
    def onExportReport(self):
        if self.data_interface is not None:
            self.exporter.showUI()
            # we have to de-select test_num(s) after exporting
            # the selected test nums may not be prepared anymore
            self.ui.TestList.clearSelection()
        else:
            # no data is found, show a warning dialog
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No file is loaded."))
    
    
    def onSettings(self):
        self.settingUI.showUI()
    
    
    def onAbout(self):
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(self.tr("About"))
        msgBox.setTextFormat(Qt.TextFormat.RichText)
        msgBox.setText("<span style='color:#930DF2;font-size:20px'>STDF Viewer</span><br>{0}: {1}<br>{2}: noonchen<br>{3}: chennoon233@foxmail.com<br>".format(self.tr("Version"), 
                                                                                                                                                               Version, 
                                                                                                                                                               self.tr("Author"), 
                                                                                                                                                               self.tr("Email")))
        msgBox.setInformativeText("{0}:\
            <br><a href='https://github.com/noonchen/STDF_Viewer'>noonchen @ STDF_Viewer</a>\
            <br>\
            <br><span style='font-size:8px'>{1}</span>".format(self.tr("For instructions, please refer to the ReadMe in the repo"), 
                                                               self.tr("Disclaimer: This free app is licensed under GPL 3.0, you may use it free of charge but WITHOUT ANY WARRANTY, it might contians bugs so use it at your own risk.")))
        appIcon = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Icon"], format = 'SVG'))
        appIcon.setDevicePixelRatio(2.0)
        msgBox.setIconPixmap(appIcon)
        dbgBtn = msgBox.addButton(self.tr("Debug"), QMessageBox.ButtonRole.ResetRole)   # leftmost
        ckupdateBtn = msgBox.addButton(self.tr("Check For Updates"), QMessageBox.ButtonRole.ApplyRole)   # middle
        msgBox.addButton(self.tr("OK"), QMessageBox.ButtonRole.NoRole)   # rightmost
        msgBox.exec_()
        if msgBox.clickedButton() == dbgBtn:
            self.showDebugPanel()
        elif msgBox.clickedButton() == ckupdateBtn:
            self.checkNewVersion()
        else:
            msgBox.close()
        
        
    def onExit(self):
        '''
        Clean up before closing app
        '''
        self.db_dut.close()
        if self.data_interface:
            self.data_interface.close()
        # clean generated database
        dbFolder = os.path.join(sys.rootFolder, "logs")
        for f in os.listdir(dbFolder):
            if f.endswith(".db"):
                try:
                    os.remove(os.path.join(dbFolder, f))
                except:
                    pass
    
    
    def getDataInterface(self) -> DataInterface:
        return self.data_interface
    
    
    def showDutDataTable(self, selectedDutIndexes: list):
        # always update style in case user changed them in the setting
        self.dutDataDisplayer.setTextFont(QtGui.QFont(self.imageFont, 13 if isMac else 10))
        self.dutDataDisplayer.setFloatFormat("%%.%d%s" % (self.settingParams.dataPrecision, 
                                                          self.settingParams.dataNotation))
        self.dutDataDisplayer.setContent(self.data_interface.getDutDataDisplayerContent(selectedDutIndexes))
        self.dutDataDisplayer.showUI()
        
    
    def onReadDutData_DS(self):
        # context menu callback for DUT summary
        selectedRows = self.ui.dutInfoTable.selectionModel().selectedRows()
        if selectedRows:
            # since we used proxy model in DUT summary, the selectedRows is from proxy model
            # it should be converted back to source model rows first
            getSourceRow = lambda pIndex: self.proxyModel_tmodel_dut.mapToSource(pIndex).row()
            selectedDutIndex = []
            for r in selectedRows:
                srcRow = getSourceRow(r)
                dutIndex = self.tmodel_dut.data( self.tmodel_dut.index(srcRow, 0), Qt.ItemDataRole.DisplayRole )
                fid = self.tmodel_dut.data( self.tmodel_dut.index(srcRow, 1), Qt.ItemDataRole.DisplayRole )
                selectedDutIndex.append( (fid, dutIndex) )
            
            self.showDutDataTable(selectedDutIndex)


    def onReadDutData_TS(self):
        # context menu callback for Test summary
        selectedRows = self.ui.rawDataTable.selectionModel().selectedIndexes()
        if selectedRows:
            # parse dut index from row header
            vhmodel = self.ui.rawDataTable.verticalHeader().model()
            selectedDutIndex = []
            for r in selectedRows:
                hRow = r.row()
                label: str = vhmodel.headerData(hRow, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole)
                fStr, dutStr = label.split(" ")
                dutIndex = (int(fStr.strip("File")), int(dutStr.strip("#")))
                if dutIndex not in selectedDutIndex:
                    selectedDutIndex.append(dutIndex)
            
            if selectedDutIndex:
                self.showDutDataTable(selectedDutIndex)
            else:
                QMessageBox.information(None, self.tr("No DUTs selected"), self.tr("You need to select DUT row(s) first"), buttons=QMessageBox.Ok)
      
    
    def enableDragDrop(self):
        for obj in [self.ui.TestList, self.ui.tabControl, self.ui.dataTable]:
            obj.setAcceptDrops(True)
            obj.installEventFilter(self)

    
    def updateIcons(self):
        self.ui.actionOpen.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Open"], format = 'PNG'))))
        self.ui.actionFailMarker.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["FailMarker"], format = 'SVG'))))
        self.ui.actionExport.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Export"], format = 'SVG'))))
        self.ui.actionSettings.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Settings"], format = 'SVG'))))
        self.ui.actionAbout.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["About"], format = 'SVG'))))
        self.ui.toolBar.setIconSize(QtCore.QSize(20, 20))
        
        self.ui.tabControl.setTabIcon(tab.Info, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_info"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Trend, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_trend"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Histo, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_histo"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Bin, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_bin"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Wafer, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(b64decode(ImgDict["tab_wafer"]), format = 'PNG'))))
    
    
    def init_TestList(self):
        # init model for ListView
        self.sim_list = QtGui.QStandardItemModel()
        self.proxyModel_list = QtCore.QSortFilterProxyModel()
        self.proxyModel_list.setSourceModel(self.sim_list)
        self.proxyModel_list.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.TestList.setModel(self.proxyModel_list)
        self.ui.TestList.setItemDelegate(StyleDelegateForTable_List(self.ui.TestList))
        
        self.sim_list_wafer = QtGui.QStandardItemModel()
        self.proxyModel_list_wafer = QtCore.QSortFilterProxyModel()
        self.proxyModel_list_wafer.setSourceModel(self.sim_list_wafer)
        self.proxyModel_list_wafer.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.WaferList.setModel(self.proxyModel_list_wafer)        
        self.ui.WaferList.setItemDelegate(StyleDelegateForTable_List(self.ui.WaferList))
        # enable multi selection
        self.ui.TestList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.TestList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.ui.WaferList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.WaferList.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)        
        # get select model and connect func to change event
        self.selModel = self.ui.TestList.selectionModel()
        self.selModel.selectionChanged.connect(self.onSelect)
        
        self.selModel_wafer = self.ui.WaferList.selectionModel()
        self.selModel_wafer.selectionChanged.connect(self.onSelect)        
        
        
    def init_DataTable(self):
        # statistic table
        self.tmodel = TestStatisticTableModel()
        self.bwmodel = BinWaferTableModel()
        self.ui.dataTable.setModel(self.tmodel)
        self.ui.dataTable.setItemDelegate(StyleDelegateForTable_List(self.ui.dataTable))
        # datalog info table
        self.tmodel_datalog = DatalogSqlQueryModel(self, 13 if isMac else 10)
        self.ui.datalogTable.setModel(self.tmodel_datalog)
        self.ui.datalogTable.setItemDelegate(StyleDelegateForTable_List(self.ui.datalogTable))
        # test data table
        self.tmodel_data = TestDataTableModel()
        self.ui.rawDataTable.setModel(self.tmodel_data)
        self.ui.rawDataTable.setItemDelegate(StyleDelegateForTable_List(self.ui.rawDataTable))
        self.ui.rawDataTable.addAction(self.ui.actionReadDutData_TS)   # add context menu for reading dut data
        # dut summary table
        self.tmodel_dut = ColorSqlQueryModel(self)
        self.proxyModel_tmodel_dut = DutSortFilter()
        self.proxyModel_tmodel_dut.setSourceModel(self.tmodel_dut)
        self.ui.dutInfoTable.setSortingEnabled(True)
        self.ui.dutInfoTable.setModel(self.proxyModel_tmodel_dut)
        self.ui.dutInfoTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)     # select row only
        self.ui.dutInfoTable.setItemDelegate(StyleDelegateForTable_List(self.ui.dutInfoTable))
        self.ui.dutInfoTable.addAction(self.ui.actionReadDutData_DS)   # add context menu for reading dut data
        # file header table
        self.tmodel_info = QtGui.QStandardItemModel()
        self.ui.fileInfoTable.setModel(self.tmodel_info)
        self.ui.fileInfoTable.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.ui.fileInfoTable.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        # self.ui.fileInfoTable.setItemDelegate(StyleDelegateForTable_List(self.ui.fileInfoTable))
        # smooth scrolling
        self.ui.datalogTable.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.datalogTable.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.dataTable.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.dataTable.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.rawDataTable.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.rawDataTable.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.dutInfoTable.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui.dutInfoTable.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)        
        self.ui.fileInfoTable.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
                            
    def init_Head_SiteCheckbox(self):
        # bind functions to all checkboxes
        self.ui.All.clicked['bool'].connect(self.onSiteChecked)

        for cb in self.site_cb_dict.values():
            cb.clicked['bool'].connect(self.onSiteChecked)
        for cb in self.head_cb_dict.values():
            cb.clicked['bool'].connect(self.onSiteChecked)
            
        # bind functions to check/uncheck all buttons
        self.ui.checkAll.clicked.connect(lambda: self.toggleSite(True))
        self.ui.cancelAll.clicked.connect(lambda: self.toggleSite(False))
        
        
    def init_SettingParams(self):
        """
        Read config file if exist, else use default params & file data (for bin color init)
        """
        # write default setting params
        self.settingParams = SettingParams()
        # init bin color by bin info
        if isinstance(self.data_interface, DataInterface):
            for (binColorDict, bin_info) in [(self.settingParams.sbinColor, self.data_interface.SBIN_dict), 
                                            (self.settingParams.hbinColor, self.data_interface.HBIN_dict)]:
                for bin in bin_info.keys():
                    binType = bin_info[bin]["BIN_PF"]   # P, F or Unknown
                    color = "#00CC00" if binType == "P" else ("#CC0000" if binType == "F" else "#FE7B00")
                    binColorDict[bin] = color
                    
        # if config file is found, update setting params
        try:
            configData = toml.load(sys.CONFIG_PATH)
            configString = dict([(v, k) for (k, v) in sys.CONFIG_NAME])
            for sec, secDict in configData.items():
                if sec == "Color Setting":
                    # convert string key (site/sbin/hbin) to int
                    for humanString, colorDict in secDict.items():
                        if humanString in configString:
                            attr = configString[humanString]    # e.g. siteColor
                            oldColorDict = getattr(self.settingParams, attr)
                            for numString, hexColor in colorDict.items():
                                try:
                                    num = int(numString)
                                except ValueError:
                                    continue        # skip the invalid site or bin
                                if ss.isHexColor(hexColor): 
                                    oldColorDict[num] = hexColor
                else:
                    for humanString, param in secDict.items():
                        if humanString in configString:
                            attr = configString[humanString]    # e.g. showHL_trend
                            if type(param) == type(getattr(self.settingParams, attr)):
                                setattr(self.settingParams, attr, param)
        except (FileNotFoundError, TypeError, toml.TomlDecodeError):
            # any error occurs in config file reading, simply ignore
            pass
            
        
    def updateModelContent(self, model, newList):
        # clear first
        model.clear()
        
        for data in newList:
            model.appendRow(QtGui.QStandardItem(data))


    def updateFileHeader(self):
        if isinstance(self.data_interface, DataInterface):
            # clear old info
            self.tmodel_info.removeRows(0, self.tmodel_info.rowCount())
            
            horizontalHeader = self.ui.fileInfoTable.horizontalHeader()
            verticalHeader = self.ui.fileInfoTable.verticalHeader()
            horizontalHeader.setVisible(False)
            verticalHeader.setVisible(False)
                
            for tmpRow in self.data_interface.getFileMetaData():
                # translate the first element, which is the field names
                qitemRow = [QtGui.QStandardItem(self.tr(ele) if i == 0 else ele) for i, ele in enumerate(tmpRow)]
                if self.settingParams.language != "English":
                    # fix weird font when switch to chinese-s
                    qfont = QtGui.QFont(self.imageFont)
                    [qele.setData(qfont, Qt.ItemDataRole.FontRole) for qele in qitemRow]
                self.tmodel_info.appendRow(qitemRow)
            
            # horizontalHeader.resizeSection(0, 250)
            
            for column in range(0, horizontalHeader.count()):
                horizontalHeader.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
                # horizontalHeader.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
            
            # resize to content to show all texts, then add additional height to each row
            for row in range(self.tmodel_info.rowCount()):
                verticalHeader.setSectionResizeMode(row, QHeaderView.ResizeMode.ResizeToContents)
                newHeight = verticalHeader.sectionSize(row) + 20
                verticalHeader.setSectionResizeMode(row, QHeaderView.ResizeMode.Fixed)
                verticalHeader.resizeSection(row, newHeight)
    
    
    def updateDutSummaryTable(self):
        header = self.ui.dutInfoTable.horizontalHeader()
        header.setVisible(True)
        
        self.tmodel_dut.setQuery(QtSql.QSqlQuery(ss.DUT_SUMMARY_QUERY, self.db_dut))
        
        for column in range(1, header.count()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        
        # always hide dut index column
        self.ui.dutInfoTable.hideColumn(0)
        # hide file id column if 1 file is opened
        if self.data_interface.num_files <= 1:
            self.ui.dutInfoTable.hideColumn(1)
        else:
            self.ui.dutInfoTable.showColumn(1)
        
        
    def updateGDR_DTR_Table(self):        
        header = self.ui.datalogTable.horizontalHeader()
        header.setVisible(True)
        
        self.tmodel_datalog.setQuery(QtSql.QSqlQuery(ss.DATALOG_QUERY, self.db_dut))
                    
        for column in [2, 3]:
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.ui.datalogTable.resizeRowsToContents()
        
        # hide file id column if 1 file is opened
        if self.data_interface.num_files <= 1:
            self.ui.datalogTable.hideColumn(0)
        else:
            self.ui.datalogTable.showColumn(0)
        
        
    def clearSearchBox(self):
        self.ui.SearchBox.clear()


    def toggleSite(self, on=True):
        self.ui.All.setChecked(on)
        for siteNum, cb in self.site_cb_dict.items():
            cb.setChecked(on)
        self.onSiteChecked()
                
                
    def getCheckedHeads(self) -> list:
        checkedHeads = []
        
        for head_num, cb in self.head_cb_dict.items():
            if cb.isChecked():
                checkedHeads.append(head_num)
                
        return sorted(checkedHeads)
    
    
    def getCheckedSites(self) -> list:
        checkedSites = []
        
        if self.ui.All.isChecked():
            # site number of All == -1
            checkedSites.append(-1)
        
        for site_num, cb in self.site_cb_dict.items():
            if cb.isChecked():
                checkedSites.append(site_num)
                
        return sorted(checkedSites)
                    
    
    def getSelectedTests(self) -> list:
        """return list of tuple(test number, pmr, test name), for non-MPR, pmr is set to 0"""
        selectedIndex = None
        testList = []
        
        if self.ui.tabControl.currentIndex() == tab.Wafer:
            inWaferTab = True
            selectedIndex = self.selModel_wafer.selection().indexes()
        else:
            inWaferTab = False
            selectedIndex = self.selModel.selection().indexes()
        
        if selectedIndex:
            for ind in selectedIndex:
                tnTuple = ss.parseTestString(ind.data(), inWaferTab)
                testList.append(tnTuple)
            testList.sort()
        
        return testList
    
    
    def onSelect(self):
        '''
        This func is called when events occurred in tab, site selection, test selection and wafer selection 
        '''
        currentTab = self.ui.tabControl.currentIndex()
        # switch test/wafer selection panel when tab changed
        if currentTab == tab.Wafer:
            self.ui.Selection_stackedWidget.setCurrentIndex(1)
        else:
            self.ui.Selection_stackedWidget.setCurrentIndex(0)
        
        if currentTab == tab.Bin:
            self.ui.TestList.setDisabled(True)
            self.ui.SearchBox.setDisabled(True)
            self.ui.ClearButton.setDisabled(True)
        else:
            self.ui.TestList.setDisabled(False)
            self.ui.SearchBox.setDisabled(False)
            self.ui.ClearButton.setDisabled(False)
        
        if self.data_interface:
            selHeads = set(self.getCheckedHeads())
            selSites = set(self.getCheckedSites())
            selTests = set(self.getSelectedTests())

            tabChanged = currentTab != self.preTab
            (preHeads, preSites, preTests) = self.selectionTracker.setdefault(currentTab, 
                                                                           (None, None, None))
            if (preHeads != selHeads or
                preSites != selSites or
                preTests != selTests):
                # if any changes, update current tab
                updateTab = True
                updateStat = True
            else:
                updateTab = False
                updateStat = False
            
            # if tab changed, must update 
            # statistic table
            updateStat = updateStat or tabChanged
                    
            if updateStat:
                self.updateStatTableContent()   # update statistic table
            if updateTab:
                self.updateTabContent()         # update tab
            
            self.preTab = currentTab
            # always update pre selection at last
            self.selectionTracker[currentTab] = (selHeads, selSites, selTests)
    
    
    def onSiteChecked(self):
        # call onSelect if there's item selected in listView
        
        # it is safe to call onSelect directly without any items in listView
        # the inner function will detect the items and will skip if there is none
        self.onSelect()
    
    
    def isTestFail(self, selected_string: str) -> str:
        testTuple = ss.parseTestString(selected_string, False)
        testPass = self.data_interface.checkTestPassFail(testTuple)
        
        if testPass:
            # if user do not need to check Cpk, return to caller
            if not self.settingParams.checkCpk:
                return "Pass"
        else:
            return "Fail"
        
        # check if cpk is lower than the threshold
        cpkList = self.data_interface.getTestCpkList(testTuple)
        for cpk in cpkList:
            if not np.isnan(cpk):
                # check cpk only if it's valid
                if cpk < self.settingParams.cpkThreshold:
                    return "cpkFail"
            
        return "Pass"
        
        
    def clearTestItemBG(self):
        # reset test item background color when cpk threshold is reset
        for i in range(self.sim_list.rowCount()):
            qitem = self.sim_list.item(i)
            qitem.setData(None, Qt.ItemDataRole.ForegroundRole)
            qitem.setData(None, Qt.ItemDataRole.BackgroundRole)
                        
                       
    def refreshTestList(self):
        if self.data_interface is None:
            return
        
        if self.settingParams.sortTestList == "Number":
            self.updateModelContent(self.sim_list, sorted(self.completeTestList, key=lambda x: ss.parseTestString(x)))
        elif self.settingParams.sortTestList == "Name":
            self.updateModelContent(self.sim_list, sorted(self.completeTestList, key=lambda x: x.split("\t")[-1]))
        else:
            self.updateModelContent(self.sim_list, self.completeTestList)
    
    
    def updateTestDataTable(self):
        if self.data_interface is None:
            return
        
        if self.ui.infoBox.currentIndex() != 2:
            # do nothing if test data table is not selected
            return

        d = self.data_interface.getTestDataTableContent(self.getSelectedTests(), 
                                                        self.getCheckedHeads(), 
                                                        self.getCheckedSites())
        self.tmodel_data.setTestData(d["Data"])
        self.tmodel_data.setTestInfo(d["TestInfo"])
        self.tmodel_data.setDutIndexMap(d["dut2ind"])
        self.tmodel_data.setDutInfoMap(d["dutInfo"])
        self.tmodel_data.setTestLists(d["TestLists"])
        self.tmodel_data.setHHeaderBase([self.tr("Part ID"), self.tr("Test Head - Site")])
        self.tmodel_data.setVHeaderBase([self.tr("Test Number"), self.tr("HLimit"), self.tr("LLimit"), self.tr("Unit")])
        self.tmodel_data.setVHeaderExt(d["VHeader"])
        self.tmodel_data.setFont(QtGui.QFont(self.imageFont, 13 if isMac else 10))
        self.tmodel_data.setFloatFormat("%%.%d%s" % (self.settingParams.dataPrecision, 
                                                     self.settingParams.dataNotation))
        self.tmodel_data.layoutChanged.emit()
        hheaderview = self.ui.rawDataTable.horizontalHeader()
        hheaderview.setVisible(True)
        # FIXME: resize to contents causes laggy
        # hheaderview.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.ui.rawDataTable.verticalHeader().setVisible(True)
    
                
    def updateTabContent(self):
        if self.data_interface is None:
            return
        
        tabType = self.ui.tabControl.currentIndex()
        selSites = self.getCheckedSites()
        selHeads = self.getCheckedHeads()
        # update Test Data table in info tab
        if tabType == tab.Info:
            # filter dut summary table if in Info tab and head & site changed
            self.proxyModel_tmodel_dut.updateHeadsSites(selHeads, selSites)
            self.updateTestDataTable()
            return
        
        # draw plots        
        selTests = self.getSelectedTests()
        #TODO clean all plots in the current layout
        self.clearAllContents()
        tabLayout: QtWidgets.QVBoxLayout = self.tab_dict[tabType]["layout"]
        for testTuple, head in product(selTests, selHeads):
            chart = self.genPlot(testTuple, head, selSites, tabType)
            if chart:
                tabLayout.addWidget(chart)
        
    
    def updateStatTableContent(self):
        if self.data_interface is None:
            return
        
        tabType = self.ui.tabControl.currentIndex()
        selTests = self.getSelectedTests()
        horizontalHeader = self.ui.dataTable.horizontalHeader()
        verticalHeader = self.ui.dataTable.verticalHeader()
        floatFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
        
        if tabType == tab.Info or tabType == tab.Trend or tabType == tab.Histo:
            # get data
            d = self.data_interface.getTestStatistics(selTests, 
                                                      self.getCheckedHeads(), 
                                                      self.getCheckedSites(), 
                                                      floatFormat=floatFormat)
            HHeader = d["HHeader"]
            indexOfFail = HHeader.index("Fail Num")
            indexOfCpk = HHeader.index("Cpk")

            self.tmodel.setContent(d["Rows"])
            self.tmodel.setColumnCount(len(HHeader))
            self.tmodel.setFailCpkIndex(indexOfFail, indexOfCpk)
            self.tmodel.setCpkThreshold(self.settingParams.cpkThreshold)
            self.tmodel.setHHeader(list(map(self.tr, HHeader)))
            self.tmodel.setVHeader(d["VHeader"])
            
            horizontalHeader.setVisible(True)
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(25)
            verticalHeader.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # activate test statistc model
            self.ui.dataTable.setModel(self.tmodel)
            self.tmodel.layoutChanged.emit()
                
        else:
            if tabType == tab.Bin:
                d = self.data_interface.getBinStatistics(self.getCheckedHeads(), 
                                                         self.getCheckedSites())
            else:
                # wafer tab
                d = self.data_interface.getWaferStatistics(selTests, 
                                                           self.getCheckedSites())
            self.bwmodel.setContent(d["Rows"])
            self.bwmodel.setColumnCount(d["maxLen"])
            self.bwmodel.setHHeader([])
            self.bwmodel.setVHeader(d["VHeader"])
            self.bwmodel.setColorDict(self.settingParams.hbinColor, self.settingParams.sbinColor)
        
            horizontalHeader.setVisible(False)
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(35)
            verticalHeader.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # activate bin wafer model
            self.ui.dataTable.setModel(self.bwmodel)
            self.bwmodel.layoutChanged.emit()
                
    
    #TODO
    def genPlot(self, testTuple: tuple, head: int, selectSites: list[int], tabType: tab):
        '''testTuple: (test_num, pmr, test_name)'''
        if tabType == tab.Trend:
            tdata = self.data_interface.getTrendChartData(testTuple, head, selectSites)
            tchart = TrendChart()
            tchart.setTrendData(tdata)
            if tchart.validData:
                return tchart
        
        elif tabType == tab.Histo:
            pass
        elif tabType == tab.Wafer:
            pass
        elif tabType == tab.Bin:
            pass
        
        return None
            
            
    def clearOtherTab(self, currentTab):        
        # clear other tabs' images
        if currentTab != tab.Wafer:
            # wafer tab and other tab is separated in the app
            # we don't want to clean trend/histo/bin when we are in wafer tab
            [[ss.deleteWidget(self.tab_dict[key]["layout"].itemAt(index).widget()) for index in range(self.tab_dict[key]["layout"].count())] if key != currentTab else None for key in [tab.Trend, tab.Histo, tab.Bin]]
        gc.collect()
    
    
    def clearAllContents(self):
        # clear tabs' images
        [[ss.deleteWidget(self.tab_dict[key]["layout"].itemAt(index).widget()) for index in range(self.tab_dict[key]["layout"].count())] for key in [tab.Trend, tab.Histo, tab.Bin, tab.Wafer]]
        
        self.selectionTracker = {}
        gc.collect()
    
    
    def callFileLoader(self, paths: list[list[str]]):
        if paths:
            self.loader.loadFile(paths)

        
    @Slot(object)
    def updateData(self, newDI: DataInterface):
        if newDI is not None:
            # clear old images & tables
            self.clearAllContents()
            # close dut summary database if opened
            if self.db_dut.isOpen():
                self.db_dut.close()
            # close old data interface
            if self.data_interface is not None:
                self.data_interface.close()
            
            # working on the new object
            self.data_interface = newDI
            self.data_interface.loadDatabase()
            # open new dut summary database
            self.db_dut.setDatabaseName(self.data_interface.dbPath)
            if not self.db_dut.open():
                raise RuntimeError(f"Database cannot be opened by Qt: {self.data_interface.dbPath}")
            
            # disable/enable wafer tab
            self.ui.tabControl.setTabEnabled(4, self.data_interface.containsWafer)
            #TODO read waferDict
            # self.waferInfoDict = self.DatabaseFetcher.getWaferInfo()
    
            # update listView
            self.completeTestList = self.data_interface.completeTestList
            self.completeWaferList = self.data_interface.completeWaferList
            self.refreshTestList()
            self.updateModelContent(self.sim_list_wafer, self.completeWaferList)
            
            # remove site/head checkbox for invalid sites/heads
            current_exist_site = list(self.site_cb_dict.keys())     # avoid RuntimeError: dictionary changed size during iteration
            current_exist_head = list(self.head_cb_dict.keys())
            self.availableSites = self.data_interface.availableSites
            self.availableHeads = self.data_interface.availableHeads
            
            for site in current_exist_site:
                if site not in self.availableSites:
                    self.site_cb_dict.pop(site)
                    row = 1 + site//4
                    col = site % 4
                    cb_layout = self.ui.gridLayout_site_select.itemAtPosition(row, col)
                    if cb_layout is not None:
                        cb_layout.widget().deleteLater()
                        self.ui.gridLayout_site_select.removeItem(cb_layout)
                        
            for headnum in current_exist_head:
                if headnum not in self.availableHeads:
                    self.head_cb_dict.pop(headnum)
                    row = headnum//3
                    col = headnum % 3
                    cb_layout_h = self.ui.gridLayout_head_select.itemAtPosition(row, col)
                    if cb_layout_h is not None:
                        cb_layout_h.widget().deleteLater()
                        self.ui.gridLayout_head_select.removeItem(cb_layout_h)                    
                                 
            # add & enable checkboxes for each sites and heads
            siteNum = 0     # pre-define local var in case there are no available sites
            for siteNum in self.availableSites:
                if siteNum in self.site_cb_dict: 
                    # skip if already have a checkbox for this site
                    continue
                siteName = "Site %d" % siteNum
                self.site_cb_dict[siteNum] = QtWidgets.QCheckBox(self.ui.site_selection_contents)
                self.site_cb_dict[siteNum].setObjectName(siteName)
                self.site_cb_dict[siteNum].setText(siteName)
                row = 1 + siteNum//4
                col = siteNum % 4
                self.ui.gridLayout_site_select.addWidget(self.site_cb_dict[siteNum], row, col)
                
            for headnum in self.availableHeads:
                if headnum in self.head_cb_dict:
                    continue
                headName = "Head %d" % headnum
                self.head_cb_dict[headnum] = QtWidgets.QCheckBox(self.ui.head_selection_tab)
                self.head_cb_dict[headnum].setObjectName(headName)
                self.head_cb_dict[headnum].setText(headName)
                self.head_cb_dict[headnum].setChecked(True)
                row = headnum//3
                col = headnum % 3
                self.ui.gridLayout_head_select.addWidget(self.head_cb_dict[headnum], row, col)                
            # set max height in order to resize site/head selection tab control
            nrow_sites = len(set([0] + [1 + sn//4 for sn in self.site_cb_dict.keys()]))
            self.ui.site_head_selection.setMaximumHeight(50 + self.ui.gridLayout_site_select.cellRect(0, 0).height()*nrow_sites + 7*nrow_sites)
            # update UI
            self.settingUI.removeColorBtns()               # remove existing color btns
            self.settingUI.initColorBtns(self.availableSites, 
                                         self.data_interface.SBIN_dict, 
                                         self.data_interface.HBIN_dict)
            self.exporter.removeSiteCBs()
            self.exporter.refreshUI(self.completeTestList)
            self.init_SettingParams()
            self.init_Head_SiteCheckbox()
            self.updateFileHeader()
            self.updateDutSummaryTable()
            self.updateGDR_DTR_Table()
            self.onSelect()

    
    @Slot(str, bool, bool, bool)
    def updateStatus(self, new_msg, info=False, warning=False, error=False):
        self.statusBar().showMessage(new_msg)
        if info: 
            QMessageBox.information(self, self.tr("Info"), new_msg)
        elif warning: 
            QMessageBox.warning(self, self.tr("Warning"), new_msg)
            logger.warning(new_msg)
        elif error:
            QMessageBox.critical(self, self.tr("Error"), new_msg)
            # sys.exit()
        QApplication.processEvents()
        
    
    def eventFilter(self, object, event: QtCore.QEvent):
        # modified from https://stackoverflow.com/questions/18001944/pyqt-drop-event-without-subclassing
        if object in [self.ui.TestList, self.ui.tabControl, self.ui.dataTable]:
            if (event.type() == QtCore.QEvent.Type.DragEnter):
                if event.mimeData().hasUrls():
                    event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
                    return True
                else:
                    event.ignore()
                    return False
                    
            if (event.type() == QtCore.QEvent.Type.Drop):
                if event.mimeData().hasUrls():   # if file or link is dropped
                    urls = event.mimeData().urls()
                    paths = [url.toLocalFile() for url in urls]
                    event.accept()  # doesnt appear to be needed
                    self.openNewFile(paths)
                    return True
        return False         
      
        
    def onException(self, errorType, errorValue, tb):
        logger.error("Uncaught Error occurred", exc_info=(errorType, errorValue, tb))
        errMsg = traceback.format_exception(errorType, errorValue, tb, limit=0)
        self.updateStatus("\n".join(errMsg), False, False, True)
    
    

# application entry point
def run():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication([])
    app.setStyle('Fusion')
    app.setWindowIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Icon"], format = 'SVG'))))
    # default font for dialogs
    # font_names = []
    defaultFontNames = FontNames()
    # reverse to put courier at the rear
    for fn in sorted(os.listdir(os.path.join(sys.rootFolder, "fonts")), 
                     key=lambda x:x.lower(), reverse=True):
        if not fn.endswith(".ttf"): continue
        fontPath = os.path.join(sys.rootFolder, "fonts", fn)
        QtGui.QFontDatabase.addApplicationFont(fontPath)
        font_name = ttLib.TTFont(fontPath)["name"].getDebugName(1)
        if fn.startswith("cn_"):
            defaultFontNames.Chinese = font_name
        elif fn.startswith("en_"):
            defaultFontNames.English = font_name
    
    pathFromArgs = [item for item in sys.argv[1:] if os.path.isfile(item)]
    window = MyWindow(defaultFontNames)
    window.show()
    if pathFromArgs:
        window.callFileLoader(pathFromArgs)
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    run()