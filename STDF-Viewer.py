#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
# -----
# Last Modified: Sat Oct 10 2026
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
from deps.StdLoader import StdfLoader
from deps.ViewerInstance import ViewerInstance
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

# application name is required to use
# `StandardLocation.AppDataLocation`
QtCore.QCoreApplication.setApplicationName("STDF-Viewer")

Version = "V4.1.0"

if getattr(sys, "frozen", False):
    resourceFolder = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    # following files are put to AppDataLocation when FROZEN:
    # - STDF-Viewer.config
    # - Logs
    # - Databases
    # - User-added fonts
    appDataFolder = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.AppDataLocation)
else:
    # dev env, use .py source folder to load/save everything
    resourceFolder = os.path.dirname(os.path.abspath(__file__))
    appDataFolder = resourceFolder

setattr(sys, "resourceFolder", resourceFolder)
setattr(sys, "appDataFolder", appDataFolder)
setattr(sys, "CONFIG_PATH", os.path.join(appDataFolder, "STDF-Viewer.config"))

# logger
init_logger(appDataFolder)
logger = logging.getLogger(LOG_NAME)


class signals4MainUI(QtCore.QObject):
    dataInterfaceSignal = Signal(object)  # get `DataInterface` from loader
    statusSignal = Signal(str, bool, bool, bool)   # status bar
    loadStatusSignal = Signal(str, int)            # status bar, loader messages with a timeout
    showDutDataSignal_TrendHisto = Signal(list)     # trend & histo
    showDutDataSignal_Bin = Signal(list)            # bin chart
    showDutDataSignal_Wafer = Signal(list)          # wafer
    metadataSignal = Signal(object)                 # File Info read before the database



class StdfApplication(QApplication):
    '''
    QApplication subclass for handling
    stdf file open requests and drag-and-drop events.
    '''

    filesOpenSignal = Signal(list)

    def __init__(self, argv):
        super().__init__(argv)
        self._openRequests = []
        self._dropTargets = []
        # a copy of sys.argv for macOS, because command line args
        # are converted to QFileOpenEvent on macOS, the list is
        # for filtering unwanted QFileOpenEvent.
        self._cliPaths = {os.path.realpath(p) for p in sys.argv} if isMac else set()
        # function to determine if the app can accept dropped files,
        # updated by `MyWindow`.
        self.canAcceptDrop = lambda: True


    def acceptDropsOn(self, *widgets):
        '''
        Handle the files dropped on the given widgets.
        '''
        for widget in widgets:
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)
        self._dropTargets.extend(widgets)


    def event(self, e):
        if e.type() == QtCore.QEvent.Type.FileOpen:
            # only macOS has this event
            path = e.url().toLocalFile() or e.file()
            # macOS AppKit converts cli args as file open requests,
            # ignore any request whose path belongs to cli so that:
            # 1. non-stdf path (such as *.py) will not be triggered.
            # 2. avoid duplicate trigger.
            # 3. real finder file event is unaffected.
            if path and os.path.realpath(path) not in self._cliPaths:
                self._openRequests.append(path)
                # ensure all files are appended before calling `_openRequestedFiles`
                QtCore.QTimer.singleShot(0, self._openRequestedFiles)
            return True
        return super().event(e)


    def _openRequestedFiles(self):
        if self._openRequests:
            paths, self._openRequests = self._openRequests, []
            self.filesOpenSignal.emit(paths)


    def eventFilter(self, widget, event):
        # modified from https://stackoverflow.com/questions/18001944/pyqt-drop-event-without-subclassing
        if widget not in self._dropTargets:
            return False

        if event.type() == QtCore.QEvent.Type.DragEnter:
            if event.mimeData().hasUrls():
                # the drop event only follows once this one is accepted
                event.accept()
                return True
            event.ignore()
            return False

        if event.type() == QtCore.QEvent.Type.Drop and event.mimeData().hasUrls():
            if not self.canAcceptDrop():
                # a load is in progress, ignore any dropped files
                event.ignore()
            else:
                event.accept()
                self.filesOpenSignal.emit([url.toLocalFile()
                                           for url in event.mimeData().urls()])
            return True

        return False



