#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
# -----
# Last Modified: Thu Nov 17 2022
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
from base64 import b64decode
from deps.SharedSrc import tab, REC
import deps.SharedSrc as ss
from deps.ui.ImgSrc_svg import ImgDict
from deps.ui.transSrc import transDict
from deps.StdfFile import DataInterface
from deps.MatplotlibWidgets import PlotCanvas, MagCursor
from deps.customizedQtClass import StyleDelegateForTable_List, DutSortFilter, ColorSqlQueryModel, DatalogSqlQueryModel


from deps.uic_stdLoader import stdfLoader
from deps.uic_stdFailMarker import FailMarker
from deps.uic_stdExporter import stdfExporter
from deps.uic_stdSettings import stdfSettings, SettingParams
from deps.uic_stdDutData import DutDataReader
from deps.uic_stdDebug import stdDebugPanel

# pyqt5
from deps.ui.stdfViewer_MainWindows import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets, QtGui, QtSql
from PyQt5.QtWidgets import QApplication, QFileDialog, QAbstractItemView, QMessageBox
from PyQt5.QtCore import Qt, QTranslator, pyqtSignal as Signal, pyqtSlot as Slot
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

import matplotlib
matplotlib.use('QT5Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

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
        # data_interface for processing requests by GUI and reading data 
        # from database or files
        self.data_interface = None
        # database for dut summary only
        self.db_dut = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        # used for detecting tab changes
        self.preTab = None             
        # used for detecting site selection changes
        self.preSiteSelection = set()    
        self.preHeadSelection = set()
        self.preTestSelection = set()
        # dict to store site/head checkbox objects
        self.site_cb_dict = {}
        self.head_cb_dict = {}
        # init/clear a dict to store cursors instance to prevent garbage collection
        self.cursorDict = {}
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
        self.dutDataReader = DutDataReader(self)
        self.debugPanel = stdDebugPanel(self)
        # update icons for actions and widgets
        self.updateIcons()
        self.init_TestList()
        self.init_DataTable()
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
        self.ui.infoBox.currentChanged.connect(self.onInfoBoxChanged)
        # add a toolbar action at the right side
        self.ui.spaceWidgetTB = QtWidgets.QWidget()
        self.ui.spaceWidgetTB.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.ui.toolBar.addWidget(self.ui.spaceWidgetTB)
        self.ui.toolBar.addAction(self.ui.actionAbout)
        # disable wafer tab in default
        self.ui.tabControl.setTabEnabled(4, False)
        # clean up before exiting
        atexit.register(self.onExit)
        # a workaround for not canvas not having render attribute
        self.textRender = None
        self.changeLanguage()   # set language after initing subwindow & reading config
        
        
    def checkNewVersion(self):
        try:
            res = rq.urlopen("https://api.github.com/repos/noonchen/STDF-Viewer/releases/latest")
            resDict = json.loads(res.read())
            latestTag = resDict["tag_name"]
            changeList = resDict["body"]
            releaseLink = resDict["html_url"]
            
            if latestTag > Version:
                # show dialog for updating
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setWindowFlag(Qt.FramelessWindowHint)
                msgBox.setTextFormat(QtCore.Qt.RichText)
                msgBox.setText("<span font-size:20px'>{0}&nbsp;&nbsp;&nbsp;&nbsp;<a href='{2}'>{1}</a></span>".format(self.tr("{0} is available!").format(latestTag),
                                                                                                                      self.tr("→Go to download page←"),
                                                                                                                      releaseLink))
                msgBox.setInformativeText(self.tr("Change List:") + "\n\n" + changeList)
                msgBox.addButton(self.tr("Maybe later"), QtWidgets.QMessageBox.NoRole)
                msgBox.exec_()
            else:
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setWindowFlag(Qt.FramelessWindowHint)
                msgBox.setTextFormat(QtCore.Qt.RichText)
                msgBox.setText(self.tr("You're using the latest version."))
                msgBox.exec_()
            
        except Exception as e:
                # tell user cannot connect to the internet
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setWindowFlag(Qt.FramelessWindowHint)
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
            self.dutDataReader.translator.loadFromData(transDict["English"])
            self.dutDataReader.tableUI.translator.loadFromData(transDict["English"])
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
            self.dutDataReader.translator.loadFromData(transDict["dutDataCode_zh_CN"])
            self.dutDataReader.tableUI.translator.loadFromData(transDict["dutDataUI_zh_CN"])
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
        _app.installTranslator(self.dutDataReader.tableUI.translator)
        self.dutDataReader.tableUI.UI.retranslateUi(self.dutDataReader.tableUI)
        # debugUI
        _app.installTranslator(self.debugPanel.translator)
        self.debugPanel.dbgUI.retranslateUi(self.debugPanel)
        # failmarker
        _app.installTranslator(self.failmarker.translator)
        # dutData
        _app.installTranslator(self.dutDataReader.translator)
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
            files, _typ = QFileDialog.getOpenFileNames(self, 
                                                  caption=self.tr("Select a STD File To Open"), 
                                                  directory=self.settingParams.recentFolder,
                                                  filter=self.tr("All Supported Files (*.std* *.std*.gz *.std*.bz2 *.std*.zip);;STDF (*.std *.stdf);;Compressed STDF (*.std*.gz *.std*.bz2 *.std*.zip);;All Files (*.*)"),)
        else:
            files = [f for f in map(os.path.normpath, files) if os.path.isfile(f)]
            
        if files:
            # store folder path
            self.updateRecentFolder(files[0])
            self.callFileLoader(files)
              
    
    def onFailMarker(self):
        if self.dbConnected:
            self.failmarker.start()
        else:
            # no data is found, show a warning dialog
            QtWidgets.QMessageBox.warning(self, self.tr("Warning"), self.tr("No file is loaded."))
                
    
    def onExportReport(self):
        if self.dbConnected:
            self.exporter.showUI()
            # we have to de-select test_num(s) after exporting
            # the selected test nums may not be prepared anymore
            self.ui.TestList.clearSelection()
        else:
            # no data is found, show a warning dialog
            QtWidgets.QMessageBox.warning(self, self.tr("Warning"), self.tr("No file is loaded."))
    
    
    def onSettings(self):
        self.settingUI.showUI()
    
    
    def onAbout(self):
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setWindowTitle(self.tr("About"))
        msgBox.setTextFormat(QtCore.Qt.RichText)
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
        dbgBtn = msgBox.addButton(self.tr("Debug"), QtWidgets.QMessageBox.ResetRole)   # leftmost
        ckupdateBtn = msgBox.addButton(self.tr("Check For Updates"), QtWidgets.QMessageBox.ApplyRole)   # middle
        msgBox.addButton(self.tr("OK"), QtWidgets.QMessageBox.NoRole)   # rightmost
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
    
    
    # TODO
    # def getDutSummaryOfIndex(self, dutIndex: int) -> list[str]:
    #     row = dutIndex - 1
    #     dutSumList = [self.tmodel_dut.data(self.tmodel_dut.index(row, col)) for col in range(self.tmodel_dut.columnCount())]
    #     if self.containsWafer:
    #         return dutSumList
    #     else:
    #         # insert empty waferIndex & (X,Y) before DUT Flag
    #         dutSumList[-1:-1] = ["-", "-"]
    #         return dutSumList
    
    
    def showDutDataTable(self, dutIndexes:list):
        self.dutDataReader.setDutIndexes(dutIndexes)
        self.dutDataReader.start()
        
    
    def onReadDutData_DS(self):
        # context menu callback for DUT summary
        selectedRows = self.ui.dutInfoTable.selectionModel().selectedRows()
        if selectedRows:
            # since we used proxy model in DUT summary, the selectedRows is from proxy model
            # it should be converted back to source model rows first
            getSourceIndex = lambda pIndex: self.proxyModel_tmodel_dut.mapToSource(pIndex)
            # TODO: instead of retrieving dut index, we need to get rowid from Dut_Info table
            selectedDutIndex = [self.Row_DutIndexDict[getSourceIndex(r).row()] for r in selectedRows]   # if row(s) is selected, self.Row_DutIndexDict is already updated in self.prepareDataForDUTSummary()
            self.showDutDataTable(sorted(selectedDutIndex))


    def onReadDutData_TS(self):
        # context menu callback for Test summary
        selectedRows = self.ui.rawDataTable.selectionModel().selectedIndexes()
        if selectedRows:
            allDutIndexes = [r.row()-3 for r in selectedRows]    # row4 is dutIndex 1
            selectedDutIndex = sorted([i for i in set(allDutIndexes) if i > 0])     # remove duplicates and invalid dutIndex (e.g. header rows)
            if selectedDutIndex:
                self.showDutDataTable(selectedDutIndex)
            else:
                QMessageBox.information(None, self.tr("No DUTs selected"), self.tr("You need to select DUT row(s) first"), buttons=QMessageBox.Ok)
  
    
    #TODO remove if we use pyqtGraph 
    def onInfoBoxChanged(self):
        # update raw data table if:
        # 1. it is activated;
        # 2. dut list changed (site & head selection changed);
        # 3. test num selection changed;
        # 4. tab changed
        updateInfoBox = False
        selHeads = []
        selSites = []
        selTests = []
        currentMask = np.array([])

        if self.ui.infoBox.currentIndex() == 2:              # raw data table activated
            selTests = self.getSelectedTests()
            selSites = self.getCheckedSites()
            selHeads = self.getCheckedHeads()
            currentMask = self.getMaskFromHeadsSites(selHeads, selSites)
            
            # test num selection changed
            # MPR test will be splited into several items with same test name
            # use (test number, pmr) to determine the changes in test selection
            testChanged = (self.preTestSelection != set(selTests))
            # dut list changed
            dutChanged = np.any(currentMask != self.getMaskFromHeadsSites(self.preHeadSelection, self.preSiteSelection))
            if testChanged or dutChanged:   
                updateInfoBox = True
            elif self.tmodel_raw.columnCount() == 0:
                updateInfoBox = True
            else:
                # if user switches to the raw table from other tabs or boxes 
                # tn & dut is unchanged, but previous raw table content might be different than current selection
                # we also need to update the table
                testsInTable = set()
                for col in range(2, self.tmodel_raw.columnCount()):     # raw col count == 0 or >= 3, thus index=2 is safe
                    tn = int(self.tmodel_raw.item(0, col).text())
                    colHeader = self.tmodel_raw.horizontalHeaderItem(col).text()
                    if (tn, colHeader) not in self.testRecTypeDict:
                        # I append pmr to the testname if it's MPR, 
                        # colheader is not likely a valid test name
                        # only MPR will hit this case
                        # colHeader: TestName #pmr
                        tmpList = colHeader.split(" #")
                        testName = tmpList[0].strip()
                        pmr = int(tmpList[-1])
                    else:
                        testName = colHeader
                        pmr = 0
                    testsInTable.add( (tn, pmr, testName) )
                
                if testsInTable != set(selTests):
                    updateInfoBox = True
                        
        if updateInfoBox:
            if not (len(selTests) > 0 and np.any(currentMask)):
                # CLEAR rawDataTable in info tab if:
                # 1. no test item is selected
                # 2. no duts selected (mask == all False)
                self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
                self.tmodel_raw.removeColumns(0, self.tmodel_raw.columnCount())
                return
            """
            1st col: Part ID
            2nd col: site
            3rd+ col: test items
            """
            hheaderLabels = [self.tr("Part ID"), self.tr("Test Head - Site")]
            vheaderLabels_base = [self.tr("Test Number"), self.tr("HLimit"), self.tr("LLimit"), self.tr("Unit")]
            vh_len = len(vheaderLabels_base)
            # clear raw data table
            self.tmodel_raw.removeColumns(0, self.tmodel_raw.columnCount())
            self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
            
            # Create the qitem for blank space
            def newBlankItem():
                blank_item = QtGui.QStandardItem("")
                blank_item.setTextAlignment(QtCore.Qt.AlignCenter)
                blank_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                blank_item.setData(QtGui.QColor("#0F80FF7F"), QtCore.Qt.BackgroundRole)
                return blank_item
                        
            # Append (vh_len) rows of blank items first
            for _ in range(vh_len):
                self.tmodel_raw.appendRow([newBlankItem() for _ in range(len(hheaderLabels))])
                
            # Append Part ID head & site to the table
            selectedDUTs = self.dutArray[currentMask]
            for dutIndex in selectedDUTs:
                qitemRow = ss.genQItemList(self.imageFont, 13 if isMac else 10, self.getDutSummaryOfIndex(dutIndex))
                id_head_site = [qitemRow[i] for i in range(len(hheaderLabels))]     # index0: ID; index1: Head/Site
                self.tmodel_raw.appendRow(id_head_site)
            # row header
            vheaderLabels = vheaderLabels_base + ["#%d"%(i+1) for i in range(len(selectedDUTs))]
            
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
            # Append Test data
            for testTuple in selTests:
                # get test value of selected DUTs
                testDict = self.getData(testTuple, selHeads, selSites)
                test_data_list = self.stringifyTestData(testDict, valueFormat)
                test_data_list.pop(0)   # remove test name
                test_stat_list = [True] * vh_len + list(map(ss.isPass, testDict["flagList"]))
                test_flagInfo_list = [""] * vh_len + self.generateDataFloatTips(testDict=testDict)
                hheaderLabels.append(testDict["TEST_NAME"])  # add test name to header list
                
                qitemCol = []
                for i, (item, stat, flagInfo) in enumerate(zip(test_data_list, test_stat_list, test_flagInfo_list)):
                    qitem = QtGui.QStandardItem(item)
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    # mark red when failed, flag == False == Fail
                    if stat == False: 
                        qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                        qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                    if flagInfo != "":
                        qitem.setToolTip(flagInfo)
                    if i < vh_len: qitem.setData(QtGui.QColor("#0F80FF7F"), QtCore.Qt.BackgroundRole)
                    qitemCol.append(qitem)
                self.tmodel_raw.appendColumn(qitemCol)
                        
            self.tmodel_raw.setHorizontalHeaderLabels(hheaderLabels)
            self.tmodel_raw.setVerticalHeaderLabels(vheaderLabels)
            self.ui.rawDataTable.horizontalHeader().setVisible(True)
            self.ui.rawDataTable.verticalHeader().setVisible(True)
                        
            self.resizeCellWidth(self.ui.rawDataTable, stretchToFit=False)
    
    
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
        self.proxyModel_list.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.ui.TestList.setModel(self.proxyModel_list)
        self.ui.TestList.setItemDelegate(StyleDelegateForTable_List(self.ui.TestList))
        
        self.sim_list_wafer = QtGui.QStandardItemModel()
        self.proxyModel_list_wafer = QtCore.QSortFilterProxyModel()
        self.proxyModel_list_wafer.setSourceModel(self.sim_list_wafer)
        self.proxyModel_list_wafer.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.ui.WaferList.setModel(self.proxyModel_list_wafer)        
        self.ui.WaferList.setItemDelegate(StyleDelegateForTable_List(self.ui.WaferList))
        # enable multi selection
        self.ui.TestList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.TestList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.ui.WaferList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.WaferList.setEditTriggers(QAbstractItemView.NoEditTriggers)        
        # get select model and connect func to change event
        self.selModel = self.ui.TestList.selectionModel()
        self.selModel.selectionChanged.connect(self.onSelect)
        
        self.selModel_wafer = self.ui.WaferList.selectionModel()
        self.selModel_wafer.selectionChanged.connect(self.onSelect)        
        
        
    def init_DataTable(self):
        # statistic table
        self.tmodel = QtGui.QStandardItemModel()
        self.ui.dataTable.setModel(self.tmodel)
        self.ui.dataTable.setItemDelegate(StyleDelegateForTable_List(self.ui.dataTable))
        # datalog info table
        self.tmodel_datalog = DatalogSqlQueryModel(self, 13 if isMac else 10)
        self.ui.datalogTable.setModel(self.tmodel_datalog)
        self.ui.datalogTable.setItemDelegate(StyleDelegateForTable_List(self.ui.datalogTable))
        # test summary table
        self.tmodel_raw = QtGui.QStandardItemModel()
        self.ui.rawDataTable.setModel(self.tmodel_raw)
        self.ui.rawDataTable.setItemDelegate(StyleDelegateForTable_List(self.ui.rawDataTable))
        self.ui.rawDataTable.addAction(self.ui.actionReadDutData_TS)   # add context menu for reading dut data
        # dut summary table
        self.tmodel_dut = ColorSqlQueryModel(self)
        self.proxyModel_tmodel_dut = DutSortFilter()
        self.proxyModel_tmodel_dut.setSourceModel(self.tmodel_dut)
        self.ui.dutInfoTable.setSortingEnabled(True)
        self.ui.dutInfoTable.setModel(self.proxyModel_tmodel_dut)
        self.ui.dutInfoTable.setSelectionBehavior(QAbstractItemView.SelectRows)     # select row only
        self.ui.dutInfoTable.setItemDelegate(StyleDelegateForTable_List(self.ui.dutInfoTable))
        self.ui.dutInfoTable.addAction(self.ui.actionReadDutData_DS)   # add context menu for reading dut data
        # file header table
        self.tmodel_info = QtGui.QStandardItemModel()
        self.ui.fileInfoTable.setModel(self.tmodel_info)
        self.ui.fileInfoTable.setSelectionMode(QAbstractItemView.NoSelection)
        # self.ui.fileInfoTable.setItemDelegate(StyleDelegateForTable_List(self.ui.fileInfoTable))
        # smooth scrolling
        self.ui.datalogTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.datalogTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dataTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dataTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.rawDataTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.rawDataTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dutInfoTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dutInfoTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)        
        self.ui.fileInfoTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
                            
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
                    [qele.setData(qfont, QtCore.Qt.FontRole) for qele in qitemRow]
                self.tmodel_info.appendRow(qitemRow)
            
            # horizontalHeader.resizeSection(0, 250)
            horizontalHeader.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            for column in range(1, horizontalHeader.count()):
                horizontalHeader.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
            
            # resize to content to show all texts, then add additional height to each row
            for row in range(self.tmodel_info.rowCount()):
                verticalHeader.setSectionResizeMode(row, QtWidgets.QHeaderView.ResizeToContents)
                newHeight = verticalHeader.sectionSize(row) + 20
                verticalHeader.setSectionResizeMode(row, QtWidgets.QHeaderView.Fixed)
                verticalHeader.resizeSection(row, newHeight)
    
    
    def updateDutSummaryTable(self):
        header = self.ui.dutInfoTable.horizontalHeader()
        header.setVisible(True)
        
        self.tmodel_dut.setQuery(QtSql.QSqlQuery(ss.DUT_SUMMARY_QUERY, self.db_dut))
        
        for column in range(1, header.count()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
        
        
    def updateGDR_DTR_Table(self):        
        header = self.ui.datalogTable.horizontalHeader()
        header.setVisible(True)
        
        self.tmodel_datalog.setQuery(QtSql.QSqlQuery(ss.DATALOG_QUERY, self.db_dut))
                    
        for column in [1, 2]:
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
        self.ui.datalogTable.resizeRowsToContents()
        
        
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
    
    
    # TODO
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
            selTests = self.getSelectedTests()
            selSites = self.getCheckedSites()
            selHeads = self.getCheckedHeads()
            hsNotChanged = (self.preHeadSelection == set(selHeads) and self.preSiteSelection == set(selSites))
            testNotChanged = (self.preTestSelection == set(selTests))
            
            # prepare the data for plot and table, skip in Bin & Wafer tab to save time
            if (not testNotChanged) and (not currentTab in [tab.Bin, tab.Wafer]): 
                # get (test_num, test_name)
                # pmr is not used, since MPR test preparation contains data for all pmr pins
                # self.prepareData([(tup[0], tup[2]) for tup in selTests])
                pass
                        
            # update bin chart only if sites changed and previous tab is not bin chart
            updateTab = False
            if hsNotChanged:
                # head & site selection is not changed
                if currentTab == tab.Bin and self.preTab == tab.Bin:
                    # do not update
                    updateTab = False
                else:
                    # in case tab or test num changed
                    updateTab = True
            else:
                # head & site selection is changed
                updateTab = True
                # filter dut summary table if in Info tab and head & site changed
                if currentTab == tab.Info:
                    self.proxyModel_tmodel_dut.updateHeadsSites(selHeads, selSites)
                    
            if updateTab:
                self.updateStatTableContent()       # update table
                # self.updateTabContent()             # update tab
            
            # always update pre selection at last
            self.preHeadSelection = set(selHeads)
            self.preSiteSelection = set(selSites)
            self.preTestSelection = set(selTests)
    
    
    def onSiteChecked(self):
        # call onSelect if there's item selected in listView
        
        # it is safe to call onSelect directly without any items in listView
        # the inner function will detect the items and will skip if there is none
        self.onSelect()
    
    
    # TODO
    def isTestFail(self, testTuple):
        testID = (testTuple[0], testTuple[-1])
        if testID in self.failCntDict:
            # test synopsis for current test item contains valid fail count
            failCount = self.failCntDict[testID]
            if failCount > 0:
                return "testFailed"
            elif failCount == 0:
                # if user do not need to check Cpk, return to caller
                if self.settingParams.checkCpk:
                    failStateChecked = True      # avoid re-check fail state when calculating Cpk
                else:
                    return "testPassed"
            else:
                failStateChecked = False

            # when need to check Cpk, fail count for this test_num in TSR is invalid, or TSR is not omitted whatsoever
            # read test data from all heads and sites
            self.prepareData([testID], cacheData=True)
            parsedData = self.selData[testID]
            if not failStateChecked:
                for stat in map(ss.isPass, parsedData["flagList"]):
                    if stat == False:
                        self.failCntDict[testID] = 1
                        return "testFailed"
                    
            self.failCntDict[testID] = 0
            if self.settingParams.checkCpk:
                # if all tests passed, check if cpk is lower than the threshold
                parsedData["dataList"] = np.array(parsedData["dataList"], dtype='float64')
                for head in self.availableHeads:
                    for site in self.availableSites:
                        cpk = self.getData(testTuple, [head], [site])["Cpk"]
                        if not np.isnan(cpk):
                            # check cpk only if it's valid
                            if cpk < self.settingParams.cpkThreshold:
                                return "cpkFailed"
            
            return "testPassed"
        
        
    def clearTestItemBG(self):
        # reset test item background color when cpk threshold is reset
        for i in range(self.sim_list.rowCount()):
            qitem = self.sim_list.item(i)
            qitem.setData(QtGui.QColor.Invalid, QtCore.Qt.ForegroundRole)
            qitem.setData(QtGui.QColor.Invalid, QtCore.Qt.BackgroundRole)
                        
                       
    def refreshTestList(self):
        if self.settingParams.sortTestList == "Number":
            self.updateModelContent(self.sim_list, sorted(self.completeTestList, key=lambda x: self.getTestTuple(x)))
        elif self.settingParams.sortTestList == "Name":
            self.updateModelContent(self.sim_list, sorted(self.completeTestList, key=lambda x: x.split("\t")[-1]))
        else:
            self.updateModelContent(self.sim_list, self.completeTestList)
    
    
                
    def updateTabContent(self, forceUpdate=False):
        '''
        update logic:
        if tab is not changed, insert canvas and toolbars based on test num and site
        if tab is changed, clear all and then add canvas
        '''
        tabType = self.ui.tabControl.currentIndex()
        self.clearOtherTab(tabType)     # clear other tabs' content to save memory
        # check if redraw is required
        # if previous tab or current tab is Wafer, no need to redraw as it has an independent listView
        tabChanged = (tabType != self.preTab)
        reDrawTab = tabChanged and (self.preTab != tab.Wafer) and (tabType != tab.Wafer)
        
        self.preTab = tabType       # save tab index everytime tab updates
        selTests = self.getSelectedTests()    # (test_num, test_name) in trend/histo, (wafer_index, wafer_name) in wafer
        selSites = self.getCheckedSites()
        selHeads = self.getCheckedHeads()
        
        # update Test Data table in info tab only when test items are selected
        if tabType == tab.Info:
            self.onInfoBoxChanged()
            return
        
        '''
        ***This following code is used for finding the index of the new image to add or old image to delete.***
                
        tabLayout only contans 1 widgets -- qfigWidget, which is the parent of all matplot canvas and toolbars
        qfigWidget.children(): 1st is qfigLayout, others are canvas
        qfigLayout contains the references to all canvas and toolbars
        qfigLayout.itemAt(index).widget(): canvas or toolbars
        canvas and toolbars can be deleted by  qfigLayout.itemAt(index).widget().setParent(None)
        '''
        canvasIndexDict = {}
        # get tab layout
        tabLayout: QtWidgets.QVBoxLayout = self.tab_dict[tabType]["layout"]
        
        if reDrawTab or forceUpdate:
            # clear all contents in current tab
            [ss.deleteWidget(tabLayout.itemAt(i).widget()) for i in range(tabLayout.count())[::-1]]
            # add new widget
            qfigWidget = QtWidgets.QWidget(self.tab_dict[tabType]["scroll"])
            qfigLayout = QtWidgets.QVBoxLayout()
            qfigWidget.setLayout(qfigLayout)
            tabLayout.addWidget(qfigWidget)
            # clear cursor dict in current tab
            if tabType == tab.Trend:
                matchString = "trend"
            elif tabType == tab.Histo:
                matchString = "histo"
            elif tabType == tab.Bin:
                matchString = "bin"
            else:
                matchString = "wafer"
            for key in list(self.cursorDict.keys()):
                # remove cursors, get a default in case key not found (only happens when data is invalid in some sites)
                if key.startswith(matchString):
                    self.cursorDict.pop(key, None)
        else:
            try:
                # get testnum/site of current canvas/toolbars and corresponding widget index
                qfigWidget: QtWidgets.QWidget = self.tab_dict[tabType]["layout"].itemAt(0).widget()
                qfigLayout: QtWidgets.QVBoxLayout = qfigWidget.children()[0]
            except AttributeError:
                # in case there are no canvas (e.g. initial state), add new widget
                qfigWidget = QtWidgets.QWidget(self.tab_dict[tabType]["scroll"])
                qfigLayout = QtWidgets.QVBoxLayout()
                qfigWidget.setLayout(qfigLayout)
                tabLayout.addWidget(qfigWidget)
                
            canvasIndexDict = ss.getCanvasDicts(qfigLayout)    # get current indexes
                    
            # delete canvas/toolbars that are not selected
            canvasIndexDict_reverse = {v:k for k, v in canvasIndexDict.items()}
            # must delete from large index, invert dict to loop from large index
            for index in sorted(canvasIndexDict_reverse.keys(), reverse=True):
                (mp_head, mp_test_num, mp_pmr, mp_site, mp_test_name) = canvasIndexDict_reverse[index]
                # if not in Bin tab: no test item selected/ test item is unselected, remove
                # if sites are unselected, remove
                if (tabType != tab.Bin and (len(selTests) == 0 or not (mp_test_num, mp_pmr, mp_test_name) in selTests)) or (not mp_site in selSites) or (not mp_head in selHeads):
                    # bin don't care about testNum
                    ss.deleteWidget(qfigLayout.itemAt(index).widget())
                    if tabType == tab.Trend:
                        matchString = f"trend_{mp_head}_{mp_test_num}_{mp_pmr}_{mp_site}_{mp_test_name}"
                    elif tabType == tab.Histo:
                        matchString = f"histo_{mp_head}_{mp_test_num}_{mp_pmr}_{mp_site}_{mp_test_name}"
                    elif tabType == tab.Bin:
                        matchString = f"bin_{mp_head}_{mp_test_num}_{mp_site}"
                    else:
                        matchString = f"wafer_{mp_head}_{mp_test_num}_{mp_site}"
                        
                    for key in list(self.cursorDict.keys()):
                        # remove cursors, get a default in case key not found (only happens when data is invalid in some sites)
                        if key.startswith(matchString):
                            self.cursorDict.pop(key, None)
                    
            canvasIndexDict = ss.getCanvasDicts(qfigLayout)    # update after deleting some images
                    
        # generate drawings in trend , histo and bin, but bin doesn't require test items selection
        if tabType == tab.Bin or (tabType in [tab.Trend, tab.Histo, tab.Wafer] and len(selTests) > 0):
            if tabType == tab.Bin:
                # bin chart is independent of test items
                for site in selSites[::-1]:
                    for head in selHeads[::-1]:
                        if (head, 0, 0, site) in canvasIndexDict:
                            # no need to draw image for a existed testnum and site
                            continue
                        calIndex = ss.calculateCanvasIndex(0, head, site, 0, "", canvasIndexDict)
                        # draw
                        self.genPlot(head, site, (0, 0, ""), tabType, updateTab=True, insertIndex=calIndex)
            else:
                # trend, histo, wafer
                for test_num, pmr, test_name in selTests[::-1]:
                    for site in selSites[::-1]:
                        for head in selHeads[::-1]:
                            if (head, test_num, pmr, site, test_name) in canvasIndexDict:
                                # no need to draw image for a existed testnum and site
                                continue
                            calIndex = ss.calculateCanvasIndex(test_num, head, site, pmr, test_name, canvasIndexDict)
                            # draw
                            self.genPlot(head, site, (test_num, pmr, test_name), tabType, updateTab=True, insertIndex=calIndex)
        # remaining cases are: no test items in tab trend, histo, wafer
        else:
            # when no test item is selected, clear trend, histo & wafer tab content
            if tabType in [tab.Trend, tab.Histo, tab.Wafer]:
                tabLayout = self.tab_dict[tabType]["layout"]
                # clear current content in the layout in reverse order - no use
                [ss.deleteWidget(tabLayout.itemAt(i).widget()) for i in range(tabLayout.count())]
                if tabType == tab.Trend:
                    matchString = "trend"
                elif tabType == tab.Histo:
                    matchString = "histo"
                else:
                    matchString = "wafer"

                for key in list(self.cursorDict.keys()):
                    if key.startswith(matchString):
                        self.cursorDict.pop(key, None)
            
            
    
    # TODO
    def prepareDUTSummaryForExporter(self, selHeads, selSites, **kargs):
        '''This method is for providing data for report generator'''
        result = []
        
        if ("testTuple" in kargs and isinstance(kargs["testTuple"], tuple)):
            # return test data of the given test_num
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
            testTuple = kargs["testTuple"]
            # get test value of selected DUTs
            testDict = self.getData(testTuple, selHeads, selSites)
            test_data_list = self.stringifyTestData(testDict, valueFormat)
            test_stat_list = [True] * 5 + list(map(ss.isPass, testDict["flagList"]))  # TestName, TestNum, HL, LL, Unit
            result = [test_data_list, test_stat_list]
        
        elif "testTuple" not in kargs:
            # return dut info
            currentMask = self.getMaskFromHeadsSites(selHeads, selSites)
            selectedDUTs = self.dutArray[currentMask]
            for dutIndex in selectedDUTs:
                # decode bytes to str
                result.append(self.getDutSummaryOfIndex(dutIndex))

        return result
        
    
    def resizeCellWidth(self, tableView, stretchToFit = True):
        # set column width
        header = tableView.horizontalHeader()
        rowheader = tableView.verticalHeader()
        rowheader.setDefaultAlignment(QtCore.Qt.AlignCenter)
        
        # set to ResizeToContents mode and get the minimum width list
        min_widthList = []
        for column in range(header.model().columnCount()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
            min_widthList += [header.sectionSize(column)]   

        # calcualte the width for each column
        hHeaderWidth = header.width()
        WL = []
        minWidth = sum(min_widthList)
        if stretchToFit and minWidth <= hHeaderWidth:
            delta_wid = int((hHeaderWidth - minWidth) / len(min_widthList))
            remain_wid = hHeaderWidth - delta_wid * len(min_widthList) - minWidth
            # add delta to each element
            for w in min_widthList:
                WL.append(w + delta_wid)
            # add remaining to the first column
            WL[0] = WL[0] + remain_wid
        else:
            # too many columns that part of contents will definity be covered, add more space to column
            WL = [w + 20 for w in min_widthList]
                
        for column, width in enumerate(WL):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
            # use the calculated width
            header.resizeSection(column, width)        
            
            
    def updateStatTableContent(self):
        tabType = self.ui.tabControl.currentIndex()
        # clear table
        self.tmodel.removeRows(0, self.tmodel.rowCount())
        
        selTests = self.getSelectedTests()
        horizontalHeader = self.ui.dataTable.horizontalHeader()
        verticalHeader = self.ui.dataTable.verticalHeader()
        floatFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
        
        if tabType == tab.Info or tabType == tab.Trend or tabType == tab.Histo:
            d = self.data_interface.getTestStatistics(selTests, 
                                                      self.getCheckedHeads(), 
                                                      self.getCheckedSites(), 
                                                      floatFormat=floatFormat)
            HHeader = d["HHeader"]
            indexOfFail = HHeader.index("Fail Num")
            indexOfCpk = HHeader.index("Cpk")

            for row in d["Rows"]:
                # create QStandardItem and set TextAlignment
                qitemList = []
                for ind, item in enumerate(row):
                    qitem = QtGui.QStandardItem(item)
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    if ind == indexOfFail:
                        if item != "0": 
                            qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                            qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                    elif ind == indexOfCpk:
                        if item != "N/A" and item != "∞":
                            if float(item) < self.settingParams.cpkThreshold:
                                qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                                qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
                    qitemList.append(qitem)
                self.tmodel.appendRow(qitemList)
            
            # horizontal header setting
            self.tmodel.setHorizontalHeaderLabels(list(map(self.tr, HHeader)))
            self.tmodel.setColumnCount(len(HHeader))
            horizontalHeader.setVisible(True)
            # vertical header setting
            # must set AFTER inserting data rows
            # otherwise there will be empty rows
            self.tmodel.setVerticalHeaderLabels(d["VHeader"])
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(25)
            verticalHeader.setDefaultAlignment(QtCore.Qt.AlignCenter)
            
            # resize table
            self.resizeCellWidth(self.ui.dataTable)
                
        elif tabType == tab.Bin:
            d = self.data_interface.getBinStatistics(self.getCheckedHeads(), 
                                                     self.getCheckedSites())
            
            for row, isHBIN in zip(d["Rows"], d["isHBIN"]):
                qitemList = []
                for dataString, bin_num in row:
                    qitem = QtGui.QStandardItem(dataString)
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    # set color
                    color_dict = self.settingParams.hbinColor if isHBIN else self.settingParams.sbinColor
                    if bin_num != -1:
                        bc = QtGui.QColor(color_dict[bin_num])
                        fc = ss.getProperFontColor(bc)
                        qitem.setData(bc, QtCore.Qt.BackgroundRole)
                        qitem.setData(fc, QtCore.Qt.ForegroundRole)
                    qitemList.append(qitem)
                self.tmodel.appendRow(qitemList)
        
            # horizontal header setting
            self.tmodel.setHorizontalHeaderLabels([])
            # set column size, better than remove columns 
            # cuz the latter will cause flicking when updating data
            self.tmodel.setColumnCount(d["maxLen"])
            horizontalHeader.setVisible(False)
            # vertical header setting
            self.tmodel.setVerticalHeaderLabels(d["VHeader"])
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(35)
            verticalHeader.setDefaultAlignment(QtCore.Qt.AlignCenter)
            
            self.resizeCellWidth(self.ui.dataTable, stretchToFit=False)
        
        else:
            # wafer tab
            d = self.data_interface.getWaferStatistics(selTests, 
                                                       self.getCheckedSites())
            color_dict = self.settingParams.sbinColor
            for row in d["Rows"]:
                qitemList = []
                for dataString, bin_num in row:
                    qitem = QtGui.QStandardItem(dataString)
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    # set color
                    if bin_num != -1:
                        bc = QtGui.QColor(color_dict[bin_num])
                        fc = ss.getProperFontColor(bc)
                        qitem.setData(bc, QtCore.Qt.BackgroundRole)
                        qitem.setData(fc, QtCore.Qt.ForegroundRole)
                    qitemList.append(qitem)
                self.tmodel.appendRow(qitemList)
        
            # horizontal header setting
            self.tmodel.setHorizontalHeaderLabels([])
            # set column size, better than remove columns 
            # cuz the latter will cause flicking when updating data
            self.tmodel.setColumnCount(d["maxLen"])
            horizontalHeader.setVisible(False)
            # vertical header setting
            self.tmodel.setVerticalHeaderLabels(d["VHeader"])
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(35)
            verticalHeader.setDefaultAlignment(QtCore.Qt.AlignCenter)
            self.resizeCellWidth(self.ui.dataTable, stretchToFit=False)
                
    
    def genPlot(self, head:int, site:int, testTuple:tuple, tabType:tab, **kargs):
        '''testTuple: (test_num, pmr, test_name)'''
        exportImg: bool = ("exportImg" in kargs) and (kargs["exportImg"] == True)
        # create fig & canvas
        figsize = (10, 4)
        fig = plt.Figure(figsize=figsize)
        fig.set_tight_layout(True)
                
        if tabType == tab.Trend:   # Trend
            ax, trendLines = self.genTrendPlot(fig, head, site, testTuple)
            
        elif tabType == tab.Histo:   # Histogram
            ax, recGroups = self.genHistoPlot(fig, head, site, testTuple)
            
        elif tabType == tab.Bin:   # Bin Chart
            axs, recGroups = self.genBinPlot(fig, head, site)
            
        elif tabType == tab.Wafer:   # Wafermap
            ax = self.genWaferPlot(fig, head, site, testTuple[0])
            
        if exportImg:
            imgData = io.BytesIO()
            fig.savefig(imgData, format="png", dpi=200, bbox_inches="tight")
            return imgData
        else:
            # put figure in a canvas and display in pyqt widgets
            test_num, pmr, test_name = testTuple
            canvas = PlotCanvas(fig)
            # binds to widget
            if "updateTab" in kargs and kargs["updateTab"] and "insertIndex" in kargs:
                qfigWidget = self.tab_dict[tabType]["layout"].itemAt(0).widget()
                qfigLayout = qfigWidget.children()[0]
                
                canvas.bindToUI(qfigWidget)
                canvas.head = head
                canvas.site = site
                canvas.test_num = test_num
                canvas.pmr = pmr
                canvas.test_name = test_name
                canvas.priority = head + test_num + pmr + site
                # place the fig and toolbar in the layout
                index = kargs["insertIndex"]
                qfigLayout.insertWidget(index, canvas)
                
            def connectMagCursor(_canvas:PlotCanvas, cursor:MagCursor, _ax):
                _canvas.mpl_connect('motion_notify_event', cursor.mouse_move)
                _canvas.mpl_connect('resize_event', cursor.canvas_resize)
                _canvas.mpl_connect('pick_event', cursor.on_pick)
                _canvas.mpl_connect('key_press_event', cursor.key_press)
                _canvas.mpl_connect('key_release_event', cursor.key_release)                
                _canvas.mpl_connect('button_press_event', cursor.button_press)
                _ax.callbacks.connect('xlim_changed', cursor.canvas_resize)
                _ax.callbacks.connect('ylim_changed', cursor.canvas_resize)
                # cursor.copyBackground()   # not required, as updating the tab will trigger canvas resize event
            
            if tabType == tab.Trend and len(trendLines) > 0:
                # connect magnet cursor
                for i, trendLine in enumerate(trendLines):
                    cursorKey = "trend_%d_%d_%d_%d_%s_%d"%(head, test_num, pmr, site, test_name, i)
                    self.cursorDict[cursorKey] = MagCursor(line=trendLine,
                                                           mainGUI=self)
                    connectMagCursor(canvas, self.cursorDict[cursorKey], ax)
                    
            elif tabType == tab.Histo and len(recGroups) > 0:
                for i, recGroup in enumerate(recGroups):
                    cursorKey = "histo_%d_%d_%d_%d_%s_%d"%(head, test_num, pmr, site, test_name, i)
                    self.cursorDict[cursorKey] = MagCursor(histo=recGroup,
                                                           mainGUI=self)
                    connectMagCursor(canvas, self.cursorDict[cursorKey], ax)
                    
            elif tabType == tab.Bin:
                for i, (ax_bin, recGroup) in enumerate(zip(axs, recGroups)):
                    if len(recGroup) == 0:
                        # skip if no bins in the plot
                        continue
                    cursorKey = "bin_%d_%d_%d_%d"%(head, test_num, site, i)
                    self.cursorDict[cursorKey] = MagCursor(binchart=recGroup,
                                                           mainGUI=self)
                    connectMagCursor(canvas, self.cursorDict[cursorKey], ax_bin)
            
            elif tabType == tab.Wafer and len(ax.collections) > 0:
                cursorKey = "wafer_%d_%d_%d"%(head, test_num, site)
                self.cursorDict[cursorKey] = MagCursor(wafer=ax.collections,
                                                       mainGUI=self,
                                                       site=site,
                                                       wafer_num=test_num)
                connectMagCursor(canvas, self.cursorDict[cursorKey], ax)
            
            
    
    def updateCursorPrecision(self):
        for _, cursor in self.cursorDict.items():
            cursor.updatePrecision(self.settingParams.dataPrecision, self.settingParams.dataNotation)
            
            
    def clearOtherTab(self, currentTab):
        # if currentTab != tab.Info:
        #     # clear raw data table
        #     self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
        #     self.tmodel_raw.removeColumns(0, self.tmodel_raw.columnCount())
        
        # clear other tabs' images
        if currentTab != tab.Wafer:
            # wafer tab and other tab is separated in the app
            # we don't want to clean trend/histo/bin when we are in wafer tab
            [[ss.deleteWidget(self.tab_dict[key]["layout"].itemAt(index).widget()) for index in range(self.tab_dict[key]["layout"].count())] if key != currentTab else None for key in [tab.Trend, tab.Histo, tab.Bin]]
            
            if currentTab == tab.Trend:
                # clear magic cursor as well, it contains copies of figures
                matchString = "trend"
            elif currentTab == tab.Histo:
                matchString = "histo"
            else:
                matchString = "bin"

            for key in list(self.cursorDict.keys()):
                # keep wafer and current tabs' cursors
                if not (key.startswith(matchString) or key.startswith("wafer")):
                    self.cursorDict.pop(key, None)
            
        gc.collect()
    
    
    def clearAllContents(self):
        # clear raw data table
        self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
        self.tmodel_raw.removeColumns(0, self.tmodel_raw.columnCount())
        # clear stat table
        self.tmodel.removeRows(0, self.tmodel.rowCount())
        # clear tabs' images
        [[ss.deleteWidget(self.tab_dict[key]["layout"].itemAt(index).widget()) for index in range(self.tab_dict[key]["layout"].count())] for key in [tab.Trend, tab.Histo, tab.Bin, tab.Wafer]]
        # clear magic cursor as well, it contains copies of figures
        self.cursorDict = {}
        
        self.preTestSelection = set()
        self.preHeadSelection = set()
        self.preSiteSelection = set()
        gc.collect()
    
    
    def callFileLoader(self, paths: list[str]):
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
            # get dutArray and its site info
            self.dutArrays = self.data_interface.dutArrays
            self.dutSiteInfo = self.data_interface.dutSiteInfo
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
            self.updateStatTableContent()
            self.updateTabContent(forceUpdate=True)

    
    @Slot(str, bool, bool, bool)
    def updateStatus(self, new_msg, info=False, warning=False, error=False):
        self.statusBar().showMessage(new_msg)
        if info: 
            QtWidgets.QMessageBox.information(self, self.tr("Info"), new_msg)
        elif warning: 
            QtWidgets.QMessageBox.warning(self, self.tr("Warning"), new_msg)
            logger.warning(new_msg)
        elif error:
            QtWidgets.QMessageBox.critical(self, self.tr("Error"), new_msg)
            # sys.exit()
        QApplication.processEvents()
        
    
    def eventFilter(self, object, event):
        # modified from https://stackoverflow.com/questions/18001944/pyqt-drop-event-without-subclassing
        if object in [self.ui.TestList, self.ui.tabControl, self.ui.dataTable]:
            if (event.type() == QtCore.QEvent.DragEnter):
                if event.mimeData().hasUrls():
                    event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
                    return True
                else:
                    event.ignore()
                    return False
                    
            if (event.type() == QtCore.QEvent.Drop):
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
    font_names = []
    defaultFontNames = FontNames()
    # reverse to put courier at the rear
    for fn in sorted(os.listdir(os.path.join(sys.rootFolder, "fonts")), key=lambda x:x.lower(), reverse=True):
        if not fn.endswith(".ttf"): continue
        fontPath = os.path.join(sys.rootFolder, "fonts", fn)
        QtGui.QFontDatabase.addApplicationFont(fontPath)
        fm.fontManager.addfont(fontPath)
        font_name = fm.FontProperties(fname=fontPath).get_name()
        font_names.append(font_name)
        # update default fonts if special prefix is found
        if fn.startswith("cn_"):
            defaultFontNames.Chinese = font_name
        elif fn.startswith("en_"):
            defaultFontNames.English = font_name

    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = font_names
    
    pathFromArgs = [item for item in sys.argv[1:] if os.path.isfile(item)]
    window = MyWindow(defaultFontNames)
    window.show()
    if pathFromArgs:
        window.callFileLoader(pathFromArgs)
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    run()