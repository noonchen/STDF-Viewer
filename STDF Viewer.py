#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
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



import io, re, os, sys
import numpy as np
from deps.ui.ImgSrc_svg import ImgDict
from deps.pystdf.RecordParser import RecordParser
from deps.stdfOffsetRetriever import stdfSummarizer

from deps.uic_stdLoader import stdfLoader
from deps.uic_stdFailMarker import FailMarker
from deps.uic_stdExporter import stdfExporter
from deps.uic_stdSettings import stdfSettings

# pyqt5
from deps.ui.stdfViewer_MainWindows import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QFileDialog, QAbstractItemView
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
# pyside2
# from deps.ui.stdfViewer_MainWindows_side import Ui_MainWindow
# from PySide2 import QtCore, QtWidgets, QtGui
# from PySide2.QtWidgets import QApplication, QFileDialog, QAbstractItemView
# from PySide2.QtCore import Signal, Slot

import matplotlib
matplotlib.use('QT5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

#-------------------------

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    

def calc_cpk(L, H, data):
    sdev = np.std(data)
    mean = np.mean(data)
    
    if L == None or H == None:
        return mean, sdev, np.nan
    
    T = H - L
    if sdev == 0:
        Cpk = np.inf
    else:
        U = (H + L)/2
        CP = T / (6 * sdev)
        # Ca = (mean - U) / (T/2)
        Cpk = CP - abs(mean - U)/(3 * sdev)
    return mean, sdev, Cpk


# convert from pixel coords to data coords
toDCoord = lambda ax, point: ax.transData.inverted().transform(point)

# simulate a Enum in python
class Tab(tuple): __getattr__ = tuple.index
tab = Tab(["Info", "Trend", "Histo", "Bin"])

# MIR field name to Description Dict
mirFieldNames = ["SETUP_T", "START_T", "STAT_NUM", "MODE_COD", "RTST_COD", "PROT_COD", "BURN_TIM", "CMOD_COD", "LOT_ID", "PART_TYP", "NODE_NAM", "TSTR_TYP",
                 "JOB_NAM", "JOB_REV", "SBLOT_ID", "OPER_NAM", "EXEC_TYP", "EXEC_VER", "TEST_COD", "TST_TEMP", "USER_TXT", "AUX_FILE", "PKG_TYP", "FAMLY_ID",
                 "DATE_COD", "FACIL_ID", "FLOOR_ID", "PROC_ID", "OPER_FRQ", "SPEC_NAM", "SPEC_VER", "FLOW_ID", "SETUP_ID", "DSGN_REV", "ENG_ID", "ROM_COD", "SERL_NUM", "SUPR_NAM"]

mirDescriptions = ["Setup Time", "Start Time", "Station Number", "Test Mode Code", "Retest Code", "Protection Code", "Burn-in Time", "Command Mode Code", "Lot ID", "Product ID", 
                   "Node Name", "Tester Type", "Job Name", "Job Revision", "Sublot ID", "Operator ID", "Tester Software Type", "Tester Software Version", "Step ID", "Test Temperature", 
                   "User Text", "Auxiliary File Name", "Package Type", "Family ID", "Date Code", "Facility ID", "Floor ID", "Process ID", "Operation Frequency", "Test Spec Name", 
                   "Test Spec Version", "Flow ID", "Setup ID", "Design Revision", "Engineer Lot ID", "ROM Code ID", "Serial Number", "Supervisor ID"]

mirDict = dict(zip(mirFieldNames, mirDescriptions))


class MagCursor(object):

    def __init__(self, ax, x, y, precision):
        self.pixRange = 20
        self.ax = ax
        self.rangeX, self.rangeY = [i-j for i,j in zip(toDCoord(self.ax, (self.pixRange, self.pixRange)), toDCoord(self.ax, (0, 0)))]   # convert pixel to data
        self.x = x  # list
        self.y = y  # list
        # create marker and data description tip, hide by default
        self.marker = self.ax.scatter(0, 0, s=40, marker="+", color='k')
        self.dcp = self.ax.text(s="", x=0, y=0, backgroundcolor="#FFFF00", fontname="Courier New", weight="bold", fontsize=8, zorder=1000)
        self.marker.set_visible(False)
        self.dcp.set_visible(False)
        self.updatePrecision(precision)
            
    def updatePrecision(self, precision):
        self.valueFormat = "%%.%df" % precision

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        # indx = min(np.searchsorted(self.x - 0.5*(self.x[1]-self.x[0]), x), len(self.x) - 1) - 1
        indx = np.nanargmin(((np.column_stack((self.x, self.y)) - (x,y))**2).sum(axis = -1))

        dx = abs(x - self.x[indx])
        dy = abs(y - self.y[indx])
        
        if dx <= self.rangeX and dy <= self.rangeY:
            x = self.x[indx]
            y = self.y[indx]
            # print(x, y)
            # update the line positions
            self.marker.set_offsets([[x, y]])
            text = 'DUT# : %d\nValue: ' % x + self.valueFormat % y
            self.dcp.set_text(text)
            self.dcp.set_position((x+self.rangeX, y+self.rangeY))
            # set visible
            self.marker.set_visible(True)
            self.dcp.set_visible(True)
            self.ax.figure.canvas.draw()
        else:
            self.marker.set_visible(False)
            self.dcp.set_visible(False)
            self.ax.figure.canvas.draw()
            
    def canvas_resize(self, event):
        # update range once the canvas is resized
        self.rangeX, self.rangeY = [i-j for i,j in zip(toDCoord(self.ax, (self.pixRange, self.pixRange)), toDCoord(self.ax, (0, 0)))]   # convert pixel to data


class SettingParams:
    # trend
    showHL_trend = True
    showLL_trend = True
    showMed_trend = True
    showMean_trend = True
    # histo
    showHL_histo = True
    showLL_histo = True
    showMed_histo = True
    showMean_histo = True
    showGaus_histo = True
    showBoxp_histo = True
    binCount = 30
    showSigma = frozenset([3, 6, 9])    # for hashability
    # table
    dataNotation = "G"  # F E G stand for float, Scientific, automatic
    dataPrecision = 3
    

class signals4MainUI(QtCore.QObject):
    dataSignal = Signal(stdfSummarizer)  # get std data from loader
    statusSignal = Signal(str)   # status bar


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.preTab = None              # used for detecting tab changes
        self.preSiteSelection = None    # used for detecting site selection changes
        self.dataSrc = None     # only store test data
        self.dataInfo = None    # used to store other info
        self.selData = None
        ### we cache the data in RecordParser, self.dataCache is not used anymore
        # self.dataCache = {}     # dict for storing data of selected test items
        self.cursorDict = {}    # init/clear a dict to store cursors instance to prevent garbage collection
        self.settingParams = SettingParams()    # used for storing setting parameters
        
        # std handler
        self.std_dict = {}
        self.std_handle = None
        
        pathList = [item for item in sys.argv[1:] if os.path.isfile(item)]
        if pathList: 
            self.std_handle = open(pathList[0], 'rb')
            self.std_dict[0] = self.std_handle
        # update icons for actions and widgets
        self.updateIcons()
        self.init_TestList()
        self.init_DataTable()
        # dict to store site checkbox objects
        self.site_cb_dict = {}
        self.availableSites = []
        # init actions
        self.ui.actionOpen.triggered.connect(self.openNewFile)
        self.ui.actionFailMarker.triggered.connect(self.onFailMarker)
        self.ui.actionExport.triggered.connect(self.onExportReport)
        self.ui.actionSettings.triggered.connect(self.onSettings)
        self.ui.actionAbout.triggered.connect(self.onAbout)
        
        # init and connect signals
        self.signals = signals4MainUI()
        self.signals.dataSignal.connect(self.updateData)
        self.signals.statusSignal.connect(self.updateStatus)
        # init search-related UI
        self.ui.SearchBox.textChanged.connect(self.proxyModel_list.setFilterWildcard)
        self.ui.ClearButton.clicked.connect(self.clearSearchBox)
        self.completeTestList = []
        
        self.tab_dict = {tab.Trend: {"scroll": self.ui.scrollArea_trend, "layout": self.ui.verticalLayout_trend},
                         tab.Histo: {"scroll": self.ui.scrollArea_histo, "layout": self.ui.verticalLayout_histo},
                         tab.Bin: {"scroll": self.ui.scrollArea_bin, "layout": self.ui.verticalLayout_bin}}
        self.ui.tabControl.currentChanged.connect(self.onSelect)    # table should be updated as well
        # add a toolbar action at the right side
        self.ui.spaceWidgetTB = QtWidgets.QWidget()
        self.ui.spaceWidgetTB.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.ui.toolBar.addWidget(self.ui.spaceWidgetTB)
        self.ui.toolBar.addAction(self.ui.actionAbout)
        
        
    def openNewFile(self):
        fname, _typ = QFileDialog.getOpenFileName(self, 
                                             caption="Select a STD File To Open", 
                                             filter="STDF (*.std*);;All Files (*.*)",)
        if os.path.isfile(fname):
            self.std_handle = open(fname, 'rb')
            # clear handles on each new file open
            self.std_dict = {}
            self.std_dict[0] = self.std_handle
            self.callFileLoader(self.std_handle)
              
    
    def onFailMarker(self):
        if self.dataSrc:
            FailMarker(self)
        else:
            # no data is found, show a warning dialog
            QtWidgets.QMessageBox.warning(self, "Warning", "No file is loaded.")
                
    
    def onExportReport(self):
        if self.dataSrc:
            stdfExporter(self)
        else:
            # no data is found, show a warning dialog
            QtWidgets.QMessageBox.warning(self, "Warning", "No file is loaded.")
    
    
    def onSettings(self):
        stdfSettings(self)
    
    
    def onAbout(self):
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setWindowTitle("About")
        msgBox.setTextFormat(QtCore.Qt.RichText)
        msgBox.setText("<span style='color:#930DF2;font-size:20px'>STDF Viewer</span><br>Author: noonchen<br>Email: chennoon233@foxmail.com<br>")
        msgBox.setInformativeText("For instructions, please refer to the ReadMe in the repo:<br><a href='https://github.com/noonchen/STDF_Viewer'>noonchen @ STDF_Viewer</a>")
        appIcon = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Icon"], format = 'SVG'))
        appIcon.setDevicePixelRatio(2.0)
        msgBox.setIconPixmap(appIcon)
        msgBox.exec_()
        
    
    def updateIcons(self):
        self.ui.actionOpen.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Open"], format = 'SVG'))))
        self.ui.actionFailMarker.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["FailMarker"], format = 'SVG'))))
        self.ui.actionExport.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Export"], format = 'SVG'))))
        self.ui.actionSettings.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Settings"], format = 'SVG'))))
        self.ui.actionAbout.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["About"], format = 'SVG'))))
        self.ui.toolBar.setIconSize(QtCore.QSize(20, 20))
        
        self.ui.tabControl.setTabIcon(tab.Info, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_info"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Trend, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_trend"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Histo, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_histo"], format = 'SVG'))))
        self.ui.tabControl.setTabIcon(tab.Bin, QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["tab_bin"], format = 'SVG'))))
    
    
    def init_TestList(self):
        # init model for ListView
        self.sim_list = QtGui.QStandardItemModel()
        self.proxyModel_list = QtCore.QSortFilterProxyModel()
        self.proxyModel_list.setSourceModel(self.sim_list)
        self.proxyModel_list.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.ui.TestList.setModel(self.proxyModel_list)
        # enable multi selection
        self.ui.TestList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.TestList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # get select model and connect func to change event
        self.selModel = self.ui.TestList.selectionModel()
        self.selModel.selectionChanged.connect(self.onSelect)
        
        
    def init_DataTable(self):
        # statistic table
        self.tmodel = QtGui.QStandardItemModel()
        self.ui.dataTable.setModel(self.tmodel)
        # rawData table
        self.tmodel_raw = QtGui.QStandardItemModel()
        self.ui.rawDataTable.setModel(self.tmodel_raw)
        # dut summary table
        self.tmodel_dut = QtGui.QStandardItemModel()
        self.ui.dutInfoTable.setModel(self.tmodel_dut)
        # file header table
        self.tmodel_info = QtGui.QStandardItemModel()
        self.ui.fileInfoTable.setModel(self.tmodel_info)
        # smooth scrolling
        self.ui.dataTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dataTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.rawDataTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.rawDataTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dutInfoTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.dutInfoTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)        
        self.ui.fileInfoTable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
                            
    def init_SiteCheckbox(self):
        # bind functions to all checkboxes
        self.ui.All.clicked['bool'].connect(self.onSiteChecked)

        for cb in self.site_cb_dict.values():
            cb.clicked['bool'].connect(self.onSiteChecked)
            
        # bind functions to check/uncheck all buttons
        self.ui.checkAll.clicked.connect(lambda: self.toggleSite(True))
        self.ui.cancelAll.clicked.connect(lambda: self.toggleSite(False))
        
        
    def updateTestList(self, newList):
        # clear first
        self.sim_list.clear()
        
        for data in newList:
            self.sim_list.appendRow(QtGui.QStandardItem(data))


    def updateFileHeader(self):
        # clear
        self.tmodel_info.removeRows(0, self.tmodel_info.rowCount())
        
        horizontalHeader = self.ui.fileInfoTable.horizontalHeader()
        verticalHeader = self.ui.fileInfoTable.verticalHeader()
        horizontalHeader.setVisible(False)
        verticalHeader.setVisible(False)
        
        # manually add rows of std file info
        absPath = os.path.realpath(self.std_handle.name)
        self.tmodel_info.appendRow([QtGui.QStandardItem(ele) for ele in ["File Name: ", os.path.basename(absPath)]])
        self.tmodel_info.appendRow([QtGui.QStandardItem(ele) for ele in ["Directory Path: ", os.path.dirname(absPath)]])
        self.tmodel_info.appendRow([QtGui.QStandardItem(ele) for ele in ["File Size: ", "%.2f MB"%(os.stat(self.std_handle.name).st_size / 2**20)]])
        self.tmodel_info.appendRow([QtGui.QStandardItem(ele) for ele in ["DUTs Tested: ", str(self.dataInfo.dutIndex + 1)]])    # PIR #
        self.tmodel_info.appendRow([QtGui.QStandardItem(ele) for ele in ["DUTs Passed: ", str(self.dataInfo.dutPassed)]])
        self.tmodel_info.appendRow([QtGui.QStandardItem(ele) for ele in ["DUTs Failed: ", str(self.dataInfo.dutFailed)]])

        for fn in mirFieldNames:
            value = self.dataInfo.fileInfo[fn]
            if value == None or value == "" or value == " " : continue
            tmpRow = [QtGui.QStandardItem(ele) for ele in [mirDict[fn] + ": ", value]]
            self.tmodel_info.appendRow(tmpRow)
            
        horizontalHeader.resizeSection(0, 250)
        horizontalHeader.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontalHeader.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        # resize to content to show all texts, then add additional height to each row
        for row in range(self.tmodel_info.rowCount()):
            verticalHeader.setSectionResizeMode(row, QtWidgets.QHeaderView.ResizeToContents)
            newHeight = verticalHeader.sectionSize(row) + 20
            verticalHeader.setSectionResizeMode(row, QtWidgets.QHeaderView.Fixed)
            verticalHeader.resizeSection(row, newHeight)
    
    
    def updateDutSummary(self):
        # clear
        self.tmodel_dut.removeRows(0, self.tmodel_dut.rowCount())
        
        headerLabels = ["Part ID", "Test Site", "Tests Executed", "Test Time", "Hardware Bin", "Software Bin", "DUT Flag"]
        self.tmodel_dut.setHorizontalHeaderLabels(headerLabels)
        header = self.ui.dutInfoTable.horizontalHeader()
        header.setVisible(True)
        dutDict = self.dataInfo.dutDict
        
        for index in sorted(dutDict.keys()):
            hbin = dutDict[index]["HARD_BIN"]
            sbin = dutDict[index]["SOFT_BIN"]
            tmpRow = ["%s" % dutDict[index]["PART_ID"], 
                      "Site %d" % dutDict[index]["SITE_NUM"], 
                      "%d" % dutDict[index]["NUM_TEST"],
                      "%d ms" % dutDict[index]["TEST_T"],
                      "Bin %d - %s" % (hbin, self.dataInfo.hbinDict[hbin][0]),
                      "Bin %d - %s" % (sbin, self.dataInfo.sbinDict[sbin][0]),
                      "%s" % dutDict[index]["PART_FLG"]]
            qitemRow = []
            for item in tmpRow:
                qitem = QtGui.QStandardItem(item)
                qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # mark red when failed
                if dutDict[index]["PART_FLG"] == "Failed": 
                    qitem.setData(QtGui.QColor(QtGui.QColor(255, 255, 255)), QtCore.Qt.ForegroundRole)
                    qitem.setData(QtGui.QColor(QtGui.QColor(204, 0, 0)), QtCore.Qt.BackgroundRole)
                qitemRow.append(qitem)                        
            # tmpTable.append(tmpRow)
            self.tmodel_dut.appendRow(qitemRow)            
            
        for column in range(header.count()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
                    

    def searchInBox(self):
        # get current string in search box as re pattern
        try:
            cpl_pattern = re.compile(self.ui.SearchBox.text(), re.IGNORECASE)
            filterList = [item for item in self.completeTestList if cpl_pattern.search(item)]
            self.updateTestList(filterList)
            # self.ui.statusBar().showMessage("")
            self.statusBar().showMessage("")
        except re.error:
            self.updateTestList(self.completeTestList)
            # self.ui.statusBar().showMessage("Search string is not a valid Regex")
            self.statusBar().showMessage("Search string is not a valid Regex")
        
        
    def clearSearchBox(self):
        self.ui.SearchBox.clear()


    def toggleSite(self, on=True):
        self.ui.All.setChecked(on)
        for siteNum, cb in self.site_cb_dict.items():
            cb.setChecked(on)
        self.onSiteChecked()
                
                
    def getCheckedSites(self):
        checkedSites = []
        
        if self.ui.All.isChecked():
            # site number of All == -1
            checkedSites.append(-1)
        
        for site_num, cb in self.site_cb_dict.items():
            if cb.isChecked():
                checkedSites.append(site_num)
                
        return checkedSites
                
    
    def getTestItemNums(self):
        selectedIndex = self.selModel.selection().indexes()
        if selectedIndex:
            return sorted([int(ind.data().split("\t")[0]) for ind in selectedIndex])
        else:
            return None
    
    
    def onSelect(self):
        if self.dataSrc:
            itemNums = self.getTestItemNums()
            # get enabled sites
            siteList = self.getCheckedSites()
            # prepare the data for plot and table
            self.prepareData(itemNums, siteList)
            
            # update bin chart only if sites changed and previous tab is not bin chart
            if self.preSiteSelection == set(siteList) and self.ui.tabControl.currentIndex() == tab.Bin and self.preTab == tab.Bin:
                # do not update
                pass
            else:
                # update site selection
                self.preSiteSelection = set(siteList)
                # update tab
                self.updateTabContent()
                # update table
                self.updateTableContent()
    
    
    def onSiteChecked(self):
        # call onSelect if there's item selected in listView
        
        # it is safe to call onSelect directly without any items in listView
        # the inner function will detect the items and will skip if there is none
        # if self.getTestItemNums():
        self.onSelect()
            
            
    def isTestFail(self, test_num, site):
        offsetL = self.dataSrc[site][test_num]["Offset"]
        lengthL = self.dataSrc[site][test_num]["Length"]
        recType = self.dataSrc[site][test_num]["RecType"]
        endian = self.dataSrc[site][test_num]["Endian"]
        # parse data on-the-fly
        RecordParser.endian = endian    # specify the parse endian
        testDict = RecordParser.parse_rawList(recType, offsetL, lengthL, self.std_handle, failCheck=True)
        
        try:
            testDict["StatList"].index(False)
            return True     # no error indicates False is found, aka, test failed
        except ValueError:
            return False
                        
            
    def prepareData(self, selectItemNums, selectSites):
        # clear
        self.selData = {}
        
        if selectItemNums:
            for test_num in selectItemNums:
                for site in selectSites:
                    offsetL = self.dataSrc[site][test_num]["Offset"]
                    lengthL = self.dataSrc[site][test_num]["Length"]
                    recType = self.dataSrc[site][test_num]["RecType"]
                    endian = self.dataSrc[site][test_num]["Endian"]
                    dutIndex = self.dataSrc[site][test_num]["DUTIndex"]
                    # parse data on-the-fly
                    RecordParser.endian = endian    # specify the parse endian
                    testDict = RecordParser.parse_rawList(recType, offsetL, lengthL, self.std_handle)
                    # Add new keys
                    testDict["DUTIndex"] = np.array(dutIndex)
                    testDict["DataList"] = np.array(testDict["DataList"], dtype="float64")
                    testDict["Min"] = np.min(testDict["DataList"])
                    testDict["Max"] = np.max(testDict["DataList"])
                    testDict["Median"] = np.median(testDict["DataList"])
                    testDict["Mean"], testDict["SDev"], testDict["Cpk"] = calc_cpk(testDict["LL"], testDict["HL"], testDict["DataList"])
                    # keys in testDict: TestName / TestNum / StatList / LL / HL / Unit / DataList / DUTIndex / Min / Max / Median / Mean / SDev / Cpk
                    tempSelDict = self.selData.setdefault(site, {})
                    tempSelDict[test_num] = testDict
                
                
    def updateTabContent(self, forceUpdate=False):
        '''
        update logic:
        if tab is not changed, insert canvas and toolbars based on test num and site
        if tab is changed, clear all and then add canvas
        '''
        tabType = self.ui.tabControl.currentIndex()
        tabChanged = (tabType != self.preTab)
        
        self.preTab = tabType       # save tab index everytime tab updates
        selTestNums = self.getTestItemNums()
        siteList = sorted(self.getCheckedSites())
        
        # generate drawings in trend , histo and bin, but bin doesn't require test items selection
        if tabType == tab.Bin or (tabType in [tab.Trend, tab.Histo] and selTestNums != None):
            # get scroll area and layout to draw plot
            '''
            tabLayout only contans 1 widgets -- qfigWidget, which is the parent of all matplot canvas and toolbars
            qfigWidget.children(): 1st is qfigLayout, others are canvas
            qfigLayout contains the references to all canvas and toolbars
            qfigLayout.itemAt(index).widget(): canvas or toolbars
            canvas and toolbars can be deleted by  qfigLayout.itemAt(index).widget().setParent(None)
            '''
            canvasIndexDict = {}
            canvasPriorityDict = {}
            # get tab layout
            tabLayout = self.tab_dict[tabType]["layout"]
            
            if tabChanged or forceUpdate:
                # clear all contents
                [tabLayout.itemAt(i).widget().setParent(None) for i in range(tabLayout.count())[::-1]]
                # add new widget
                qfigWidget = QtWidgets.QWidget(self.tab_dict[tabType]["scroll"])
                qfigWidget.setStyleSheet("background-color: transparent")    # prevent plot flicking when updating
                qfigLayout = QtWidgets.QVBoxLayout()
                qfigWidget.setLayout(qfigLayout)
                tabLayout.addWidget(qfigWidget)
                
            else:
                try:
                    # get testnum/site of current canvas/toolbars and corresponding widget index
                    qfigWidget = self.tab_dict[tabType]["layout"].itemAt(0).widget()
                    qfigLayout = qfigWidget.children()[0]
                except AttributeError:
                    # add new widget
                    qfigWidget = QtWidgets.QWidget(self.tab_dict[tabType]["scroll"])
                    qfigWidget.setStyleSheet("background-color: transparent")    # prevent plot flicking when updating
                    qfigLayout = QtWidgets.QVBoxLayout()
                    qfigWidget.setLayout(qfigLayout)
                    tabLayout.addWidget(qfigWidget)
                    
                def getCanvasDicts(qfigLayout):
                    canvasIndexDict = {}
                    canvasPriorityDict = {}
                    for index in range(qfigLayout.count()):
                        mp_widget = qfigLayout.itemAt(index).widget()
                        if mp_widget.isCanvas:
                            # skip toolbar widget
                            mp_test_num = mp_widget.test_num
                            mp_site = mp_widget.site
                            priority = float("%d.%03d"%(mp_test_num, mp_site+1))    # use test_num.site as priority to sort the images based on test number and sites in ascending order, assuming site number < 1000
                            canvasIndexDict[(mp_test_num, mp_site)] = index
                            canvasPriorityDict[priority] = index
                    return canvasIndexDict, canvasPriorityDict
                
                canvasIndexDict, canvasPriorityDict = getCanvasDicts(qfigLayout)    # get current indexes
                        
                # delete canvas/toolbars that are not selected
                canvasIndexDict_reverse = {v:k for k, v in canvasIndexDict.items()}     # must delete from large index, invert dict to loop from large index
                for index in sorted(canvasIndexDict_reverse.keys(), reverse=True):
                    (mp_test_num, mp_site) = canvasIndexDict_reverse[index]
                    if (tabType != tab.Bin and not mp_test_num in selTestNums) or (not mp_site in siteList):
                        # bin don't care about testNum
                        qfigLayout.itemAt(index+1).widget().setParent(None)     # must delete toolbar first (index+1)
                        qfigLayout.itemAt(index).widget().setParent(None)
                        
                canvasIndexDict, canvasPriorityDict = getCanvasDicts(qfigLayout)    # update after deleting some images
                        
            def calculateCanvasIndex(test_num, site, canvasPriorityDict):
                # get index to which the new plot should be inserted
                Pr = float("%d.%03d"%(test_num, site+1))
                PrList = list(canvasPriorityDict.keys())
                PrList.append(Pr)
                PrIndex = sorted(PrList).index(Pr)
                calculatedIndex = canvasPriorityDict.get(PrList[PrIndex-1], -2) + 2
                return calculatedIndex
                            
            if tabType == tab.Bin:
                # bin chart is independent of test items
                for site in siteList[::-1]:
                    if (0, site) in canvasIndexDict:
                        # no need to draw image for a existed testnum and site
                        continue
                    calIndex = calculateCanvasIndex(0, site, canvasPriorityDict)
                    # draw
                    self.genPlot(site, 0, tabType, updateTab=True, insertIndex=calIndex)
            else:
                for test_num in selTestNums[::-1]:
                    for site in siteList[::-1]:
                        if (test_num, site) in canvasIndexDict:
                            # no need to draw image for a existed testnum and site
                            continue
                        calIndex = calculateCanvasIndex(test_num, site, canvasPriorityDict)
                        # draw
                        self.genPlot(site, test_num, tabType, updateTab=True, insertIndex=calIndex)
            
        # update info tab only when test items are selected
        elif tabType == tab.Info and selTestNums != None:
            # clear table
            self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
        
            headerLabels = ["Part ID", "Test Number / Site", "Test Name", "Unit", "Low Limit", "High Limit", "Value", "Test Flag"]
            self.tmodel_raw.setHorizontalHeaderLabels(headerLabels)
            self.ui.rawDataTable.horizontalHeader().setVisible(True)
            
            # All sites is misleading in raw data table, replace with all available sites in current file
            if -1 in siteList:
                siteList = self.availableSites
                self.prepareData(selTestNums, siteList + [-1])  # we have to include All site when preparing data, dataTable may need the data
            
            for test_num in selTestNums:
                for site in siteList:
                    rowList = self.prepareTableContent(tab.Info, site=site, test_num=test_num, RawData=True)
                    
                    for tmpRow in rowList:
                        status = tmpRow[-1]     # the last element is test flag, see headerLabels
                        qitemRow = []
                        for item in tmpRow:
                            qitem = QtGui.QStandardItem(item)
                            qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                            qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                            # mark red when failed
                            if status == "Fail": qitem.setData(QtGui.QColor(QtGui.QColor(204, 0, 0)), QtCore.Qt.BackgroundRole)
                            qitemRow.append(qitem)                        
                        self.tmodel_raw.appendRow(qitemRow)
                        
            self.resizeCellWidth(self.ui.rawDataTable)
                                    
        # remaining cases are: no test items in tab trend, histo, info
        else:
            # when no test item is selected, clear trend & histo tab content
            if tabType in [tab.Trend, tab.Histo]:
                tabLayout = self.tab_dict[tabType]["layout"]
                # clear current content in the layout in reverse order - no use
                [tabLayout.itemAt(i).widget().setParent(None) for i in range(tabLayout.count())]
            else:
                # clear rawDataTable in info tab
                self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
            
            
    def prepareTableContent(self, tabType, **kargs):
        if tabType == tab.Trend or tabType == tab.Histo or tabType == tab.Info:
            site = kargs["site"]
            test_num = kargs["test_num"]
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
            
            if "RawData" in kargs and kargs["RawData"]:
                # return data for raw data table
                testDict = self.selData[site][test_num]
                DUTIndex = testDict["DUTIndex"]
                DataList = testDict["DataList"]
                StatList = testDict["StatList"]
                rowList = []    # 2d list
                for index, value, status in zip(DUTIndex, DataList, StatList):
                    tmpRow = [self.dataInfo.dutDict.get(index, {"PART_ID": "MissingID"})["PART_ID"],
                                "%d / %s" % (test_num, "All Sites" if site == -1 else "Site%d"%site),
                                "%s" % testDict["TestName"],
                                "%s" % testDict["Unit"],
                                "" if self.selData[site][test_num]["LL"] == None else valueFormat % self.selData[site][test_num]["LL"],
                                "" if self.selData[site][test_num]["HL"] == None else valueFormat % self.selData[site][test_num]["HL"],
                                valueFormat % value,
                                "%s" % "Pass" if status else ("Fail" if status == False else "")]            
                    rowList.append(tmpRow)
            
            else:
                # return data for statistic table
                rowList = ["%d / %s" % (test_num, "All Sites" if site == -1 else "Site%d"%site),
                        self.selData[site][test_num]["TestName"],
                        self.selData[site][test_num]["Unit"],
                        "" if self.selData[site][test_num]["LL"] == None else valueFormat % self.selData[site][test_num]["LL"],
                        "" if self.selData[site][test_num]["HL"] == None else valueFormat % self.selData[site][test_num]["HL"],
                        "%d" % self.selData[site][test_num]["StatList"].count(False),
                        "%s" % "∞" if self.selData[site][test_num]["Cpk"] == np.inf else ("" if self.selData[site][test_num]["Cpk"] is np.nan else valueFormat % self.selData[site][test_num]["Cpk"]),
                        valueFormat % self.selData[site][test_num]["Mean"],
                        valueFormat % self.selData[site][test_num]["Median"],
                        valueFormat % self.selData[site][test_num]["SDev"],
                        valueFormat % self.selData[site][test_num]["Min"],
                        valueFormat % self.selData[site][test_num]["Max"]]
            return rowList
        
        elif tabType == tab.Bin:
            bin = kargs["bin"]
            site = kargs["site"]
            rowList = []
            
            if bin == "HBIN":
                hbin_count = self.dataInfo.hbinSUM[site]
                hbin_info = self.dataInfo.hbinDict
                HList = sorted(hbin_count.keys())
                HCnt = [hbin_count[i] for i in HList]
                
                rowList.append("%s / %s" % ("Hardware Bin", "All Sites" if site == -1 else "Site%d"%site))
                for bin_num, cnt in zip(HList, HCnt):
                    if cnt == 0: continue
                    item = ["Bin%d: %.1f%%"%(bin_num, 100*cnt/sum(HCnt)), "Unknown"]
                    if bin_num in hbin_info:
                        item[0] = hbin_info[bin_num][0] + "\n" + item[0]
                        item[1] = hbin_info[bin_num][1]
                    rowList.append(item)
                        
            elif bin == "SBIN":
                sbin_count = self.dataInfo.sbinSUM[site]
                sbin_info = self.dataInfo.sbinDict
                SList = sorted(sbin_count.keys())
                SCnt = [sbin_count[i] for i in SList]
                
                rowList.append("%s / %s" % ("Software Bin", "All Sites" if site == -1 else "Site%d"%site))
                for bin_num, cnt in zip(SList, SCnt):
                    if cnt == 0: continue
                    item = ["Bin%d: %.1f%%"%(bin_num, 100*cnt/sum(SCnt)), "Unknown"]
                    if bin_num in sbin_info:
                        item[0] = sbin_info[bin_num][0] + "\n" + item[0]
                        item[1] = sbin_info[bin_num][1]
                    rowList.append(item)
                                    
            return rowList
      
      
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
        if stretchToFit and sum(min_widthList) <= hHeaderWidth:
            delta_wid = int((hHeaderWidth - sum(min_widthList)) / len(min_widthList))
            # add delta to each element
            for w in min_widthList:
                WL.append(w + delta_wid)
        else:
            # too many columns that part of contents will definity be covered, add more space to column
            WL = [w + 20 for w in min_widthList]
                
        for column, width in enumerate(WL):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
            # use the calculated width
            header.resizeSection(column, width)        
            
            
    def updateTableContent(self):
        tabType = self.ui.tabControl.currentIndex()
        # clear table
        self.tmodel.removeRows(0, self.tmodel.rowCount())
        selTestNums = self.getTestItemNums()
        verticalHeader = self.ui.dataTable.verticalHeader()
        
        if tabType == tab.Trend or tabType == tab.Histo or tabType == tab.Info:
            # set col headers except Bin Chart
            headerLabels = ["Test Name", "Unit", "Low Limit", "High Limit", "Fail Num", "Cpk", "Average", "Median", "St. Dev.", "Min", "Max"]
            indexOfFail = headerLabels.index("Fail Num")    # used for pickup fail number when iterating
            self.tmodel.setHorizontalHeaderLabels(headerLabels)     
            self.ui.dataTable.horizontalHeader().setVisible(True)
            verticalHeader.setDefaultSectionSize(25)
 
            if selTestNums:
                # update data
                rowHeader = []
                for test_num in selTestNums:
                    for site in sorted(self.getCheckedSites()):
                        rowList = self.prepareTableContent(tabType, site=site, test_num=test_num)
                        # create QStandardItem and set TextAlignment
                        qitemList = []
                        rowHeader.append(rowList.pop(0))    # pop the 1st item as row header
                        for index in range(len(rowList)):
                            item  = rowList[index]
                            qitem = QtGui.QStandardItem(item)
                            qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                            qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                            if index == indexOfFail:
                                if item != "0": 
                                    qitem.setData(QtGui.QColor(QtGui.QColor(255, 255, 255)), QtCore.Qt.ForegroundRole)
                                    qitem.setData(QtGui.QColor(QtGui.QColor(204, 0, 0)), QtCore.Qt.BackgroundRole)
                            qitemList.append(qitem)
                        self.tmodel.appendRow(qitemList)
                        
                self.tmodel.setVerticalHeaderLabels(rowHeader)
                self.ui.dataTable.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
                self.tmodel.setColumnCount(len(headerLabels))
            self.resizeCellWidth(self.ui.dataTable)
                
        elif tabType == tab.Bin:
            self.tmodel.setHorizontalHeaderLabels([])
            self.ui.dataTable.horizontalHeader().setVisible(False)
            verticalHeader.setDefaultSectionSize(35)
            rowHeader = []
            colSize = 0
            for binType in ["HBIN", "SBIN"]:
                for site in sorted(self.getCheckedSites()):
                    rowList = self.prepareTableContent(tabType, bin=binType, site=site)
                    qitemList = []
                    rowHeader.append(rowList[0])    # the 1st item as row header
                    colSize = len(rowList)-1 if len(rowList)-1>colSize else colSize     # get max length
                    for item in rowList[1:]:
                        qitem = QtGui.QStandardItem(item[0])
                        qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                        qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                        # set color
                        if item[1] == "P":      bc = QtGui.QColor(0, 204, 0); fc = QtGui.QColor(0, 0, 0)
                        elif item[1] == "F":    bc = QtGui.QColor(204, 0, 0); fc = QtGui.QColor(255, 255, 255)
                        else:                   bc = QtGui.QColor(254, 123, 0); fc = QtGui.QColor(0, 0, 0)
                        qitem.setData(QtGui.QColor(bc), QtCore.Qt.BackgroundRole)
                        qitem.setData(QtGui.QColor(fc), QtCore.Qt.ForegroundRole)
                        qitemList.append(qitem)
                    self.tmodel.appendRow(qitemList)
                    
            self.tmodel.setVerticalHeaderLabels(rowHeader)
            self.ui.dataTable.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
            # remove unnecessary blank columns, better than remove columns cuz the latter will cause flicking when updating data
            self.tmodel.setColumnCount(colSize)
            self.resizeCellWidth(self.ui.dataTable, stretchToFit=False)
                
    
    def genPlot(self, site, test_num, tabType, **kargs):
        # create fig & canvas
        fig = plt.Figure((9, 4))
        # fig.tight_layout()
        fig.set_tight_layout(True)
        canvas = FigureCanvas(fig)
        # prevent the canvas to shrink beyond a point
        # original size looks like a good minimum size
        canvas.setMinimumSize(canvas.size())
        # binds to widget
        if "updateTab" in kargs and kargs["updateTab"] and "insertIndex" in kargs:
                qfigWidget = self.tab_dict[tabType]["layout"].itemAt(0).widget()
                qfigLayout = qfigWidget.children()[0]
                
                canvas.setParent(qfigWidget)
                toolbar = NavigationToolbar(canvas, qfigWidget)
                setattr(canvas, "test_num", test_num)
                setattr(canvas, "site", site)
                setattr(canvas, "priority", float("%d.%03d"%(test_num, site+1)))
                setattr(canvas, "isCanvas", True)
                setattr(toolbar, "isCanvas", False)
                # place the fig and toolbar in the layout
                index = kargs["insertIndex"]
                qfigLayout.insertWidget(index, canvas)
                qfigLayout.insertWidget(index+1, toolbar)
        
        # customize plot
        site_color = {-1: "#00CC00", 0: "#00B3FF", 1: "#FF9300", 2: "#EC4EFF", 3: "#00FFFF",
                      4: "#AA8D00", 5: "#FFB1FF", 6: "#929292", 7: "#FFFB00"}
                
        if tabType == tab.Trend:   # Trend
            ax = fig.add_subplot(111)
            ax.set_title("%d %s - %s"%(self.selData[site][test_num]["TestNum"], self.selData[site][test_num]["TestName"], "All Sites" if site == -1 else "Site%d"%site), fontsize=15, fontname="Tahoma")
            # x_arr = np.array(range(len(self.selData[site][test_num]["DataList"])))
            x_arr = self.selData[site][test_num]["DUTIndex"]
            y_arr = self.selData[site][test_num]["DataList"]
            HL = self.selData[site][test_num]["HL"]
            LL = self.selData[site][test_num]["LL"]
            med = self.selData[site][test_num]["Median"]
            avg = self.selData[site][test_num]["Mean"]
            # connect magnet cursor
            self.cursorDict[site] = MagCursor(ax, x_arr, y_arr, self.settingParams.dataPrecision)
            canvas.mpl_connect('motion_notify_event', self.cursorDict[site].mouse_move)
            canvas.mpl_connect('resize_event', self.cursorDict[site].canvas_resize)
            ax.callbacks.connect('xlim_changed', self.cursorDict[site].canvas_resize)
            ax.callbacks.connect('ylim_changed', self.cursorDict[site].canvas_resize)
            # plot            
            ax.plot(x_arr, y_arr, "-o", markersize=6, markeredgewidth=0.5, markeredgecolor="black", linewidth=0.5, color=site_color[site if site<0 else site%8], zorder = 0, label="Data")
            # axes label
            ax.ticklabel_format(useOffset=False)    # prevent + sign
            ax.set_xlabel("%s"%("DUT Index"), fontsize=12, fontname="Tahoma")
            ax.set_ylabel("%s%s"%(self.selData[site][test_num]["TestName"], " (%s)"%self.selData[site][test_num]["Unit"] if self.selData[site][test_num]["Unit"] else ""), fontsize=12, fontname="Tahoma")
            # limits
            ax.set_xlim(left = x_arr[0] - (x_arr[-1]-x_arr[0]) * 0.05)
            data_max = self.selData[site][test_num]["Max"]
            data_min = self.selData[site][test_num]["Min"]
            if HL != None and HL != None: # if HL/LL is not None, set ylim based on HL/LL or data
                if HL == LL:
                    ax.set_ylim((LL-1, HL+1))   # if HL/HL is not None, and they are identical, place the HL/LL line in the middle
                else:
                    headroomY = max((data_max-data_min), (HL-LL)) * 0.1     # use the bigger delta to calc the headroom
                    ax.set_ylim((LL-headroomY, HL+headroomY))
            else:
                ax.set_ylim((data_min-5, data_max+5))   # if HL/LL is None, set ylim based on data
            # reset limits if data points are out of canvas
            if data_max  > ax.get_ylim()[1]:
                ax.set_ylim(top = data_max + (data_max-data_min) * 0.1)
            if self.selData[site][test_num]["Min"]  < ax.get_ylim()[0]:
                ax.set_ylim(bottom = data_min - (data_max-data_min) * 0.1)
            # HL/LL lines
            if self.settingParams.showHL_trend: 
                if HL != None: 
                    ax.axhline(y = HL, linewidth=3, color='r', zorder = -10, label="Upper Limit")
                    ax.text(x=ax.get_xlim()[0], y=HL, s=" HLimit = %.3f\n"%HL, color='r', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left", va="center")
            if self.settingParams.showLL_trend:
                if LL != None: 
                    ax.axhline(y = LL, linewidth=3, color='b', zorder = -10, label="Lower Limit")
                    ax.text(x=ax.get_xlim()[0], y=LL, s="\n LLimit = %.3f"%LL, color='b', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left", va="center")
            # data labels
            med_text = ("Med = %.3f \n" if med > avg else "\nMed = %.3f ") % med
            avg_text = ("\nAvg = %.3f " if med > avg else "Avg = %.3f \n") % avg
            # set xlim to prevent text and data point overlap, convert str len to plot pixel by times 14
            headroomX, _ = [i-j for i,j in zip(toDCoord(ax, (len(med_text)*16, 0)), toDCoord(ax, (0, 0)))]
            ax.set_xlim(right = x_arr[-1]+headroomX)
            # add med and avg text at the right edge of the plot
            if self.settingParams.showMed_trend:
                ax.text(x=ax.get_xlim()[1], y=med, s=med_text, color='k', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center")
                ax.axhline(y = med, linewidth=1, color='k', zorder = 1, label="Median")
            if self.settingParams.showMean_trend:
                ax.text(x=ax.get_xlim()[1], y=avg, s=avg_text, color='orange', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center")
                ax.axhline(y = avg, linewidth=1, color='orange', zorder = 2, label="Mean")
        
        elif tabType == tab.Histo:   # Histogram
            ax = fig.add_subplot(111)
            ax.set_title("%d %s - %s"%(self.selData[site][test_num]["TestNum"], self.selData[site][test_num]["TestName"], "All Sites" if site == -1 else "Site%d"%site), fontsize=15, fontname="Tahoma")
            dataList = self.selData[site][test_num]["DataList"]
            HL = self.selData[site][test_num]["HL"]
            LL = self.selData[site][test_num]["LL"]
            med = self.selData[site][test_num]["Median"]
            avg = self.selData[site][test_num]["Mean"]
            sd = self.selData[site][test_num]["SDev"]
            bin_num = self.settingParams.binCount
            # note: len(bin_edges) = len(hist) + 1
            hist, bin_edges = np.histogram(dataList, bins = bin_num)
            bin_width = bin_edges[1]-bin_edges[0]
            # use bar to draw histogram, only for its "align" option 
            ax.bar(bin_edges[:len(hist)], hist, width=bin_width, color=site_color[site if site<0 else site%8], edgecolor="black", zorder = 0, label="Histo Chart")
            # draw boxplot
            if self.settingParams.showBoxp_histo:
                ax_box = ax.twinx()
                ax_box.axis('off')  # hide axis and tick for boxplot
                ax_box.boxplot(dataList, showfliers=False, vert=False, notch=True, widths=0.5, patch_artist=True,
                               boxprops=dict(color='b', facecolor=(1, 1, 1, 0)),
                               capprops=dict(color='b'),
                               whiskerprops=dict(color='b'))
            # ax.hist(dataList, bins="auto", facecolor="green", zorder = 0)
            if self.settingParams.showHL_histo:
                if HL != None: 
                    ax.axvline(x = HL, linewidth=3, color='r', zorder = -10, label="Upper Limit")
            if self.settingParams.showLL_histo:
                if LL != None: 
                    ax.axvline(x = LL, linewidth=3, color='b', zorder = -10, label="Lower Limit")
            # gauss fitting
            # def gaussian(x, a, mean, sigma):
            #     return a * np.exp(-((x - mean)**2 / (2 * sigma**2)))
            # popt, pcov = curve_fit(gaussian, bin_edges[:len(hist)], hist, [max(hist), self.selData[site][test_num]["Mean"], self.selData[site][test_num]["SDev"]], maxfev=100000)
            # g_x = np.linspace(self.selData[site][test_num]["Mean"] - self.selData[site][test_num]["SDev"] * 10, self.selData[site][test_num]["Mean"] + self.selData[site][test_num]["SDev"] * 10, 1000)
            # g_y = gaussian(g_x, *popt)
            # ax.plot(g_x, g_y, "k--")
            
            # get amplitude thru least square fitting
            # fitting_A, _ = leastsq(lambda A, y, x: y - A * norm.pdf(x, loc=avg, scale=sd), max(hist), args=(hist, bin_edges[:len(hist)]))
            # g_x = np.linspace(self.selData[site][test_num]["Mean"] - self.selData[site][test_num]["SDev"] * 10, self.selData[site][test_num]["Mean"] + self.selData[site][test_num]["SDev"] * 10, 1000)
            # g_y = fitting_A * norm.pdf(g_x, loc=avg, scale=sd)

            # set xlimit and draw fitting curve only when standard deviation is not 0
            if sd != 0:
                if self.settingParams.showGaus_histo:
                    # gauss fitting
                    g_x = np.linspace(avg - sd * 10, avg + sd * 10, 1000)
                    g_y = max(hist) * np.exp( -0.5 * (g_x - avg)**2 / sd**2 )
                    ax.plot(g_x, g_y, "r--", label="Normalized Gauss Curve")
                # set x limit
                if bin_edges[0] > avg - sd * 10:
                    ax.set_xlim(left=avg - sd * 10)
                if bin_edges[-1] < avg + sd * 10:
                    ax.set_xlim(right=avg + sd * 10)
            ax.set_ylim(top=max(hist)*1.1)
                
            # vertical lines for n * σ
            sigmaList = self.settingParams.showSigma
            axis_to_data = ax.transAxes + ax.transData.inverted()
            for n in sigmaList:
                position_pos = avg + sd * n
                position_neg = avg - sd * n
                ax.axvline(x = position_pos, linewidth=1, ls='-.', color='gray', zorder = 2, label="%dσ"%n)
                ax.axvline(x = position_neg, linewidth=1, ls='-.', color='gray', zorder = 2, label="-%dσ"%n)
                _, ypos = axis_to_data.transform([0, 0.98])
                ax.text(x = position_pos, y = ypos, s="%dσ"%n, c="gray", ha="center", va="top", backgroundcolor="white", fontname="Courier New", fontsize=10)
                ax.text(x = position_neg, y = ypos, s="-%dσ"%n, c="gray", ha="center", va="top", backgroundcolor="white", fontname="Courier New", fontsize=10)
            # med avg text labels / lines
            med_text = ("\n Med = %.3f ") % med
            avg_text = ("\n Avg = %.3f ") % avg
            if self.settingParams.showMed_histo:
                ax.text(x=med, y=ax.get_ylim()[1], s=med_text, color='k', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left" if med>avg else "right", va="center")
                ax.axvline(x = med, linewidth=1, color='black', zorder = 1, label="Median")
            if self.settingParams.showMean_histo:
                ax.text(x=avg, y=ax.get_ylim()[1], s=avg_text, color='orange', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right" if med>avg else "left", va="center")
                ax.axvline(x = avg, linewidth=1, color='orange', zorder = 2, label="Mean")
            ax.ticklabel_format(useOffset=False)    # prevent + sign
            ax.set_xlabel("%s%s"%(self.selData[site][test_num]["TestName"], " (%s)"%self.selData[site][test_num]["Unit"] if self.selData[site][test_num]["Unit"] else ""), fontsize=12, fontname="Tahoma")
            ax.set_ylabel("%s"%("DUT Counts"), fontsize=12, fontname="Tahoma")
            
        elif tabType == tab.Bin:   # Bin Chart
            fig.suptitle("%s - %s"%("Bin Summary", "All Sites" if site == -1 else "Site%d"%site), fontsize=15, fontname="Tahoma")
            ax_l = fig.add_subplot(121)
            ax_r = fig.add_subplot(122)
            binColorDict = {"P": "#00CC00", "F": "#CC0000"}
            Tsize = lambda barNum: 10 if barNum <= 6 else round(5 + 5 * 2 ** (0.4*(6-barNum)))  # adjust fontsize based on bar count
            # HBIN plot
            hbin_count = self.dataInfo.hbinSUM[site]
            hbin_info = self.dataInfo.hbinDict
            HList = sorted(hbin_count.keys())
            HCnt = [hbin_count[i] for i in HList]
            HLable = []
            HColor = []
            for ind, i in enumerate(HList):
                HLable.append(hbin_info.get(i, [str(i)])[0])  # get bin name if dict is not empty, else use bin number
                HColor.append(binColorDict.get(hbin_info.get(i, "  ")[1], "#FE7B00"))    # if dict is empty, use orange as default, if Bin type is unknown, use orange
                ax_l.text(x=ind, y=HCnt[ind], s="Bin%d\n%.1f%%"%(i, 100*HCnt[ind]/sum(HCnt)), ha="center", va="bottom", fontsize=Tsize(len(HCnt)))
                
            ax_l.bar(np.arange(len(HCnt)), HCnt, color=HColor, edgecolor="black", zorder = 0, label="HardwareBin Summary")
            ax_l.set_xticks(np.arange(len(HCnt)))
            ax_l.set_xticklabels(labels=HLable, rotation=30, ha='right', fontsize=1+Tsize(len(HCnt)))    # Warning: This method should only be used after fixing the tick positions using Axes.set_xticks. Otherwise, the labels may end up in unexpected positions.
            ax_l.set_xlim(-.5, max(3, len(HCnt))-.5)
            ax_l.set_ylim(top=max(HCnt)*1.2)
            ax_l.set_xlabel("Hardware Bin", fontsize=12, fontname="Tahoma")
            ax_l.set_ylabel("Hardware Bin Counts", fontsize=12, fontname="Tahoma")

            # SBIN plot
            sbin_count = self.dataInfo.sbinSUM[site]
            sbin_info = self.dataInfo.sbinDict
            SList = sorted(sbin_count.keys())
            SCnt = [sbin_count[i] for i in SList]
            SLable = []
            SColor = []
            for ind, i in enumerate(SList):
                SLable.append(sbin_info.get(i, [str(i)])[0])  # get bin name if dict is not empty, else use bin number
                SColor.append(binColorDict.get(sbin_info.get(i, "  ")[1], "#FE7B00"))    # if dict is empty, use orange as default, if Bin type is unknown, use orange
                ax_r.text(x=ind, y=SCnt[ind], s="Bin%d\n%.1f%%"%(i, 100*SCnt[ind]/sum(SCnt)), ha="center", va="bottom", fontsize=Tsize(len(SCnt)))
                
            ax_r.bar(np.arange(len(SCnt)), SCnt, color=SColor, edgecolor="black", zorder = 0, label="SoftwareBin Summary")
            ax_r.set_xticks(np.arange(len(SCnt)))
            ax_r.set_xticklabels(labels=SLable, rotation=30, ha='right', fontsize=1+Tsize(len(SCnt)))
            ax_r.set_xlim(-.5, max(3, len(SCnt))-.5)
            ax_r.set_ylim(top=max(SCnt)*1.2)
            ax_r.set_xlabel("Software Bin", fontsize=12, fontname="Tahoma")
            ax_r.set_ylabel("Software Bin Counts", fontsize=12, fontname="Tahoma")

        if "exportImg" in kargs and kargs["exportImg"] == True:
            imgData = io.BytesIO()
            fig.savefig(imgData, format="png", dpi=200, bbox_inches="tight")
            return imgData
            
            
    def updateCursorPrecision(self):
        for site, cursor in self.cursorDict.items():
            cursor.updatePrecision(self.settingParams.dataPrecision)
            
            
    def releaseMemory(self):
        # clear cache to release memory
        RecordParser.cache = {}
        self.selData = {}
        # clear images
        [[self.tab_dict[key]["layout"].itemAt(index).widget().setParent(None) for index in range(self.tab_dict[key]["layout"].count())] for key in [tab.Trend, tab.Histo, tab.Bin]]
    
    
    def callFileLoader(self, stdHandle):
        if stdHandle:
            self.releaseMemory()
            stdfLoader(stdHandle, self.signals, self)

        
    @Slot(stdfSummarizer)
    def updateData(self, smz):
        if smz:
            self.dataSrc = smz.data
            self.dataInfo = smz     # attrs: fileInfo; pinDict; hbinSUM; sbinSUM; hbinDict; sbinDict;
    
            # update listView
            self.completeTestList = ["%d\t%s"%(test_num, self.dataSrc[-1][test_num]["TestName"]) for test_num in sorted(self.dataSrc[-1].keys())]
            self.updateTestList(self.completeTestList)
            
            # remove site checkbox for invalid sites
            current_exist_site = list(self.site_cb_dict.keys())     # avoid RuntimeError: dictionary changed size during iteration
            for site in current_exist_site:
                if site not in self.dataSrc:
                    self.site_cb_dict.pop(site)
                    row = 1 + site//4
                    col = site % 4
                    cb_layout = self.ui.gridLayout_site_select.itemAtPosition(row, col)
                    if cb_layout is not None:
                        cb_layout.widget().deleteLater()
                        self.ui.gridLayout_site_select.removeItem(cb_layout)
                                 
            # add & enable checkboxes for each sites
            self.availableSites = [i for i in self.dataSrc.keys() if i != -1]
            for siteNum in self.availableSites:
                if siteNum in self.site_cb_dict:
                    # skip if already have a checkbox for this site
                    continue
                siteName = "Site %d" % siteNum
                self.site_cb_dict[siteNum] = QtWidgets.QCheckBox(self.ui.site_selection)
                self.site_cb_dict[siteNum].setObjectName(siteName)
                self.site_cb_dict[siteNum].setText(siteName)
                row = 1 + siteNum//4
                col = siteNum % 4
                self.ui.gridLayout_site_select.addWidget(self.site_cb_dict[siteNum], row, col)
                
            self.init_SiteCheckbox()
            self.updateFileHeader()
            self.updateDutSummary()
            self.updateTableContent()
            self.updateTabContent(forceUpdate=True)
    
    @Slot(str)
    def updateStatus(self, new_msg):
        self.statusBar().showMessage(new_msg)
            
        
        
if __name__ == '__main__':
    # sys.argv.append("Test path")
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication([])
    app.setStyle('Fusion')
    app.setWindowIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Icon"], format = 'SVG'))))
    # default font for dialogs
    f = QtGui.QFont()
    f.setFamily("Tahoma")
    app.setFont(f)
    
    window = MyWindow()
    window.show()
    window.callFileLoader(window.std_handle)
    sys.exit(app.exec_())
    