class MyWindow(QtWidgets.QMainWindow):
    # number of checkboxes per row in
    # file/head/site selection grids
    CHECKBOX_PER_ROW = 4
    
    def __init__(self):
        super(MyWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # whether the load currently running (or the last one) got a database
        self._dbProduced = False
        # whether a load is running right now
        self._fileLoading = False
        # the database to go back to when a load is abandoned
        self._preDB = ""
        # whether the user gave up on the load that is running
        self._abandoned = False
        # the window asked to close while a load was running
        self._closeOnFinish = False
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
        # dict to store the file id checkbox objects
        self.file_cb_dict = {}
        # full File Info rows of the loaded database, the table shows a filtered view
        self.fileMetaData = []
        # hide file selection until multiple files are loaded
        self.ui.file_selection.hide()
        # track widgets whose click signal has already been connected
        self._connectedCbs = set()
        self.translatorUI = QTranslator(self)
        self.translatorCode = QTranslator(self)
        # init and connect signals
        self.signals = signals4MainUI()
        self.signals.dataInterfaceSignal.connect(self.updateData)
        self.signals.statusSignal.connect(self.updateStatus)
        self.signals.loadStatusSignal.connect(self.updateLoadStatus)
        self.signals.metadataSignal.connect(self.showEarlyFileInfo)
        self.signals.showDutDataSignal_TrendHisto.connect(self.onReadDutData_TrendHisto)
        self.signals.showDutDataSignal_Bin.connect(self.onReadDutData_Bin)
        self.signals.showDutDataSignal_Wafer.connect(self.onReadDutData_Wafer)
        # init loader
        self.loader = StdfLoader(self.signals, self)
        self.loader.signals.closeSignal.connect(self.onLoaderFinished)
        self.loader.signals.progressBarSignal.connect(self.onLoaderProgress)
        # sub windows
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
        self.connectCheckbox()
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
        # the dialog stays hidden, so the progress bar uses its configuration
        self.ui.loaderProgress.hide()
        self.ui.stopLoadButton.hide()
        self.ui.stopLoadButton.clicked.connect(self.onTerminateLoad)
        # disable wafer tab in default
        self.ui.tabControl.setTabEnabled(tab.Wafer, False)
        # clean up before exiting
        atexit.register(self.onExit)
        # set language after initing subwindow & reading config
        self.changeLanguage()
        self.restorePreviousSession()
        # hide unfinished feature
        self.ui.tabControl.setTabVisible(tab.PPQQ, False)
        self.ui.tabControl.setTabVisible(tab.Correlate, False)
        
        
    def checkNewVersion(self):
        try:
            res = rq.urlopen("https://api.github.com/repos/noonchen/STDF-Viewer/releases/latest")
            resDict = json.loads(res.read())
            latestTag = resDict["tag_name"]
            changeList = resDict["body"]
            releaseLink = resDict["html_url"]
            
            latestVer = tuple(int(x) for x in latestTag.lstrip("vV").split("."))
            currentVer = tuple(int(x) for x in Version.lstrip("vV").split("."))

            if latestVer > currentVer:
                # show dialog for updating
                msgBox = QMessageBox(self)
                msgBox.setWindowFlag(Qt.WindowType.FramelessWindowHint)
                msgBox.setTextFormat(Qt.TextFormat.RichText)
                msgBox.setText("<span style='font-size:15px'>{0}&nbsp;&nbsp;\
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
        curLang = settings.gen.language
        font = settings.gen.font
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
        '''
        Open input STDF files in compare mode,
        prompting the user to select files if none are provided.
        '''
        if not files:
            files, _ = QFileDialog.getOpenFileNames(self, caption=self.tr("Select STDF Files To Open"), 
                                                    directory=getSetting().gen.recent_dir, 
                                                    filter=self.tr(FILE_FILTER),)
        else:
            files = [f for f in map(os.path.normpath, files) if os.path.isfile(f)]
            
        if files:
            # store folder path
            updateRecentFolder(files[0])
            self.callFileLoader([[f] for f in files])
              
    
    def onMerge(self):
        self.mergePanel.showUI()
    
    
    def onLoadSession(self):
        p, _ = QFileDialog.getOpenFileName(self, caption=self.tr("Select a STDF-Viewer session"), 
                                           directory=getSetting().gen.recent_dir, 
                                           filter=self.tr("Database (*.db)"))
        if p:
            isvalid, msg = rust_stdf_helper.validate_session(p)
            if isvalid:
                self.loadDatabase(p)
            else:
                QMessageBox.warning(self, self.tr("Warning"), 
                                    self.tr("This session cannot be loaded: \n{}\n\n{}").format(p, msg))
    
    
    def onSaveSession(self):
        if self.data_interface is not None:
            dbPath = self.data_interface.dbPath
            # the WAL is part of the session while it is open, count it too
            dbSize = os.stat(dbPath).st_size
            walPath = dbPath + "-wal"
            if os.path.exists(walPath):
                dbSize += os.stat(walPath).st_size
            dbSize /= 2**20
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
                    # SQLite online backup: consistent even while the database
                    # is open and background indexing is still running
                    rust_stdf_helper.save_session(pIn, pOut)
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
                                           directory=getSetting().gen.recent_dir, 
                                           filter=self.tr("TTF Font (*.ttf)"))
        if not p:
            return
        
        if QtGui.QFontDatabase.addApplicationFont(p) < 0:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("This font cannot be loaded:\n{}").format(p))
        else:
            # a user font belongs to the writable data folder, not to the bundle
            fontFolder = os.path.join(sys.appDataFolder, "fonts")
            os.makedirs(fontFolder, exist_ok=True)
            shutil.copy(src=p, dst=fontFolder, follow_symlinks=True)
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
        # Close the Rust fetcher before QtSql.
        if self.data_interface:
            currentDB = self.data_interface.dbPath
            self.data_interface.close()
        else:
            currentDB = "???"
        self.db_dut.close()
        # No connection holds the database now,
        # fold the WAL back into the db file.
        if currentDB != "???" and os.path.isfile(currentDB):
            try:
                rust_stdf_helper.checkpoint_truncate(currentDB)
            except Exception:
                logger.warning("Could not checkpoint the WAL of %s", currentDB, exc_info=True)
        # save settings to file
        dumpConfigFile()
        # clean generated databases; keep the current one and any sidecar left
        # behind when the checkpoint above failed
        dbFolder = os.path.join(sys.appDataFolder, "logs")
        currentName = os.path.basename(currentDB)
        for f in os.listdir(dbFolder):
            # keep the current database and any sidecar of it
            if f == currentName or f.startswith(currentName + "-"):
                continue
            # an interrupted run can leave -journal/-wal/-shm behind, collect them too
            if f.endswith((".db", ".db-journal", ".db-wal", ".db-shm")):
                try:
                    os.remove(os.path.join(dbFolder, f))
                except OSError:
                    pass
    
    
    def getDataInterface(self) -> DataInterface:
        return self.data_interface
    
    
    def bringGuiToFront(self):
        '''
        Show and raise the window, for a later launch that handed files over.
        '''
        self.show()
        if self.isMinimized():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized
                                | Qt.WindowState.WindowActive)
        self.raise_()
        self.activateWindow()
    
    
    def showDutDataTable(self, selectedDutIndexes: list):
        # always update style in case user changed them in the setting
        settings = getSetting()
        self.dutDataDisplayer.setTextFont(QtGui.QFont(settings.gen.font, 13 if isMac else 10))
        self.dutDataDisplayer.setFloatFormat(settings.getFloatFormat())
        # the dialog opens at once and loads in slices, showing a progress bar
        self.dutDataDisplayer.showWithLoader(
            self.data_interface.dutDataDisplayerContentGenerator(selectedDutIndexes)
        )
        
    
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
        if isinstance(model, FileFilterProxyModel):
            # dut summary and GDR&DTR tables uses FileFilter model
            model = model.sourceModel()
        if isinstance(model, QtSql.QSqlQueryModel):
            self.signals.statusSignal.emit(self.tr("Fetching all..."), False, False, False)
            while model.canFetchMore():
                model.fetchMore()
            # row heights are not preserved across lazy fetch/filter changes
            activeTable.resizeRowsToContents()
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
        # dropped files are handled by the application, like the ones the OS opens
        _app = QApplication.instance()
        if isinstance(_app, StdfApplication):
            _app.canAcceptDrop = lambda: not self._fileLoading
            _app.acceptDropsOn(self.ui.TestList, self.ui.tabControl, self.ui.dataTable)
    
    
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
        stopIcon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop)
        self.ui.stopLoadButton.setIcon(stopIcon)
        
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
        self.proxyModel_tmodel_datalog = FileFilterProxyModel()
        self.proxyModel_tmodel_datalog.setSourceModel(self.tmodel_datalog)
        self.ui.datalogTable.setModel(self.proxyModel_tmodel_datalog)
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
        
        
    def connectCheckbox(self):
        # bind functions to all file/head/site checkboxes, but only once per widget
        if id(self.ui.All) not in self._connectedCbs:
            self.ui.All.clicked.connect(self.onSelect)
            self._connectedCbs.add(id(self.ui.All))
        # iterate the dicts directly to avoid an extra list holding every checkbox
        for cb_dict in (self.site_cb_dict, self.head_cb_dict, self.file_cb_dict):
            for cb in cb_dict.values():
                if id(cb) not in self._connectedCbs:
                    cb.clicked.connect(self.onSelect)
                    self._connectedCbs.add(id(cb))
            
        # bind functions to check/uncheck all buttons, also only once
        if id(self.ui.checkAll) not in self._connectedCbs:
            self.ui.checkAll.clicked.connect(lambda: self.toggleSite(True))
            self._connectedCbs.add(id(self.ui.checkAll))
        if id(self.ui.cancelAll) not in self._connectedCbs:
            self.ui.cancelAll.clicked.connect(lambda: self.toggleSite(False))
            self._connectedCbs.add(id(self.ui.cancelAll))
    
    
    def refreshFileCheckbox(self):
        '''
        Rebuild the File {fid} checkboxes of compare mode.
        
        The whole group box is hidden unless more than one file (fid) exists,
        every file is checked by default.
        '''
        # drop the old checkboxes
        for cb in self.file_cb_dict.values():
            self._connectedCbs.discard(id(cb))
            self.ui.gridLayout_file_select.removeWidget(cb)
            cb.deleteLater()
        self.file_cb_dict = {}
        
        num_files = self.data_interface.num_files if self.data_interface else 0
        if num_files <= 1:
            self.ui.file_selection.hide()
            return
        
        fileNames = self.data_interface.getFileNames()
        nrow = (num_files - 1) // self.CHECKBOX_PER_ROW + 1
        for fid in range(num_files):
            cb = QtWidgets.QCheckBox(self.ui.file_selection)
            cb.setText(f"File {fid}")
            # show the file name on hover
            cb.setToolTip(f"[File {fid}] {fileNames[fid] if fid < len(fileNames) else '?'}")
            cb.setChecked(True)
            row = fid // self.CHECKBOX_PER_ROW
            col = fid % self.CHECKBOX_PER_ROW
            self.ui.gridLayout_file_select.addWidget(cb, row, col)
            self.file_cb_dict[fid] = cb
            if fid == num_files - 1:
                # resize the group box to show every row
                selectionHeight = 50 + (cb.sizeHint().height() + 7) * nrow
                self.ui.file_selection.setMinimumHeight(selectionHeight)
                self.ui.file_selection.setMaximumHeight(selectionHeight)
        self.ui.file_selection.show()
    
    
    def refreshSiteCheckbox(self):
        '''
        Rebuild the Site checkboxes to match the sites of the loaded database.
        '''
        # remove checkboxes of sites that no longer exist
        for site in list(self.site_cb_dict.keys()):     # avoid RuntimeError: dictionary changed size during iteration
            if site in self.availableSites:
                continue
            self.site_cb_dict.pop(site)
            row = 1 + site // self.CHECKBOX_PER_ROW
            col = site % self.CHECKBOX_PER_ROW
            cb_layout = self.ui.gridLayout_site_select.itemAtPosition(row, col)
            if cb_layout is not None:
                cb = cb_layout.widget()
                self._connectedCbs.discard(id(cb))
                cb.deleteLater()
                self.ui.gridLayout_site_select.removeItem(cb_layout)
        
        # add & enable checkboxes for each site
        for siteNum in self.availableSites:
            if siteNum in self.site_cb_dict: 
                # skip if already have a checkbox for this site
                continue
            siteName = "Site %d" % siteNum
            cb = QtWidgets.QCheckBox(self.ui.site_selection_contents)
            cb.setObjectName(siteName)
            cb.setText(siteName)
            row = 1 + siteNum // self.CHECKBOX_PER_ROW
            col = siteNum % self.CHECKBOX_PER_ROW
            self.ui.gridLayout_site_select.addWidget(cb, row, col)
            self.site_cb_dict[siteNum] = cb
        
        # set max height in order to resize site/head selection tab control
        # +2: row 0 holds All/checkAll/cancelAll and sites start at row 1
        nrow_sites = max(self.site_cb_dict, default=-1) // self.CHECKBOX_PER_ROW + 2
        selectionHeight = 50 + (self.ui.gridLayout_site_select.cellRect(0, 0).height() + 7) * nrow_sites
        self.ui.site_head_selection.setMaximumHeight(selectionHeight)
    
    
    def refreshHeadCheckbox(self):
        '''
        Rebuild the Test Head checkboxes to match the heads of the loaded database.
        '''
        # remove checkboxes of heads that no longer exist
        for headnum in list(self.head_cb_dict.keys()):  # avoid RuntimeError: dictionary changed size during iteration
            if headnum in self.availableHeads:
                continue
            self.head_cb_dict.pop(headnum)
            row = headnum // self.CHECKBOX_PER_ROW
            col = headnum % self.CHECKBOX_PER_ROW
            cb_layout = self.ui.gridLayout_head_select.itemAtPosition(row, col)
            if cb_layout is not None:
                cb = cb_layout.widget()
                self._connectedCbs.discard(id(cb))
                cb.deleteLater()
                self.ui.gridLayout_head_select.removeItem(cb_layout)
        
        # add & enable checkboxes for each head
        for headnum in self.availableHeads:
            if headnum in self.head_cb_dict:
                continue
            headName = "Head %d" % headnum
            cb = QtWidgets.QCheckBox(self.ui.head_selection_tab)
            cb.setObjectName(headName)
            cb.setText(headName)
            cb.setChecked(True)
            row = headnum // self.CHECKBOX_PER_ROW
            col = headnum % self.CHECKBOX_PER_ROW
            self.ui.gridLayout_head_select.addWidget(cb, row, col)
            self.head_cb_dict[headnum] = cb
    
    
    def getCheckedFiles(self) -> list:
        '''
        Return the checked file ids. An empty list means the user unchecked
        every file, `None` is never returned so that "no selection yet" is
        not mistaken for "read all files".
        '''
        if not self.file_cb_dict:
            # no compare mode, the only file (if any) is selected
            return list(range(self.data_interface.num_files)) if self.data_interface else []
        return sorted(fid for fid, cb in self.file_cb_dict.items() if cb.isChecked())
    
    
    def refreshWaferList(self):
        '''
        Keep only the wafers belonging to the checked files in the wafer
        selection list, the stacked wafer map entry is always kept.
        
        The previously selected wafers are restored when they are still listed.
        '''
        if self.data_interface is None:
            return
        selectedBefore = set()
        for index in self.selModel_wafer.selectedIndexes():
            data = index.data()
            if isinstance(data, str):
                selectedBefore.add(data)
        checkedFiles = set(self.getCheckedFiles())
        waferList = []
        for item in self.completeWaferList:
            _, fid, _ = parseTestString(item, True)
            # fid == -1 is the stacked wafer map, which is always available
            if fid == -1 or fid in checkedFiles:
                waferList.append(item)
        # block the selection signals so that onSelect runs once, after the
        # selection is restored
        with QtCore.QSignalBlocker(self.selModel_wafer):
            self.updateModelContent(self.sim_list_wafer, waferList)
            # restore the selection for wafers that are still in the list
            if selectedBefore:
                for row in range(self.sim_list_wafer.rowCount()):
                    item = self.sim_list_wafer.item(row)
                    if item is not None and item.text() in selectedBefore:
                        proxyIndex = self.proxyModel_list_wafer.mapFromSource(self.sim_list_wafer.index(row, 0))
                        if proxyIndex.isValid():
                            self.selModel_wafer.select(proxyIndex,
                                                       QtCore.QItemSelectionModel.SelectionFlag.Select)
    
    
    def updateModelContent(self, model, newList):
        # clear first
        model.clear()
        
        for data in newList:
            model.appendRow(QtGui.QStandardItem(data))


    def updateFileHeader(self):
        if isinstance(self.data_interface, DataInterface):
            self.fileMetaData = self.data_interface.getFileMetaData()
            self.applyFileInfoRows(self.fileMetaData, selectFiles=self.getCheckedFiles())
    
    
    def showEarlyFileInfo(self, payload: dict):
        '''
        Display incomplete File Info during loading,
        showing loading text for entries that are not available yet.
        '''
        groups = payload.get("groups") or []
        if not groups:
            return
        # replace absent info with loading text
        loadText = self.tr("Loading...")
        loading = (loadText,)
        counters = {key: loading for key in
                    ("Total", "Pass", "Failed", "Superseded", "Unknown")}
        rows = buildFileMetaData(
            [joinFileGroup(g["names"]) for g in groups],
            [g["path"] for g in groups],
            [joinFileGroup(g["sizes"]) for g in groups],
            counters, payload.get("meta") or {}, plainValues=True)
        self.applyFileInfoRows(rows, pending = loadText)
    
    
    def applyFileInfoRows(self, rows: list, pending: str = None, selectFiles: list = None):
        # clear old info
        self.tmodel_info.removeRows(0, self.tmodel_info.rowCount())
        
        if selectFiles is not None:
            # the first element of a row is the field name, the rest is one
            # value per file, keep the field name and the checked files only
            rows = [[row[0]] + [row[fid + 1] for fid in selectFiles if fid + 1 < len(row)]
                    for row in rows]
        # QStandardItemModel keeps the widest column count it ever had, set it
        # explicitly so the table shrinks when fewer files are checked
        self.tmodel_info.setColumnCount(max((len(row) for row in rows), default=0))
        
        horizontalHeader = self.ui.fileInfoTable.horizontalHeader()
        verticalHeader = self.ui.fileInfoTable.verticalHeader()
        horizontalHeader.setVisible(False)
        verticalHeader.setVisible(False)
            
        for tmpRow in rows:
            # translate the first element, which is the field names
            qitemRow = [QtGui.QStandardItem(self.tr(ele) if i == 0 else ele) for i, ele in enumerate(tmpRow)]
            if pending is not None:
                pendingFont = QtGui.QFont(getSetting().gen.font)
                pendingFont.setItalic(True)
                for item in qitemRow[1:]:
                    if item.text() == pending:
                        item.setForeground(QtGui.QColor(150, 150, 150))
                        item.setFont(pendingFont)
            if getSetting().gen.language != "English":
                # fix weird font when switch to chinese-s
                qfont = QtGui.QFont(getSetting().gen.font)
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
            if column in [DutTableColIndex.PartID, 
                          DutTableColIndex.HeadSite, 
                          DutTableColIndex.DutFlag]:
                # PartID, Head-Site and DUT Flag
                # column may be too long to display
                mode = QHeaderView.ResizeMode.ResizeToContents
            else:
                mode = QHeaderView.ResizeMode.Stretch
            header.setSectionResizeMode(column, mode)
        
        # always hide dut index column
        self.ui.dutInfoTable.hideColumn(DutTableColIndex.DutIndex)
        # hide other columns under specific condition
        for hideCond, col in [(self.data_interface.num_files <= 1, DutTableColIndex.FileID),
                              (self.data_interface.noPartTXT, DutTableColIndex.PartText),
                              (self.data_interface.noWaferID, DutTableColIndex.WaferID),
                              (self.data_interface.noWaferXY, DutTableColIndex.XYCOORD)]:
            if hideCond:
                self.ui.dutInfoTable.hideColumn(col)
            else:
                self.ui.dutInfoTable.showColumn(col)
        
        
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
        self.onSelect()
                
                
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
        This func is called when events occurred in tab, file/site/head selection, test selection and wafer selection 
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
            selFiles = set(self.getCheckedFiles())

            tabChanged = currentTab != self.preTab
            (preHeads, preSites, preTests, preFiles) = self.selectionTracker.setdefault(currentTab, 
                                                                           (None, None, None, None))
            filesChanged = preFiles != selFiles
            # the wafer list only exists on the wafer tab and is the only
            # content that depends on the file selection, rebuild it before
            # reading the wafer selection
            if currentTab == tab.Wafer and filesChanged:
                self.refreshWaferList()
            if filesChanged:
                # the file selection filters the File Info and GDR&DTR tables too
                self.applyFileInfoRows(self.fileMetaData, selectFiles=sorted(selFiles))
                self.proxyModel_tmodel_datalog.setSelectedFiles(selFiles)
                # row heights are not preserved when the proxy re-filters
                self.ui.datalogTable.resizeRowsToContents()
            selTests = set(self.getSelectedTests())

            if (preHeads != selHeads or
                preSites != selSites or
                preTests != selTests or
                preFiles != selFiles):
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
            self.selectionTracker[currentTab] = (selHeads, selSites, selTests, selFiles)
    
    
    def isTestFail(self, selected_string: str) -> str:
        testTuple = parseTestString(selected_string, False)
        testPass = self.data_interface.checkTestPassFail(testTuple)
        settings = getSetting()
        
        if testPass:
            # if user do not need to check Cpk, return to caller
            if not settings.gen.check_cpk:
                return "Pass"
        else:
            return "Fail"
        
        # check if cpk is lower than the threshold
        cpkList = self.data_interface.getTestCpkList(testTuple)
        for cpk in cpkList:
            if not np.isnan(cpk):
                # check cpk only if it's valid
                if cpk < settings.gen.cpk_thrsh:
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
        
        testSortMethod = getSetting().gen.sort_tlist
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
                                                        self.getCheckedSites(),
                                                        self.getCheckedFiles())
        self.tmodel_data.setTestData(d["Data"])
        self.tmodel_data.setTestInfo(d["TestInfo"])
        self.tmodel_data.setDutIndexMap(d["dut2ind"])
        self.tmodel_data.setDutInfoMap(d["dutInfo"])
        self.tmodel_data.setTestLists(d["TestLists"])
        self.tmodel_data.setHHeaderBase([self.tr("Part ID"), self.tr("Part Text"), self.tr("Test Head - Site")])
        self.tmodel_data.setVHeaderBase([self.tr("Test Number"), self.tr("HLimit"), self.tr("LLimit"), self.tr("Unit")])
        self.tmodel_data.setVHeaderExt(d["VHeader"])
        self.tmodel_data.setFont(QtGui.QFont(settings.gen.font, 13 if isMac else 10))
        self.tmodel_data.setFloatFormat(settings.getFloatFormat())
        self.tmodel_data.layoutChanged.emit()
        hheaderview = self.ui.rawDataTable.horizontalHeader()
        hheaderview.setVisible(True)
        # resize table columns to header string (test name)
        for col in range(self.tmodel_data.columnCount()):
            cellWidth = hheaderview.fontMetrics().horizontalAdvance(
                self.tmodel_data.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            )
            hheaderview.resizeSection(col, max(cellWidth, 80))
        self.ui.rawDataTable.verticalHeader().setVisible(True)
    
                
    def updateTabContent(self):
        if self.data_interface is None:
            return
        
        tabType = self.ui.tabControl.currentIndex()
        selSites = self.getCheckedSites()
        selHeads = self.getCheckedHeads()
        selFiles = self.getCheckedFiles()
        # update Test Data table in info tab
        if tabType == tab.Info:
            # filter dut summary table if in Info tab and head & site changed
            self.proxyModel_tmodel_dut.updateHeadsSites(selHeads, selSites)
            self.proxyModel_tmodel_dut.setSelectedFiles(selFiles)
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
            chart = self.genPlot(testTuple, head, selSites, tabType, selFiles)
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
                                                      self.getCheckedSites(),
                                                      self.getCheckedFiles())
            HHeader = d["HHeader"]
            indexOfFail = HHeader.index("Fail Num")
            indexOfCpk = HHeader.index("Cpk")

            self.tmodel.setContent(d["Rows"])
            self.tmodel.setColumnCount(len(HHeader))
            self.tmodel.setFailCpkIndex(indexOfFail, indexOfCpk)
            self.tmodel.setCpkThreshold(settings.gen.cpk_thrsh)
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
                                                         self.getCheckedSites(),
                                                         self.getCheckedFiles())
            else:
                # wafer tab
                d = self.data_interface.getWaferStatistics(selTests, 
                                                           self.getCheckedSites())
            self.bwmodel.setContent(d["Rows"])
            self.bwmodel.setColumnCount(d["maxLen"])
            self.bwmodel.setHHeader([])
            self.bwmodel.setVHeader(d["VHeader"])
            self.bwmodel.setColorDict(settings.color.hbin_colors, 
                                      settings.color.sbin_colors)
        
            horizontalHeader.setVisible(False)
            verticalHeader.setVisible(True)
            verticalHeader.setDefaultSectionSize(35)
            verticalHeader.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # activate bin wafer model
            self.ui.dataTable.setModel(self.bwmodel)
            self.bwmodel.layoutChanged.emit()
        
        # resize table cell by its contents
        horizontalHeader.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # set min size to avoid "compressed" cells
        horizontalHeader.setMinimumSectionSize(80)
                
    
    def genPlot(self, testTuple: tuple, head: int, selectSites: list[int], tabType: tab, selectFiles: list[int]):
        '''
        testTuple: (test_num, pmr, test_name)
        For wafer: (wafer index, file id, wafer name)
        selectFiles: file ids checked in file_selection, the stacked wafer map
                     only aggregates these files
        '''
        if tabType == tab.Trend:
            tdata = self.data_interface.getTrendChartData(testTuple, head, selectSites, selectFiles)
            tchart = TrendChart()
            tchart.setFileNames(self.data_interface.getFileNames())
            tchart.setData(tdata)
            if tchart.validData:
                tchart.setShowDutSignal(self.signals.showDutDataSignal_TrendHisto)
                return tchart
        
        elif tabType == tab.Histo:
            tdata = self.data_interface.getTrendChartData(testTuple, head, selectSites, selectFiles)
            hchart = HistoChart()
            hchart.setFileNames(self.data_interface.getFileNames())
            hchart.setData(tdata)
            if hchart.validData:
                hchart.setShowDutSignal(self.signals.showDutDataSignal_TrendHisto)
                return hchart
        
        elif tabType == tab.Wafer:
            wdata = self.data_interface.getWaferMapData(testTuple, selectSites, selectFiles)
            wchart = WaferMap()
            wchart.setWaferData(wdata)
            if wchart.validData:
                wchart.setShowDutSignal(self.signals.showDutDataSignal_Wafer)
                return wchart
        
        elif tabType == tab.Bin:
            bcharts = []
            # one site per binchart
            for site in selectSites:
                bdata = self.data_interface.getBinChartData(head, site, selectFiles)
                bchartgen = BinChartGenerator()
                bchartgen.setBinData(bdata)
                if bchartgen.validData:
                    for isHBIN in [True, False]:
                        gvm = bchartgen.genGraphicView(isHBIN)
                        gvm.setShowDutSignal(self.signals.showDutDataSignal_Bin)
                        bcharts.append(gvm)
            return bcharts
        
        return None
            
            
    def getFileInfoForReport(self, fids: list[int]):
        '''
        For report generator, File Info rows filtered by the given file ids.
        '''
        info = []
        for row in self.fileMetaData:
            # the first element is the field name, the rest is one value per file
            infoRow = [self.tr(row[0])] + [row[fid + 1] for fid in fids if fid + 1 < len(row)]
            info.append([ele if isinstance(ele, str) else str(ele) for ele in infoRow])
        return info
    
    
    def getDUTSummaryForReport(self, heads: list[int], sites: list[int], fids: list[int], testTuples: list):
        '''
        For report generator
        Return data for `DutSummary` content
        '''
        return self.data_interface.getDutSummaryReportContent(testTuples, heads, sites, fids)
    
    
    def getDatalogForReport(self, fids: list[int]):
        # this table uses sql query model
        model = self.tmodel_datalog
        fidSet = set(fids)
        
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
        # Yield whatever rows are currently in the model, then call fetchMore()
        # and yield again, repeating until the underlying query is exhausted.
        # column 0 is the File ID, only the requested files are yielded.
        row = 0
        while True:
            while row < model.rowCount():
                datalogRow = []
                for col in range(model.columnCount()):
                    d = model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
                    datalogRow.append(d.strip("\n") if isinstance(d, str) else str(d))
                row += 1
                fid = int(datalogRow[0])
                if fid in fidSet:
                    yield datalogRow
            if not model.canFetchMore():
                break
            model.fetchMore()
    
    
    def getImageBytesForReport(self, testTuple: tuple, head: int, sites: list[int], fids: list[int], tabType: tab):
        '''
        For report generator
        '''
        chart = self.genPlot(testTuple, head, sites, tabType, fids)
        return pyqtGraphPlot2Bytes(chart)
    
    
    def getTestStatisticForReport(self, heads: list[int], sites: list[int], fids: list[int], tabType: tab, kargs: dict):
        '''
        For report generator, kargs contains (testTuple or isHBIN)
        '''
        data = []
        if tabType in [tab.Trend, tab.Histo, tab.PPQQ]:
            testTuples = kargs["testTuples"]
            d = self.data_interface.getTestStatistics(testTuples, heads, sites, fids)
            # add translated hheader, put an empty string for matching
            data.append([""] + [self.tr(h) for h in d["HHeader"]])
            # vheader + statistics
            for vh, dataRow in zip(d["VHeader"], d["Rows"]):
                data.append([vh] + dataRow)            
            
        elif tabType == tab.Bin:
            isHBIN = kargs["isHBIN"]
            d = self.data_interface.getBinStatistics(heads, sites, fids)
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
    
    
    def clearAllContents(self):
        # clear tabs' images
        for t in [tab.Trend, tab.Histo, tab.PPQQ, 
                  tab.Bin, tab.Wafer, tab.Correlate]:
            self.clearCurrentTab(t)
        self.selectionTracker = {}
        self.fileMetaData = []
        gc.collect()
    
    
    def callFileLoader(self, paths: list[list[str]]):
        '''
        Open input STDF files groups
        '''
        if paths:
            self.loader.loadFile(paths)

        
    def restorePreviousSession(self):
        '''
        looking for database of previous loaded
        stdf files
        '''
        dbFolder = os.path.join(sys.appDataFolder, "logs")
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
            # a cancelled load arrives as None, only a real one counts
            self._dbProduced = True
            # clear old images & tables
            self.clearAllContents()
            # close old data interface first
            if self.data_interface is not None:
                self.data_interface.close()
            # close dut summary database if opened
            if self.db_dut.isOpen():
                self.db_dut.close()
            
            # working on the new object
            self.data_interface = newDI
            self.data_interface.loadDatabase()
            # open new dut summary database
            self.db_dut.setDatabaseName(self.data_interface.dbPath)
            # the fetcher may build query indexes in the background, so let the
            # Qt connection wait out a commit instead of failing
            # access db using read-only mode
            self.db_dut.setConnectOptions("QSQLITE_OPEN_READONLY;QSQLITE_BUSY_TIMEOUT=5000")
            if not self.db_dut.open():
                raise RuntimeError(f"Database cannot be opened by Qt: {self.data_interface.dbPath}")
            # QtSql is a second SQLite version in this process, it cannot see F_GETLK
            # in Rust fetcher, so it will attach to the WAL index and resets it on first
            # statement, leading to SIGBUS if index building thread is running on macOS/Linux.
            # 
            # Add a simple query before starting index build thread avoids the issue.
            QtSql.QSqlQuery(SIMPLE_PROBE, self.db_dut)
            # index build thread must be started after QtSql's first statement
            self.data_interface.DatabaseFetcher.startIndexBuild()
            
            # report the background index build in the status bar
            self.startIndexStatusPolling()
            
            # disable/enable wafer tab
            self.ui.tabControl.setTabEnabled(tab.Wafer, self.data_interface.containsWafer)
    
            # update listView
            self.completeTestList = self.data_interface.completeTestList
            self.completeWaferList = self.data_interface.completeWaferList
            self.refreshTestList()
            # rebuild the file/head/site checkboxes for the new database
            self.availableSites = self.data_interface.availableSites
            self.availableHeads = self.data_interface.availableHeads
            self.refreshFileCheckbox()
            self.refreshHeadCheckbox()
            self.refreshSiteCheckbox()
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
            self.connectCheckbox()
            self.updateFileHeader()
            self.updateDutSummaryTable()
            self.updateGDR_DTR_Table()
            self.onSelect()

    
    @Slot(str, bool, bool, bool)
    def updateStatus(self, new_msg, info=False, warning=False, error=False, duration=0):
        # duration 0 keeps the message, like it always did
        self.statusBar().showMessage(new_msg, duration)
        if info: 
            QMessageBox.information(self, self.tr("Info"), new_msg)
        elif warning: 
            QMessageBox.warning(self, self.tr("Warning"), new_msg)
            logger.warning(new_msg)
        elif error:
            QMessageBox.critical(self, self.tr("Error"), new_msg)
            # sys.exit()
        QApplication.processEvents()

    
    @Slot(str, int)
    def updateLoadStatus(self, new_msg, duration: int):
        '''Status bar messages of the loader, the caller sets how long they stay'''
        self.updateStatus(new_msg, duration=duration)
        
    
    def startIndexStatusPolling(self):
        '''Report the background index build (started by updateData).'''
        if not hasattr(self, "indexStatusTimer"):
            self.indexStatusTimer = QtCore.QTimer(self)
            self.indexStatusTimer.setInterval(400)
            self.indexStatusTimer.timeout.connect(self.pollIndexStatus)
        self.indexStatusTimer.start()
        
    
    def pollIndexStatus(self):
        if self.data_interface is None or not self.data_interface.dbConnected:
            self.indexStatusTimer.stop()
            return
        state, elapsed_ms = self.data_interface.DatabaseFetcher.indexBuildState()
        INDEX_DONE = 2
        INDEX_NONE = 3
        # report the duration once it is done
        if state in (INDEX_DONE, INDEX_NONE):
            self.indexStatusTimer.stop()
            if state == INDEX_DONE:
                self.statusBar().showMessage(
                    self.tr("Database index ready, building for {0} sec").format(
                        round(elapsed_ms / 1000, 1)), 4000)
        
    
    @Slot()
    def onLoaderFinished(self):
        """The loader thread is done, stopped early or finished normally."""
        self._fileLoading = False
        if self._closeOnFinish:
            # a build that was stopped never reaches the "database is ready" path
            self.close()


    @Slot(int)
    def onLoaderProgress(self, num: int):
        self.ui.loaderProgress.setValue(min(num, 10000))
        self.ui.loaderProgress.setFormat("%.2f%%" % (num / 100.0))
        self.ui.loaderProgress.show()


    @Slot()
    def onTerminateLoad(self):
        if not self._fileLoading:
            return
        if not self.loader.askAbandon():
            return
        if not self._fileLoading:
            # load complete while user gives up,
            # discard the completed db.
            self.loader.abandon()
            self.onLoadEnd()
            return
        # prevent repeated button triggers
        self.ui.stopLoadButton.setEnabled(False)
        self.loader.abandon()


    def closeEvent(self, event):
        # closing during a load used to quit and drop the half built database
        if self._fileLoading:
            if self.loader.askAbandon():
                if not self._fileLoading:
                    # same as `onTerminateLoad`
                    self.loader.abandon()
                    self.onLoadEnd()
                    super().closeEvent(event)
                    return
                # closed in onLoaderFinished, leaving now would kill the thread
                self._closeOnFinish = True
                self.loader.abandon()
            event.ignore()
            return
        super().closeEvent(event)


    def onLoadState(self, loading: bool):
        '''Lock certain functionalities during new file loading'''
        if loading:
            self._dbProduced = False
            self._abandoned = False
            # the database to go back to when the load is abandoned
            self._preDB = (self.data_interface.dbPath
                                if self.data_interface is not None
                                and self.data_interface.dbConnected else "")
        self._fileLoading = loading
        self.ui.tabControl.setTabEnabled(tab.Info, True)
        for index in range(self.ui.tabControl.count()):
            if index == tab.Wafer:
                # the file decides this one, unlocking it here overrides updateData
                continue
            if index != tab.Info:
                self.ui.tabControl.setTabEnabled(index, not loading)
        # File Info stays visible, the other pages cannot be opened
        for index in range(self.ui.infoBox.count()):
            if index != 0:
                self.ui.infoBox.setItemEnabled(index, not loading)
        if loading:
            self.ui.tabControl.setCurrentIndex(tab.Info)
            self.ui.infoBox.setCurrentIndex(0)
            self.ui.stopLoadButton.setEnabled(True)
            self.ui.stopLoadButton.show()
        # selection acts on the loaded database
        self.ui.Selection_stackedWidget.setEnabled(not loading)
        # disable actions during loading to prevent race conditions
        for action in ("actionOpen", "actionMerge",
                       "actionFailMarker", "actionExport",
                       "actionLoad_Session", "actionSave_Session"):
            getattr(self.ui, action).setEnabled(not loading)
        if not loading:
            self.onLoadEnd()


    def markAbandoned(self):
        # called by the loader when the user gives up on the running load
        self._abandoned = True


    def onLoadEnd(self):
        '''The load is over, restore'''
        self.ui.loaderProgress.hide()
        self.ui.stopLoadButton.hide()
        current = self.data_interface.dbPath if self.data_interface is not None else ""
        if self._abandoned:
            if self._preDB and current and current != self._preDB:
                # new database already in place, restore the old one
                return self.loadDatabase(self._preDB)
            if not current and self._preDB:
                # the load was abandoned before any database arrived, nothing to put back
                return
            if not self._preDB:
                # nothing was opened before, so the header read is all there is
                # and the abandoned file must not be left on screen
                return self.clearAbandonedLoad()
        if not self._dbProduced:
            if self.data_interface is not None and self.data_interface.dbConnected:
                self.updateFileHeader()
            else:
                self.applyFileInfoRows([])


    def clearAbandonedLoad(self):
        '''Drop the header of an abandoned load'''
        self.clearAllContents()
        if self.data_interface is not None:
            self.data_interface.close()
            self.data_interface = None
        if self.db_dut.isOpen():
            self.db_dut.close()
        self.applyFileInfoRows([])


    def onException(self, errorType, errorValue, tb):
        logger.error("Uncaught Error occurred", exc_info=(errorType, errorValue, tb))
        errMsg = traceback.format_exception(errorType, errorValue, tb, limit=0)
        self.updateStatus("\n".join(errMsg), False, False, True)



# application entry point
def run():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = StdfApplication([])
    pathFromArgs = [item for item in sys.argv[1:] if os.path.isfile(item)]
    
    # only a single STDF-Viwer process should be running
    instance = ViewerInstance()
    if not instance.tryClaim():
        # already owned, pass files to owner and exit
        instance.passFilesToOwner(pathFromArgs)
        sys.exit(0)
    
    app.setStyle('Fusion')
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    app.setWindowIcon(getIcon("App"))
    window = MyWindow()
    window.show()
    if pathFromArgs:
        window.openNewFile(pathFromArgs)
    app.filesOpenSignal.connect(window.openNewFile)
    instance.filesReceived.connect(window.openNewFile)
    instance.activateRequested.connect(window.bringGuiToFront)
    sys.exit(app.exec_())
    

if __name__ == '__main__':
    run()