#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
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



import os, sys, gc, traceback, atexit
import json, logging, urllib.request as rq
import shutil
import numpy as np
from itertools import product
from deps.SharedSrc import *
from deps.ui.transSrc import transDict
from deps.DataInterface import DataInterface
from deps.customizedQtClass import *
from deps.ChartWidgets import *
from deps.uic_stdLoader import stdfLoader
from deps.uic_stdMerge import MergePanel
from deps.uic_stdFailMarker import FailMarker
from deps.uic_stdExporter import stdfExporter
from deps.uic_stdSettings import stdfSettings
from deps.uic_stdDutData import DutDataDisplayer
from deps.uic_stdDebug import stdDebugPanel
from deps.uic_stdConverter import StdfConverter
import rust_stdf_helper
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
    
# save config path to sys
rootFolder = os.path.dirname(sys.argv[0])
setattr(sys, "rootFolder", rootFolder)
setattr(sys, "CONFIG_PATH", os.path.join(rootFolder, "STDF-Viewer.config"))

# logger
init_logger(rootFolder)
logger = logging.getLogger("STDF-Viewer")


class signals4MainUI(QtCore.QObject):
    dataInterfaceSignal = Signal(object)  # get `DataInterface` from loader
    statusSignal = Signal(str, bool, bool, bool)   # status bar
    showDutDataSignal_TrendHisto = Signal(list)     # trend & histo
    showDutDataSignal_Bin = Signal(list)            # bin chart
    showDutDataSignal_Wafer = Signal(list)          # wafer


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        sys.excepthook = self.onException
        # load fonts and config file
        loadFonts()
        loadConfigFile()
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
        self.translatorUI = QTranslator(self)
        self.translatorCode = QTranslator(self)
        # init and connect signals
        self.signals = signals4MainUI()
        self.signals.dataInterfaceSignal.connect(self.updateData)
        self.signals.statusSignal.connect(self.updateStatus)
        self.signals.showDutDataSignal_TrendHisto.connect(self.onReadDutData_TrendHisto)
        self.signals.showDutDataSignal_Bin.connect(self.onReadDutData_Bin)
        self.signals.showDutDataSignal_Wafer.connect(self.onReadDutData_Wafer)
        # sub windows
        self.loader = stdfLoader(self.signals, self)
        self.mergePanel = MergePanel(self)
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
        self.ui.actionMerge.triggered.connect(self.onMerge)
        self.ui.actionLoad_Session.triggered.connect(self.onLoadSession)
        self.ui.actionSave_Session.triggered.connect(self.onSaveSession)
        self.ui.actionFailMarker.triggered.connect(self.onFailMarker)
        self.ui.actionExport.triggered.connect(self.onExportReport)
        self.ui.actionSettings.triggered.connect(self.onSettings)
        self.ui.actionAbout.triggered.connect(self.onAbout)
        self.ui.actionReadDutData_DS.triggered.connect(self.onReadDutData_DS)
        self.ui.actionReadDutData_TS.triggered.connect(self.onReadDutData_TS)
        self.ui.actionFetchDuts.triggered.connect(lambda: self.onFetchAllRows(self.ui.dutInfoTable))
        self.ui.actionFetchDatalog.triggered.connect(lambda: self.onFetchAllRows(self.ui.datalogTable))
        self.ui.actionAddFont.triggered.connect(self.onAddFont)
        self.ui.actionToXLSX.triggered.connect(self.onToXLSX)
        # init search-related UI
        self.ui.SearchBox.textChanged.connect(self.proxyModel_list.setFilterWildcard)
        self.ui.ClearButton.clicked.connect(self.clearSearchBox)
        # manage tab layout
        self.tab_dict = {tab.Trend: {"scroll": self.ui.scrollArea_trend, "layout": self.ui.verticalLayout_trend},
                         tab.Histo: {"scroll": self.ui.scrollArea_histo, "layout": self.ui.verticalLayout_histo},
                         tab.PPQQ: {"scroll": self.ui.scrollArea_ppqq, "layout": self.ui.verticalLayout_ppqq},
                         tab.Bin: {"scroll": self.ui.scrollArea_bin, "layout": self.ui.verticalLayout_bin},
                         tab.Wafer: {"scroll": self.ui.scrollArea_wafer, "layout": self.ui.verticalLayout_wafer},
                         tab.Correlate: {"scroll": self.ui.scrollArea_correlation, "layout": self.ui.verticalLayout_correlation}}
        # init callback for UI component
        self.ui.tabControl.currentChanged.connect(self.onSelect)
        self.ui.infoBox.currentChanged.connect(self.updateTestDataTable)
        # set drop down menu for session action
        self.utilityMenu = QtWidgets.QMenu()
        self.utilityMenu.addActions([self.ui.actionLoad_Session, 
                                     self.ui.actionSave_Session,
                                     self.ui.actionAddFont,
                                     self.ui.actionToXLSX])
        self.utilityBtn = QtWidgets.QToolButton()
        self.utilityBtn.setText(self.tr("Utility"))
        self.utilityBtn.setMenu(self.utilityMenu)
        self.utilityBtn.setIcon(getIcon("Tools"))
        self.utilityBtn.setStyleSheet("QToolButton::menu-indicator{image:none}")
        self.utilityBtn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.utilityBtn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.ui.toolBar.addWidget(self.utilityBtn)
        # add a toolbar action at the right side
        self.spaceWidgetTB = QtWidgets.QWidget()
        self.spaceWidgetTB.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                                               QtWidgets.QSizePolicy.Policy.Expanding))
        self.ui.toolBar.addWidget(self.spaceWidgetTB)
        self.ui.toolBar.addAction(self.ui.actionAbout)
        # disable wafer tab in default
        self.ui.tabControl.setTabEnabled(tab.Wafer, False)
        # clean up before exiting
        atexit.register(self.onExit)
        # set language after initing subwindow & reading config
        self.changeLanguage()
        self.restorePreviousSession()
        # hide unfinished feature
        self.ui.file_selection.hide()
        self.ui.tabControl.setTabVisible(tab.PPQQ, False)
        self.ui.tabControl.setTabVisible(tab.Correlate, False)
        
        
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
                msgBox.setText("<span font-size:20px'>{0}&nbsp;&nbsp;&nbsp;&nbsp;\
                                <a href='{2}'>{1}</a></span>".format(
                                    self.tr("{0} is available!").format(latestTag),
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
        settings = getSetting()
        curLang = settings.language
        font = settings.font
        if curLang == "English":
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
            
        newfont = QtGui.QFont(font)
        _app.setFont(newfont)
        _ = [w.setFont(newfont) if not isinstance(w, QtWidgets.QListView) else None for w in QApplication.allWidgets()]
        # actions is not listed in qapp all widgets, iterate separately
        _ = [w.setFont(newfont) for w in self.ui.toolBar.actions()]
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
        translate_const_dicts(self.tr)
        # need to rewrite file info table after changing language
        self.updateFileHeader()        
    

    def openNewFile(self, files: list[str]):
        if not files:
            files, _ = QFileDialog.getOpenFileNames(self, caption=self.tr("Select STDF Files To Open"), 
                                                    directory=getSetting().recentFolder, 
                                                    filter=self.tr(FILE_FILTER),)
        else:
            files = [f for f in map(os.path.normpath, files) if os.path.isfile(f)]
            
        if files:
            # store folder path
            updateRecentFolder(files[0])
            # self.callFileLoader([files])
            self.callFileLoader([[f] for f in files])
              
    
    def onMerge(self):
        self.mergePanel.showUI()
    
    
    def onLoadSession(self):
        p, _ = QFileDialog.getOpenFileName(self, caption=self.tr("Select a STDF-Viewer session"), 
                                           directory=getSetting().recentFolder, 
                                           filter=self.tr("Database (*.db)"))
        if p:
            isvalid, msg = validateSession(p)
            if isvalid:
                self.loadDatabase(p)
            else:
                QMessageBox.warning(self, self.tr("Warning"), 
                                    self.tr("This session cannot be loaded: \n{}\n\n{}").format(p, msg))
    
    
    def onSaveSession(self):
        if self.data_interface is not None:
            dbPath = self.data_interface.dbPath
            dbSize = os.stat(dbPath).st_size / 2**20
            # show confirm message if size is > 50M
            if dbSize >= 50:
                msg = QMessageBox.information(None, self.tr("Notice"), 
                                              self.tr("Current session size is {}, proceed?").format("%.2f MB"%dbSize),
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                              QMessageBox.StandardButton.No)
                if msg == QMessageBox.StandardButton.No:
                    return
            outPath, _ = QFileDialog.getSaveFileName(None, caption=self.tr("Save Session As"), 
                                                     filter=self.tr("Database (*.db)"))
            if outPath:
                def saveSessionTask(pIn: str, pOut: str):
                    shutil.copy(pIn, pOut)
                # tmp is only used for preventing thread being deleted before finished
                self.tmp = runInQThread(saveSessionTask, 
                                        (dbPath, outPath), 
                                        self.tr("Saving session"), 
                                        self.signals.statusSignal)
        else:
            # no data is found, show a warning dialog
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No file is loaded."))
    
    
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
        msgBox.setText("<span style='color:#930DF2;font-size:20px'>STDF Viewer</span>\
                        <br>{0}: {1}\
                        <br>{2}: noonchen\
                        <br>{3}: chennoon233@foxmail.com<br>".format(
                            self.tr("Version"), 
                            Version,  
                            self.tr("Author"),
                            self.tr("Email")))
        
        msgBox.setInformativeText("{0}:\
            <br><a href='https://github.com/noonchen/STDF_Viewer'>noonchen @ STDF_Viewer</a>\
            <br>\
            <br><span style='font-size:10px'>{1}</span>".format(self.tr("For instructions, please refer to the ReadMe in the repo"), 
                                                               self.tr("Disclaimer: This free app is licensed under GPL 3.0, \
                                                                        you may use it free of charge but WITHOUT ANY WARRANTY, \
                                                                        it might contians bugs so use it at your own risk.")))
        appIcon = getIcon("App").pixmap(250, 250)
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
        
        
    def onAddFont(self):
        p, _ = QFileDialog.getOpenFileName(self, caption=self.tr("Select a .ttf font file"), 
                                           directory=getSetting().recentFolder, 
                                           filter=self.tr("TTF Font (*.ttf)"))
        if not p:
            return
        
        if QtGui.QFontDatabase.addApplicationFont(p) < 0:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("This font cannot be loaded:\n{}").format(p))
        else:
            shutil.copy(src=p, 
                        dst=os.path.join(sys.rootFolder, "fonts"), 
                        follow_symlinks=True)
            # manually refresh font list
            loadFonts()
            self.settingUI.refreshFontList()
            QMessageBox.information(self, self.tr("Completed"), self.tr("Load successfully, change font in settings to take effect"))
    
    
    def onToXLSX(self):
        cv = StdfConverter(self)
        cv.setupConverter(self.tr("STDF to XLSX Converter"), 
                          self.tr("XLSX Path Selection"), 
                          ".xlsx", 
                          rust_stdf_helper.stdf_to_xlsx)
        cv.showUI()
    
    
    def onExit(self):
        '''
        Clean up before closing app
        '''
        self.db_dut.close()
        if self.data_interface:
            currentDB = self.data_interface.dbPath
            self.data_interface.close()
        else:
            currentDB = "???"
        # save settings to file
        dumpConfigFile()
        # clean generated database
        dbFolder = os.path.join(sys.rootFolder, "logs")
        for f in os.listdir(dbFolder):
            # save current database
            if f.endswith(".db") and not currentDB.endswith(f):
                try:
                    os.remove(os.path.join(dbFolder, f))
                except OSError:
                    pass
    
    
    def getDataInterface(self) -> DataInterface:
        return self.data_interface
    
    
    def showDutDataTable(self, selectedDutIndexes: list):
        # always update style in case user changed them in the setting
        settings = getSetting()
        self.dutDataDisplayer.setTextFont(QtGui.QFont(settings.font, 13 if isMac else 10))
        self.dutDataDisplayer.setFloatFormat(settings.getFloatFormat())
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
      
    
    def onFetchAllRows(self, activeTable: QtWidgets.QTableView):
        model = activeTable.model()
        if isinstance(model, DutSortFilter):
            # dut summary uses proxy model
            model = model.sourceModel()
        if isinstance(model, QtSql.QSqlQueryModel):
            self.signals.statusSignal.emit(self.tr("Fetching all..."), False, False, False)
            while model.canFetchMore():
                model.fetchMore()
            self.signals.statusSignal.emit(self.tr("Fetch Done!"), False, False, False)
    
    
    @Slot(list)
    def onReadDutData_TrendHisto(self, selectedDutIndex: list):
        '''
        selectedDutIndex: a list of (fid, dutIndex)
        '''
        if selectedDutIndex:
            self.showDutDataTable(selectedDutIndex)
    
        
    @Slot(list)
    def onReadDutData_Bin(self, selectedBin: list):
        '''
        selectedBin: a list of (fid, isHBIN, [bin_num])
        '''
        selectedDutIndex = self.data_interface.DatabaseFetcher.getDUTIndexFromBin(selectedBin)
        if selectedDutIndex:
            self.showDutDataTable(selectedDutIndex)
    
    
    @Slot(list)
    def onReadDutData_Wafer(self, selectedDie: list):
        '''
        selectedDie: a list of (waferInd, fid, (x, y))
        '''
        selectedDutIndex = self.data_interface.DatabaseFetcher.getDUTIndexFromXY(selectedDie)
        if selectedDutIndex:
            self.showDutDataTable(selectedDutIndex)
    
    
    def enableDragDrop(self):
        for obj in [self.ui.TestList, self.ui.tabControl, self.ui.dataTable]:
            obj.setAcceptDrops(True)
            obj.installEventFilter(self)

    
    def updateIcons(self):
        self.ui.actionOpen.setIcon(getIcon("Open"))
        self.ui.actionMerge.setIcon(getIcon("Merge"))
        self.ui.actionFailMarker.setIcon(getIcon("FailMarker"))
        self.ui.actionExport.setIcon(getIcon("Export"))
        self.ui.actionSettings.setIcon(getIcon("Settings"))
        self.ui.actionLoad_Session.setIcon(getIcon("LoadSession"))
        self.ui.actionSave_Session.setIcon(getIcon("SaveSession"))
        self.ui.actionAbout.setIcon(getIcon("About"))
        self.ui.actionAddFont.setIcon(getIcon("AddFont"))
        self.ui.actionToXLSX.setIcon(getIcon("Convert"))
        self.ui.toolBar.setIconSize(QtCore.QSize(20, 20))
        
        self.ui.tabControl.setTabIcon(tab.Info, getIcon("tab_info"))
        self.ui.tabControl.setTabIcon(tab.Trend, getIcon("tab_trend"))
        self.ui.tabControl.setTabIcon(tab.Histo, getIcon("tab_hist"))
        self.ui.tabControl.setTabIcon(tab.PPQQ, getIcon("tab_ppqq"))
        self.ui.tabControl.setTabIcon(tab.Bin, getIcon("tab_bin"))
        self.ui.tabControl.setTabIcon(tab.Wafer, getIcon("tab_wafer"))
        self.ui.tabControl.setTabIcon(tab.Correlate, getIcon("tab_correlation"))
    
    
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
        self.ui.datalogTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)     # select row only
        self.ui.datalogTable.setItemDelegate(StyleDelegateForTable_List(self.ui.datalogTable))
        self.ui.datalogTable.addAction(self.ui.actionFetchDatalog)
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
        self.ui.dutInfoTable.addAction(self.ui.actionFetchDuts)
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
        self.ui.fileInfoTable.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        
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
                if getSetting().language != "English":
                    # fix weird font when switch to chinese-s
                    qfont = QtGui.QFont(getSetting().font)
                    _ = [qele.setData(qfont, Qt.ItemDataRole.FontRole) for qele in qitemRow]
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
        
        self.tmodel_dut.setQuery(QtSql.QSqlQuery(DUT_SUMMARY_QUERY, self.db_dut))
        
        for column in range(0, header.count()):
            if column in [2, 3, header.count()-1]:
                # PartID, Head-Site and DUT Flag
                # column may be too long to display
                mode = QHeaderView.ResizeMode.ResizeToContents
            else:
                mode = QHeaderView.ResizeMode.Stretch
            header.setSectionResizeMode(column, mode)
        
        # always hide dut index column
        self.ui.dutInfoTable.hideColumn(0)
        # hide file id column if 1 file is opened
        if self.data_interface.num_files <= 1:
            self.ui.dutInfoTable.hideColumn(1)
        else:
            self.ui.dutInfoTable.showColumn(1)
        # # show all rows
        # while self.tmodel_dut.canFetchMore():
        #     self.tmodel_dut.fetchMore()
        
        
    def updateGDR_DTR_Table(self):
        header = self.ui.datalogTable.horizontalHeader()
        header.setVisible(True)
        
        self.tmodel_datalog.setQuery(QtSql.QSqlQuery(DATALOG_QUERY, self.db_dut))
                    
        for column in [2, 3]:
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.ui.datalogTable.resizeRowsToContents()
        
        # hide file id column if 1 file is opened
        if self.data_interface.num_files <= 1:
            self.ui.datalogTable.hideColumn(0)
        else:
            self.ui.datalogTable.showColumn(0)
        # # show all rows
        # while self.tmodel_datalog.canFetchMore():
        #     self.tmodel_datalog.fetchMore()
        
        
    def clearSearchBox(self):
        self.ui.SearchBox.clear()


    def toggleSite(self, on=True):
        self.ui.All.setChecked(on)
        for _, cb in self.site_cb_dict.items():
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
                tnTuple = parseTestString(ind.data(), inWaferTab)
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
        
        if currentTab in [tab.Bin, tab.Correlate]:
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
        testTuple = parseTestString(selected_string, False)
        testPass = self.data_interface.checkTestPassFail(testTuple)
        settings = getSetting()
        
        if testPass:
            # if user do not need to check Cpk, return to caller
            if not settings.checkCpk:
                return "Pass"
        else:
            return "Fail"
        
        # check if cpk is lower than the threshold
        cpkList = self.data_interface.getTestCpkList(testTuple)
        for cpk in cpkList:
            if not np.isnan(cpk):
                # check cpk only if it's valid
                if cpk < settings.cpkThreshold:
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
        
        testSortMethod = getSetting().sortTestList
        if testSortMethod == "Number":
            self.updateModelContent(self.sim_list, sorted(self.completeTestList, key=lambda x: parseTestString(x)[0]))
        elif testSortMethod == "Name":
            self.updateModelContent(self.sim_list, sorted(self.completeTestList, key=lambda x: x.split("\t")[-1]))
        else:
            self.updateModelContent(self.sim_list, self.completeTestList)
    
    
    def updateTestDataTable(self):
        if self.data_interface is None:
            return
        
        if self.ui.infoBox.currentIndex() != 2:
            # do nothing if test data table is not selected
            return

        settings = getSetting()
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
        self.tmodel_data.setFont(QtGui.QFont(settings.font, 13 if isMac else 10))
        self.tmodel_data.setFloatFormat(settings.getFloatFormat())
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
        
        # get selected tests
        if tabType in [tab.Bin, tab.Correlate]:
            # BinChart & correlation are irrelevent to tests, 
            # fake a list with only one element
            selTests = [""]
        else:
            selTests = self.getSelectedTests()
        # clean all plots in the current layout
        self.clearCurrentTab(tabType)
        tabLayout: QtWidgets.QVBoxLayout = self.tab_dict[tabType]["layout"]
        for testTuple, head in product(selTests, selHeads):
            chart = self.genPlot(testTuple, head, selSites, tabType)
            if isinstance(chart, QtWidgets.QGraphicsView):
                tabLayout.addWidget(chart)
            elif isinstance(chart, list):
                for c in chart:
                    if isinstance(c, QtWidgets.QGraphicsView):
                        tabLayout.addWidget(c)
        
    
    def updateStatTableContent(self):
        if self.data_interface is None:
            return
        
        tabType = self.ui.tabControl.currentIndex()
        selTests = self.getSelectedTests()
        horizontalHeader = self.ui.dataTable.horizontalHeader()
        verticalHeader = self.ui.dataTable.verticalHeader()
        settings = getSetting()
        
        if tabType in [tab.Info, tab.Trend, tab.Histo, tab.PPQQ]:
            # get data
            d = self.data_interface.getTestStatistics(selTests, 
                                                      self.getCheckedHeads(), 
                                                      self.getCheckedSites())
            HHeader = d["HHeader"]
            indexOfFail = HHeader.index("Fail Num")
            indexOfCpk = HHeader.index("Cpk")

            self.tmodel.setContent(d["Rows"])
            self.tmodel.setColumnCount(len(HHeader))
            self.tmodel.setFailCpkIndex(indexOfFail, indexOfCpk)
            self.tmodel.setCpkThreshold(settings.cpkThreshold)
            self.tmodel.setHHeader(list(map(self.tr, HHeader)))
            self.tmodel.setVHeader(d["VHeader"])
            
            horizontalHeader.setVisible(True)
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(25)
            verticalHeader.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # activate test statistc model
            self.ui.dataTable.setModel(self.tmodel)
            self.tmodel.layoutChanged.emit()
                
        elif tabType == tab.Correlate:
            #TODO
            pass
        
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
            self.bwmodel.setColorDict(settings.hbinColor, 
                                      settings.sbinColor)
        
            horizontalHeader.setVisible(False)
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(35)
            verticalHeader.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # activate bin wafer model
            self.ui.dataTable.setModel(self.bwmodel)
            self.bwmodel.layoutChanged.emit()
                
    
    def genPlot(self, testTuple: tuple, head: int, selectSites: list[int], tabType: tab):
        '''
        testTuple: (test_num, pmr, test_name)
        For wafer: (wafer index, file id, wafer name)
        '''
        if tabType == tab.Trend:
            tdata = self.data_interface.getTrendChartData(testTuple, head, selectSites)
            tchart = TrendChart()
            tchart.setTrendData(tdata)
            if tchart.validData:
                tchart.setShowDutSignal(self.signals.showDutDataSignal_TrendHisto)
                return tchart
        
        elif tabType == tab.Histo:
            tdata = self.data_interface.getTrendChartData(testTuple, head, selectSites)
            hchart = HistoChart()
            hchart.setTrendData(tdata)
            if hchart.validData:
                hchart.setShowDutSignal(self.signals.showDutDataSignal_TrendHisto)
                return hchart
        
        elif tabType == tab.Wafer:
            wdata = self.data_interface.getWaferMapData(testTuple, selectSites)
            wchart = WaferMap()
            wchart.setWaferData(wdata)
            if wchart.validData:
                wchart.setShowDutSignal(self.signals.showDutDataSignal_Wafer)
                return wchart
        
        elif tabType == tab.Bin:
            bcharts = []
            # one site per binchart
            for site in selectSites:
                bdata = self.data_interface.getBinChartData(head, site)
                bchart = BinChart()
                bchart.setBinData(bdata)
                if bchart.validData:
                    bchart.setShowDutSignal(self.signals.showDutDataSignal_Bin)
                    bcharts.append(bchart)
            return bcharts
        
        return None
            
            
    def getFileInfoForReport(self):
        # this table uses standarded model
        model = self.tmodel_info
        info = []
        for row in range(model.rowCount()):
            infoRow = []
            for col in range(model.columnCount()):
                d = model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
                infoRow.append(d if isinstance(d, str) else str(d))
            info.append(infoRow)
        return info
    
    
    def getDUTSummaryForReport(self, heads: list[int], sites: list[int], fids: list[int], testTuples: list):
        '''
        For report generator
        Return data for `DutSummary` content
        '''
        return self.data_interface.getDutSummaryReportContent(testTuples, heads, sites, fids)
    
    
    def getDatalogForReport(self):
        # this table uses sql query model
        model = self.tmodel_datalog
        
        # # method 1: store complete data in a list
        # while model.canFetchMore():
        #     model.fetchMore()

        # datalog = []
        # for row in range(model.rowCount()):
        #     datalogRow = []
        #     for col in range(model.columnCount()):
        #         d = model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
        #         datalogRow.append(d if isinstance(d, str) else "")
        #     datalog.append(datalogRow)
        # return datalog
        
        # method 2: use generator
        row = 0
        while model.canFetchMore():
            model.fetchMore()
            
            while row < model.rowCount():
                datalogRow = []
                for col in range(model.columnCount()):
                    d = model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
                    datalogRow.append(d.strip("\n") if isinstance(d, str) else str(d))
                row += 1
                yield datalogRow
    
    
    def getImageBytesForReport(self, testTuple: tuple, head: int, sites: list[int], fids: list[int], tabType: tab):
        '''
        For report generator
        #TODO fids current not used
        '''
        chart = self.genPlot(testTuple, head, sites, tabType)
        return pyqtGraphPlot2Bytes(chart)
    
    
    def getTestStatisticForReport(self, heads: list[int], sites: list[int], fids: list[int], tabType: tab, kargs: dict):
        '''
        For report generator, kargs contains (testTuple or isHBIN)
        #TODO fids current not used
        '''
        data = []
        if tabType in [tab.Trend, tab.Histo, tab.PPQQ]:
            testTuples = kargs["testTuples"]
            d = self.data_interface.getTestStatistics(testTuples, heads, sites)
            # add translated hheader, put an empty string for matching
            data.append([""] + [self.tr(h) for h in d["HHeader"]])
            # vheader + statistics
            for vh, dataRow in zip(d["VHeader"], d["Rows"]):
                data.append([vh] + dataRow)            
            
        elif tabType == tab.Bin:
            isHBIN = kargs["isHBIN"]
            d = self.data_interface.getBinStatistics(heads, sites)
            for vh, dataRow in zip(d["VHeader"], d["Rows"]):
                if isHBIN == dataRow[0][-1]:
                    data.append([vh] + [ele[0] for ele in dataRow])
        
        elif tabType == tab.Wafer:
            waferTuples = kargs["testTuples"]
            d = self.data_interface.getWaferStatistics(waferTuples, sites)
            for vh, dataRow in zip(d["VHeader"], d["Rows"]):
                data.append([vh] + [ele[0] for ele in dataRow])

        return data
    
    
    def clearCurrentTab(self, currentTab: tab):
        layout: QtWidgets.QVBoxLayout = self.tab_dict[currentTab]["layout"]
        # put widgets in a list and delete at once
        # if delete directly from layout, the widget index might be invalid
        wl = []
        for i in range(layout.count()):
            wl.append(layout.itemAt(i).widget())
        deleteWidget(wl)
        del wl
        gc.collect()
    
    
    def clearAllContents(self):
        # clear tabs' images
        for t in [tab.Trend, tab.Histo, tab.PPQQ, 
                  tab.Bin, tab.Wafer, tab.Correlate]:
            self.clearCurrentTab(t)
        self.selectionTracker = {}
        gc.collect()
    
    
    def callFileLoader(self, paths: list[list[str]]):
        if paths:
            self.loader.loadFile(paths)

        
    def restorePreviousSession(self):
        '''
        looking for database of previous loaded
        stdf files
        '''
        dbFolder = os.path.join(sys.rootFolder, "logs")
        dbs = [f for f in os.listdir(dbFolder) if f.endswith(".db")]
        if dbs:
            dbPath = os.path.join(dbFolder, dbs[0])
            self.loadDatabase(dbPath)
    
    
    def loadDatabase(self, dbPath: str):
        di = DataInterface()
        di.dbPath = dbPath
        self.signals.dataInterfaceSignal.emit(di)
    
    
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
            self.ui.tabControl.setTabEnabled(tab.Wafer, self.data_interface.containsWafer)
    
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
            setSettingDefaultColor(self.availableSites, 
                                   self.data_interface.SBIN_dict, 
                                   self.data_interface.HBIN_dict)
            setSettingDefaultSymbol(self.data_interface.num_files)
            # remove existing color btns
            self.settingUI.removeColorBtns()
            self.settingUI.initColorBtns(self.availableSites, 
                                         self.data_interface.SBIN_dict, 
                                         self.data_interface.HBIN_dict)
            self.settingUI.removeSymbolBtns()
            self.settingUI.initSymbolBtns(self.data_interface.num_files)
            self.exporter.removeSiteCBs()
            self.exporter.refreshUI(self.completeTestList,
                                    self.completeWaferList,
                                    self.availableHeads,
                                    self.availableSites,
                                    self.data_interface.num_files)
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
        
    
    def eventFilter(self, widget, event: QtCore.QEvent):
        # modified from https://stackoverflow.com/questions/18001944/pyqt-drop-event-without-subclassing
        if widget in [self.ui.TestList, self.ui.tabControl, self.ui.dataTable]:
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
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    app.setWindowIcon(getIcon("App"))
    pathFromArgs = [item for item in sys.argv[1:] if os.path.isfile(item)]
    window = MyWindow()
    window.show()
    if pathFromArgs:
        window.callFileLoader(pathFromArgs)
    sys.exit(app.exec_())
    

if __name__ == '__main__':
    run()