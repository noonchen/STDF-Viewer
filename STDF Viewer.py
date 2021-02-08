#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
# -----
# Last Modified: Mon Feb 08 2021
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



import io, os, sys, gzip, bz2
import numpy as np
from base64 import b64decode
from deps.ui.ImgSrc_svg import ImgDict
from deps.pystdf.RecordParser import RecordParser
from deps.stdfOffsetRetriever import stdfSummarizer

from deps.uic_stdLoader import stdfLoader
from deps.uic_stdFailMarker import FailMarker
from deps.uic_stdExporter import stdfExporter
from deps.uic_stdSettings import stdfSettings
from deps.uic_stdDutData import DutDataReader

# pyqt5
from deps.ui.stdfViewer_MainWindows import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QFileDialog, QAbstractItemView, QStyledItemDelegate
from PyQt5.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot
# pyside2
# from deps.ui.stdfViewer_MainWindows_side import Ui_MainWindow
# from PySide2 import QtCore, QtWidgets, QtGui
# from PySide2.QtWidgets import QApplication, QFileDialog, QAbstractItemView, QStyledItemDelegate
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
tab = Tab(["Info", "Trend", "Histo", "Bin", "Wafer"])

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

    def __init__(self, line, precision):
        self.pixRange = 20
        self.line = line
        self.ax = line.axes
        self.rangeX, self.rangeY = [i-j for i,j in zip(toDCoord(self.ax, (self.pixRange, self.pixRange)), toDCoord(self.ax, (0, 0)))]   # convert pixel to data
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
        
        ishover, data = self.line.contains(event)
        if ishover:
            ind = data["ind"][0]
            x = self.line._xorig[ind]
            y = self.line._yorig[ind]
            if abs(x-event.xdata) > 2*self.rangeX or abs(y-event.ydata) > 2*self.rangeY:
                return
            # update the line positions
            self.marker.set_offsets([[x, y]])
            text = 'Dut# : %d\nValue: ' % x + self.valueFormat % y
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
    cpkThreshold = 1.33
    

class StyleDelegateForTable_List(QStyledItemDelegate):
    """
    Customize highlight style for ListView & TableView
    """
    color_default = QtGui.QColor("#0096ff")

    def paint(self, painter, option, index):
        if option.state & QtWidgets.QStyle.State_Selected:
            # font color, foreground color
            # fgcolor = self.getColor(option, index, "FG")
            option.palette.setColor(QtGui.QPalette.HighlightedText, Qt.black)
            # background color
            bgcolor = self.combineColors(self.getColor(option, index, "BG"), self.color_default)
            option.palette.setColor(QtGui.QPalette.Highlight, bgcolor)    # change color for listView
            painter.fillRect(option.rect, bgcolor)    # change color for tableView
        QStyledItemDelegate.paint(self, painter, option, index)

    def getColor(self, option, index, pos):
        qitem = None
        # TableView
        if isinstance(self.parent(), QtWidgets.QTableView):
            qitem = self.parent().model().itemFromIndex(index)

        # ListView
        if isinstance(self.parent(), QtWidgets.QListView):
            row = index.row()
            qitem = self.parent().model().sourceModel().item(row)   # my listView uses proxyModel
        
        if qitem:
            if pos == "BG":
                if qitem.background() != QtGui.QBrush():
                        return qitem.background().color()
            if pos == "FG":
                if qitem.foreground() != QtGui.QBrush():
                        return qitem.foreground().color()
        return option.palette.color(QtGui.QPalette.Base)

    def combineColors(self, c1, c2):
        c3 = QtGui.QColor()
        c3.setRed(int(c1.red()*0.7 + c2.red()*0.3))
        c3.setGreen(int(c1.green()*0.7 + c2.green()*0.3))
        c3.setBlue(int(c1.blue()*0.7 + c2.blue()*0.3))
        return c3


class signals4MainUI(QtCore.QObject):
    dataSignal = Signal(stdfSummarizer)  # get std data from loader
    statusSignal = Signal(str, bool)   # status bar


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
        self.stdHandleList = [None]
        self.std_handle = None
        
        pathList = [item for item in sys.argv[1:] if os.path.isfile(item)]
        if pathList: 
            f = pathList[0]     # only open the first file
            if f.endswith("gz"):
                self.std_handle = gzip.open(f, 'rb')
                setattr(self.std_handle, "name", f)     # manually add file path to gz/bzip handler
            elif f.endswith("bz2"):
                self.std_handle = bz2.BZ2File(f, 'rb')
                setattr(self.std_handle, "name", f)
            else:
                self.std_handle = open(f, 'rb')
            self.stdHandleList.append(self.std_handle)
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
        self.ui.actionReadDutData.triggered.connect(self.onReadDutData)
        
        # init and connect signals
        self.signals = signals4MainUI()
        self.signals.dataSignal.connect(self.updateData)
        self.signals.statusSignal.connect(self.updateStatus)
        # init search-related UI
        self.ui.SearchBox.textChanged.connect(self.proxyModel_list.setFilterWildcard)
        self.ui.ClearButton.clicked.connect(self.clearSearchBox)
        self.completeTestList = []
        self.completeWaferList = []
        
        self.tab_dict = {tab.Trend: {"scroll": self.ui.scrollArea_trend, "layout": self.ui.verticalLayout_trend},
                         tab.Histo: {"scroll": self.ui.scrollArea_histo, "layout": self.ui.verticalLayout_histo},
                         tab.Bin: {"scroll": self.ui.scrollArea_bin, "layout": self.ui.verticalLayout_bin},
                         tab.Wafer: {"scroll": self.ui.scrollArea_wafer, "layout": self.ui.verticalLayout_bin}}
        self.ui.tabControl.currentChanged.connect(self.onSelect)    # table should be updated as well
        # add a toolbar action at the right side
        self.ui.spaceWidgetTB = QtWidgets.QWidget()
        self.ui.spaceWidgetTB.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.ui.toolBar.addWidget(self.ui.spaceWidgetTB)
        self.ui.toolBar.addAction(self.ui.actionAbout)
        # disable wafer tab in default
        self.ui.tabControl.setTabEnabled(4, False)
        
        
    def openNewFile(self):
        f, _typ = QFileDialog.getOpenFileName(self, 
                                             caption="Select a STD File To Open", 
                                             filter="STDF (*.std; *.stdf);;Compressed STDF (*.gz; *.bz2);;All Files (*.*)",)
        if os.path.isfile(f):
            if f.endswith("gz"):
                self.std_handle = gzip.open(f, 'rb')
                setattr(self.std_handle, "name", f)     # manually add file path to gz/bzip handler
            elif f.endswith("bz2"):
                self.std_handle = bz2.BZ2File(f, 'rb')
                setattr(self.std_handle, "name", f)
            else:
                self.std_handle = open(f, 'rb')            
            # clear handles on each new file open
            self.stdHandleList.append(self.std_handle)   # if a file is already open, its handle is saved in case the new file not opened successfully
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
        msgBox.setInformativeText("For instructions, please refer to the ReadMe in the repo:<br><a href='https://github.com/noonchen/STDF_Viewer'>noonchen @ STDF_Viewer</a><br><br><span style='font-size:8px'>Disclaimer: This free app is licensed under GPL 3.0, you may use it free of charge but WITHOUT ANY WARRANTY, it might contians bugs so use it at your own risk.</span>")
        appIcon = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(ImgDict["Icon"], format = 'SVG'))
        appIcon.setDevicePixelRatio(2.0)
        msgBox.setIconPixmap(appIcon)
        msgBox.exec_()
        
    
    def onReadDutData(self):
        selectedRows = self.ui.dutInfoTable.selectionModel().selectedRows()
        if selectedRows:
            selectedDutIndex = [self.Row_DutIndexDict[r.row()] for r in selectedRows]   # if row(s) is selected, self.Row_DutIndexDict is already updated in self.prepareDataForDUTSummary()
            DutDataReader(self, selectedDutIndex, StyleDelegateForTable_List())     # pass styleDelegate because I don't want to copy the code...
    
    
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
        # rawData table
        self.tmodel_raw = QtGui.QStandardItemModel()
        self.ui.rawDataTable.setModel(self.tmodel_raw)
        self.ui.rawDataTable.setItemDelegate(StyleDelegateForTable_List(self.ui.rawDataTable))
        # dut summary table
        self.tmodel_dut = QtGui.QStandardItemModel()
        self.ui.dutInfoTable.setModel(self.tmodel_dut)
        self.ui.dutInfoTable.setSelectionBehavior(QAbstractItemView.SelectRows)     # select row only
        self.ui.dutInfoTable.setItemDelegate(StyleDelegateForTable_List(self.ui.dutInfoTable))
        self.ui.dutInfoTable.addAction(self.ui.actionReadDutData)   # add context menu for reading dut data
        # file header table
        self.tmodel_info = QtGui.QStandardItemModel()
        self.ui.fileInfoTable.setModel(self.tmodel_info)
        self.ui.fileInfoTable.setSelectionMode(QAbstractItemView.NoSelection)
        # self.ui.fileInfoTable.setItemDelegate(StyleDelegateForTable_List(self.ui.fileInfoTable))
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
        
        
    def updateModelContent(self, model, newList):
        # clear first
        model.clear()
        
        for data in newList:
            model.appendRow(QtGui.QStandardItem(data))


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
        self.tmodel_dut.removeColumns(0, self.tmodel_dut.columnCount())
        
        headerLabels = ["Part ID", "Test Site", "Tests Executed", "Test Time", "Hardware Bin", "Software Bin", "DUT Flag"]
        self.tmodel_dut.setHorizontalHeaderLabels(headerLabels)
        header = self.ui.dutInfoTable.horizontalHeader()
        header.setVisible(True)
        siteList = sorted(self.getCheckedSites())
        
        dutInfo = self.prepareDataForDUTSummary(siteList, updateRow_dutIndex_dict=True)
        for tmpRow in dutInfo:
            qitemRow = []
            for item in tmpRow:
                qitem = QtGui.QStandardItem(item)
                qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                # mark red when failed
                if tmpRow[-1] == "Failed": 
                    qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                    qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                qitemRow.append(qitem)                        
            self.tmodel_dut.appendRow(qitemRow)            
            
        for column in range(header.count()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
        
        
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
                
    
    def getSelectedNums(self):
        selectedIndex = None
        
        if self.ui.tabControl.currentIndex() == tab.Wafer:
            selectedIndex = self.selModel_wafer.selection().indexes()
        else:
            selectedIndex = self.selModel.selection().indexes()
        
        if selectedIndex:
            return sorted([int(ind.data().split("\t")[0]) for ind in selectedIndex])
        else:
            return None
    
    
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
        
        if self.dataSrc:
            itemNums = self.getSelectedNums()
            # get enabled sites
            siteList = self.getCheckedSites()
            # prepare the data for plot and table, skip in Bin & Wafer tab to save time
            if not currentTab in [tab.Bin, tab.Wafer]: self.prepareData(itemNums, siteList)
            
            # update bin chart only if sites changed and previous tab is not bin chart
            if self.preSiteSelection == set(siteList) and currentTab == tab.Bin and self.preTab == tab.Bin:
                # do not update
                pass
            else:
                # update site selection
                self.preSiteSelection = set(siteList)
                # update table
                self.updateTableContent()
                # update tab
                self.updateTabContent()     # do not change order, updating raw data table may alter the tmp data
                # update DUT summary
                self.updateDutSummary()
    
    
    def onSiteChecked(self):
        # call onSelect if there's item selected in listView
        
        # it is safe to call onSelect directly without any items in listView
        # the inner function will detect the items and will skip if there is none
        # if self.getSelectedNums():
        self.onSelect()
            
            
    def cacheOmittedRecordField(self):
        #MUST pre-read and cache OPT_FLAG, RES_SCAL, LLM_SCAL, HLM_SCAL of a test item from the first record
        # as it may be omitted in the later record, causing typeError when user directly selects sites where 
        # no such field value is available in the data preparation.
        arbSite = list(self.dataSrc.keys())[0]
        for test_num in self.dataSrc[arbSite].keys():
            recType, endian, _, offsetL, lengthL = self.mergeAllSiteTestData(test_num)
            offset_1st = offsetL[0]
            lengthL_1s = lengthL[0]
            
            self.std_handle.seek(offset_1st, 0)
            rawByte_1st = self.std_handle.read(lengthL_1s)
            
            RecordParser.updateOCache(recType, lengthL_1s, rawByte_1st)
    
    
    def isTestFail(self, test_num, site):
        if site == -1:
            recType, endian, _, offsetL, lengthL = self.mergeAllSiteTestData(test_num)
        else:
            offsetL = self.dataSrc[site][test_num]["Offset"]
            lengthL = self.dataSrc[site][test_num]["Length"]
            recType = self.dataSrc[site][test_num]["RecType"]
            endian = self.dataSrc[site][test_num]["Endian"]
        # parse data on-the-fly
        RecordParser.endian = endian    # specify the parse endian
        testDict = RecordParser.parse_rawList(recType, offsetL, lengthL, self.std_handle, failCheck=True)
        
        try:
            testDict["StatList"].index(False)
            return "testFailed"     # no error indicates False is found, aka, test failed
        except ValueError:
            # if the test passed, check if cpk is lower than the threshold
            threshold = self.settingParams.cpkThreshold
            _, _, cpk = calc_cpk(testDict["LL"], testDict["HL"], testDict["DataList"])
            if cpk != np.nan:
                # check cpk only if it's valid
                if cpk < threshold:
                    return "cpkFailed"

            return "testPassed"
                        
            
    def mergeAllSiteTestData(self, test_num):
        # get UnOrdered offsetL, lengthL & dutIndex list from all sites
        uo_dutIndex = []
        uo_offsetL = []
        uo_lengthL = []
        recType = None
        endian = ""
        
        for site in self.dataSrc.keys():
            if site == -1:
                continue     # manually skip 
            uo_offsetL += self.dataSrc[site][test_num]["Offset"]
            uo_lengthL += self.dataSrc[site][test_num]["Length"]
            uo_dutIndex += self.dataSrc[site][test_num]["DUTIndex"]        
            recType = self.dataSrc[site][test_num]["RecType"]
            endian = self.dataSrc[site][test_num]["Endian"]
        sorted_lists = sorted(zip(uo_dutIndex, uo_offsetL, uo_lengthL), key=lambda x: x[0])
        dutIndex, offsetL, lengthL = [[x[i] for x in sorted_lists] for i in range(3)]
        return recType, endian, dutIndex, offsetL, lengthL
            
            
    def prepareData(self, selectItemNums, selectSites):
        # clear
        self.selData = {}
        
        if selectItemNums:
            for test_num in selectItemNums:
                for site in selectSites:
                    if site == -1:
                        recType, endian, dutIndex, offsetL, lengthL = self.mergeAllSiteTestData(test_num)
                    else:
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
        # check if redraw is required, but if previous tab is Wafer, no need to redraw as they are independent
        reDrawTab = (tabType != self.preTab) and (self.preTab != tab.Wafer)
        
        self.preTab = tabType       # save tab index everytime tab updates
        selTestNums = self.getSelectedNums()
        siteList = sorted(self.getCheckedSites())
        
        # generate wafer maps
        if tabType == tab.Wafer:
            pass
        
        # generate drawings in trend , histo and bin, but bin doesn't require test items selection
        elif tabType == tab.Bin or (tabType in [tab.Trend, tab.Histo] and selTestNums != None):
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
            
            if reDrawTab or forceUpdate:
                # clear all contents
                [tabLayout.itemAt(i).widget().setParent(None) for i in range(tabLayout.count())[::-1]]
                # add new widget
                qfigWidget = QtWidgets.QWidget(self.tab_dict[tabType]["scroll"])
                qfigWidget.setStyleSheet("background-color: transparent")    # prevent plot flicking when updating
                qfigLayout = QtWidgets.QVBoxLayout()
                qfigWidget.setLayout(qfigLayout)
                tabLayout.addWidget(qfigWidget)
                # clear cursor dict used in trend chart
                self.cursorDict = {}
                
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
            
        # update Raw Data table in info tab only when test items are selected
        elif tabType == tab.Info and selTestNums != None:
            """
            1st col: Part ID
            2nd col: site
            3rd+ col: test items
            """
            hheaderLabels = ["Part ID", "Site"]
            vheaderLabels_base = ["Test Number", "HLimit", "LLimit", "Unit"]
            vh_len = len(vheaderLabels_base)
            # clear raw data table
            self.tmodel_raw.removeColumns(0, self.tmodel_raw.columnCount())
            self.tmodel_raw.removeRows(0, self.tmodel_raw.rowCount())
            
            # All sites is misleading in raw data table, replace with all available sites in current file
            if -1 in siteList:
                siteList = self.availableSites
            
            # Append Part ID & site to the table first
            dutInfo = self.prepareDataForDUTSummary(siteList)
            dut_ID_Site = [[L[i] for L in dutInfo] for i in [0, 1]]     # index0: ID; index1: Site
            dut_ID_Site = [["N/A"]*vh_len + L for L in dut_ID_Site]     # add blank to match with the test data
            vheaderLabels = vheaderLabels_base + ["#%d"%(i+1) for i in range(len(dutInfo))]
            
            for L in dut_ID_Site:
                qitemCol = []
                for i, item in enumerate(L):
                    qitem = QtGui.QStandardItem(item)
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    if i < vh_len: qitem.setData(QtGui.QColor("#0F80FF7F"), QtCore.Qt.BackgroundRole)
                    qitemCol.append(qitem)
                self.tmodel_raw.appendColumn(qitemCol)            
            
            # Append Test data
            for test_num in selTestNums:
                test_data_list, test_flag_list = self.prepareDataForDUTSummary(siteList, test_num=test_num, exportTestFlag=True)
                hheaderLabels.append(test_data_list[0])  # add test number to header list
                
                qitemCol = []
                for i, (item, flag) in enumerate(zip(test_data_list[1:], test_flag_list[1:])):
                    qitem = QtGui.QStandardItem(item)
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    # mark red when failed, flag == False == Fail
                    if flag == False: qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                    if i < vh_len: qitem.setData(QtGui.QColor("#0F80FF7F"), QtCore.Qt.BackgroundRole)
                    qitemCol.append(qitem)
                self.tmodel_raw.appendColumn(qitemCol)
                        
            self.tmodel_raw.setHorizontalHeaderLabels(hheaderLabels)
            self.tmodel_raw.setVerticalHeaderLabels(vheaderLabels)
            self.ui.rawDataTable.horizontalHeader().setVisible(True)
            self.ui.rawDataTable.verticalHeader().setVisible(True)
                        
            self.resizeCellWidth(self.ui.rawDataTable, stretchToFit=False)
                                    
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
        
        elif tabType == tab.Bin or tabType == tab.Wafer:
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
      
      
    def prepareDataForDUTSummary(self, siteList, updateRow_dutIndex_dict=False, **kargs):
        """
        Provide data for DUT summary sheet in exported excel
        if selectedDutIndex in kargs, siteList is ignored
        if test_num is in kargs: return its test data sorted by dutIndex
        if test_num and exportTestFlag in kargs, return [data, flag]
        else: return dut info sorted by dutIndex
        """
        valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
        dutDict = self.dataInfo.dutDict
        dut_data_dict = None
        dut_status_dict = None
        data = []
        flag = []
        selectedDutIndex = []
        
        if "selectedDutIndex" in kargs and kargs["selectedDutIndex"] != []:
            selectedDutIndex = kargs["selectedDutIndex"]
        else:
            for dutIndex in sorted(dutDict.keys()):
                site = dutDict[dutIndex]["SITE_NUM"]
                # skip dutIndex if its site is not selected
                if not (site in siteList or -1 in siteList): continue
                selectedDutIndex.append(dutIndex)
                    
        if "test_num" in kargs:
            test_num = kargs["test_num"]
            recType, endian, dutIndexList, offsetL, lengthL = self.mergeAllSiteTestData(test_num)
            # get offset & length of selected dut only
            ind_tested = []
            # dutL_no_test = []
            for dI in selectedDutIndex:
                try:
                    ind_tested.append(dutIndexList.index(dI))
                except ValueError:
                    # Some dut may skip certain test, meaning dI may not present in 
                    # dutIndexList, which is the list of duts that contain test_num
                    # dutL_no_test.append(dI)
                    pass
                    
            selectedOffsetL = [offsetL[i] for i in ind_tested]
            selectedLengthL = [lengthL[i] for i in ind_tested]
            # parse selected
            RecordParser.endian = endian    # specify the parse endian
            testDict = RecordParser.parse_rawList(recType, selectedOffsetL, selectedLengthL, self.std_handle)
            # for those dut in iL_no_test, insert default value to DataList & StatList manually
            # for dut_no_test in dutL_no_test:
            #     ind = selectedDutIndex.index(dut_no_test)
            #     testDict["DataList"].insert(ind, "")
            #     testDict["StatList"].insert(ind, True)  # default True to bypass fail check
            
            if testDict:
                dut_data_dict = dict(zip([dutIndexList[i] for i in ind_tested], testDict["DataList"]))   # used for search test data by dutIndex
                dut_status_dict = dict(zip([dutIndexList[i] for i in ind_tested], testDict["StatList"]))   # used for search status by dutIndex
            else:
                # if selectedOffsetL is empty, testDict is also empty
                dut_data_dict = {}
                dut_status_dict = {}
                # find test name in self.completeTestList
                testDict["TestName"] = ""
                for t_num, t_name in map(lambda x: x.split("\t", 1), self.completeTestList):
                    if t_num == "%d"%test_num:
                        testDict["TestName"] = t_name
                        break
                testDict["HL"] = None
                testDict["LL"] = None
                testDict["Unit"] = ""
                
            # headers: ["Test Name", "Test Number", "Upper Limit", "Lower Limit", "Unit"]
            data = [testDict["TestName"],
                    "%d" % test_num,
                    "" if testDict["HL"] == None else valueFormat % testDict["HL"],
                    "" if testDict["LL"] == None else valueFormat % testDict["LL"],
                    testDict["Unit"]]
            flag = [True] * len(data)     # append True (Pass) at beginning to match with data

        for dutIndex in selectedDutIndex:
            hbin = dutDict[dutIndex]["HARD_BIN"]
            sbin = dutDict[dutIndex]["SOFT_BIN"]
            site = dutDict[dutIndex]["SITE_NUM"]
            
            if "test_num" in kargs:
                # append data of test_num for all selected dutIndex
                data.append("Not Tested" if not dutIndex in dut_data_dict else valueFormat % dut_data_dict[dutIndex])
                flag.append(True if not dutIndex in dut_status_dict else dut_status_dict[dutIndex])
            else:
                # dut info without any test data    
                tmpRow = [dutDict.get(dutIndex, {"PART_ID": "MissingID"})["PART_ID"], 
                        "Site %d" % site, 
                        "%d" % dutDict[dutIndex]["NUM_TEST"],
                        "%d ms" % dutDict[dutIndex]["TEST_T"],
                        "Bin %d - %s" % (hbin, self.dataInfo.hbinDict[hbin][0]),
                        "Bin %d - %s" % (sbin, self.dataInfo.sbinDict[sbin][0]),
                        "%s" % dutDict[dutIndex]["PART_FLG"]]
                data.append(tmpRow)
                
        if updateRow_dutIndex_dict:
            # this dict is used to get dutIndex of specified row in dut info table
            # since this func has multiple reference, we'd like this dict to update only when the tableView is changing
            # key: row in dut table; value: dutIndex
            self.Row_DutIndexDict = dict(zip(range(len(selectedDutIndex)), selectedDutIndex))
                
        if "exportTestFlag" in kargs and kargs["exportTestFlag"]:
            data = [data, flag]
        return data
    
    
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
        selTestNums = self.getSelectedNums()
        verticalHeader = self.ui.dataTable.verticalHeader()
        
        if tabType == tab.Trend or tabType == tab.Histo or tabType == tab.Info:
            # set col headers except Bin Chart
            headerLabels = ["Test Name", "Unit", "Low Limit", "High Limit", "Fail Num", "Cpk", "Average", "Median", "St. Dev.", "Min", "Max"]
            indexOfFail = headerLabels.index("Fail Num")    # used for pickup fail number when iterating
            indexOfCpk = headerLabels.index("Cpk")
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
                                    qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                                    qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
                            elif index == indexOfCpk:
                                if item != "" and item != "∞":
                                    if float(item) < self.settingParams.cpkThreshold:
                                        qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                                        qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
                            qitemList.append(qitem)
                        self.tmodel.appendRow(qitemList)
                        
                self.tmodel.setVerticalHeaderLabels(rowHeader)
                self.ui.dataTable.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
                self.tmodel.setColumnCount(len(headerLabels))
            self.resizeCellWidth(self.ui.dataTable)
                
        elif tabType == tab.Bin or tabType == tab.Wafer:
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
                        if item[1] == "P":      bc = "#00CC00"; fc = "#000000"
                        elif item[1] == "F":    bc = "#CC0000"; fc = "#FFFFFF"
                        else:                   bc = "#FE7B00"; fc = "#000000"
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
            # plot            
            trendLine, = ax.plot(x_arr, y_arr, "-o", markersize=6, markeredgewidth=0.5, markeredgecolor="black", linewidth=0.5, color=site_color[site if site<0 else site%8], zorder = 0, label="Data")
            # connect magnet cursor
            cursorKey = "%d_%d"%(test_num, site)
            self.cursorDict[cursorKey] = MagCursor(trendLine, self.settingParams.dataPrecision)
            canvas.mpl_connect('motion_notify_event', self.cursorDict[cursorKey].mouse_move)
            canvas.mpl_connect('resize_event', self.cursorDict[cursorKey].canvas_resize)
            ax.callbacks.connect('xlim_changed', self.cursorDict[cursorKey].canvas_resize)
            ax.callbacks.connect('ylim_changed', self.cursorDict[cursorKey].canvas_resize)
            # axes label
            ax.ticklabel_format(useOffset=False)    # prevent + sign
            ax.set_xlabel("%s"%("DUT Index"), fontsize=12, fontname="Tahoma")
            ax.set_ylabel("%s%s"%(self.selData[site][test_num]["TestName"], " (%s)"%self.selData[site][test_num]["Unit"] if self.selData[site][test_num]["Unit"] else ""), fontsize=12, fontname="Tahoma")
            # limits
            ax.set_xlim(left = x_arr[0] - (x_arr[-1]-x_arr[0]) * 0.05)
            data_max = self.selData[site][test_num]["Max"]
            data_min = self.selData[site][test_num]["Min"]
            dataDelta = data_max - data_min
            
            if (HL != None) and (LL != None): # if HL/LL is not None, set ylim based on HL/LL or data
                largeDelta = max(dataDelta, (HL-LL))     # use the bigger delta to calc the headroom
                headroomY = 5 if largeDelta == 0 else largeDelta * 0.1
                ax.set_ylim((LL-headroomY, HL+headroomY))
            else:   # if HL/LL is None, set ylim based on data
                headroomY = 5 if dataDelta == 0 else dataDelta * 0.1
                ax.set_ylim((data_min-headroomY, data_max+headroomY))
                
            # reset limits if data points are out of canvas
            if data_max  > ax.get_ylim()[1]:
                ax.set_ylim(top = data_max + dataDelta * 0.1)
            if self.selData[site][test_num]["Min"]  < ax.get_ylim()[0]:
                ax.set_ylim(bottom = data_min - dataDelta * 0.1)
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
        for _, cursor in self.cursorDict.items():
            cursor.updatePrecision(self.settingParams.dataPrecision)
            
            
    def releaseMemory(self):
        # clear cache to release memory
        RecordParser.cache = {}
        RecordParser.ocache = {}
        self.selData = {}
        # clear images
        [[self.tab_dict[key]["layout"].itemAt(index).widget().setParent(None) for index in range(self.tab_dict[key]["layout"].count())] for key in [tab.Trend, tab.Histo, tab.Bin]]
    
    
    def callFileLoader(self, stdHandle):
        if stdHandle:
            self.releaseMemory()
            stdfLoader(stdHandle, self.signals, self)

        
    @Slot(stdfSummarizer)
    def updateData(self, smz):
        if len(smz.data) != 0:
            # store new std file handler
            self.stdHandleList = [self.std_handle]
            
            self.dataSrc = smz.data
            self.dataInfo = smz     # attrs: fileInfo; pinDict; hbinSUM; sbinSUM; hbinDict; sbinDict; waferInfo; waferDict
            
            # disable/enable wafer tab
            self.ui.tabControl.setTabEnabled(4, self.dataInfo.waferInfo != {})
    
            # update listView
            arbSite = list(self.dataSrc.keys())[0]    # get an arbitrary site number to get test number & test name
            self.completeTestList = ["%d\t%s"%(test_num, self.dataSrc[arbSite][test_num]["TestName"]) for test_num in sorted(self.dataSrc[arbSite].keys())]
            self.updateModelContent(self.sim_list, self.completeTestList)
            self.completeWaferList = ["%d\t%s"%(waferIndex, self.dataInfo.waferDict[waferIndex]["WAFER_ID"]) for waferIndex in sorted(self.dataInfo.waferDict.keys())]
            self.updateModelContent(self.sim_list_wafer, self.completeWaferList)
            
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
            # set max height in order to resize site selection groupbox
            self.ui.site_selection.setMaximumHeight(60 + self.ui.gridLayout_site_select.cellRect(0, 0).height()*(2 + siteNum//4))   # 2 + siteNum//4 == total row in grid layout
            
            self.init_SiteCheckbox()
            self.updateFileHeader()
            self.updateDutSummary()
            self.updateTableContent()
            self.updateTabContent(forceUpdate=True)
            self.cacheOmittedRecordField()
            
        else:
            # aborted, restore to original stdf file handler
            self.std_handle = self.stdHandleList[0]
            self.stdHandleList = [self.std_handle]

    
    @Slot(str, bool)
    def updateStatus(self, new_msg, popUp=False):
        self.statusBar().showMessage(new_msg)
        if popUp: QtWidgets.QMessageBox.warning(self, "Warning", new_msg)
            
        
        
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
    
