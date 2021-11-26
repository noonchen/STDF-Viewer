#
# STDF Viewer.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 13th 2020
# -----
# Last Modified: Fri Nov 26 2021
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



import io, os, sys, gc, traceback, toml, logging, atexit
import json, urllib.request as rq
# from memory_profiler import profile
import platform
import numpy as np
from enum import IntEnum
from random import choice
from base64 import b64decode
from operator import itemgetter
from indexed_gzip import IndexedGzipFile
from indexed_bzip2 import IndexedBzip2File
from deps.ui.ImgSrc_svg import ImgDict
from deps.ui.transSrc import transDict
from deps.DatabaseFetcher import DatabaseFetcher
from deps.cystdf import stdf_MPR_Parser, stdf_PFTR_Parser, setByteSwap

from deps.uic_stdLoader import stdfLoader
from deps.uic_stdFailMarker import FailMarker
from deps.uic_stdExporter import stdfExporter
from deps.uic_stdSettings import stdfSettings
from deps.uic_stdDutData import DutDataReader

from deps.customizedQtClass import StyleDelegateForTable_List, DutSortFilter
# pyqt5
from deps.ui.stdfViewer_MainWindows import Ui_MainWindow
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QFileDialog, QAbstractItemView, QMessageBox
from PyQt5.QtCore import QObject, Qt, QTranslator, pyqtSignal as Signal, pyqtSlot as Slot
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
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
from matplotlib.collections import PatchCollection
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

#-------------------------
# QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
# QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
QApplication.setHighDpiScaleFactorRoundingPolicy(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
Version = "V3.1.0"
isMac = platform.system() == 'Darwin'
    
# save config path to sys
rootFolder = os.path.dirname(sys.argv[0])
setattr(sys, "rootFolder", rootFolder)
base = os.path.splitext(os.path.basename(sys.argv[0]))[0]
setattr(sys, "CONFIG_PATH", os.path.join(rootFolder, base + ".config"))
# setting attr to human string
settingNamePair = [("showHL_trend", "Show Upper Limit (Trend)"), ("showLL_trend", "Show Lower Limit (Trend)"), ("showHSpec_trend", "Show High Specification (Trend)"), ("showLSpec_trend", "Show Low Specification (Trend)"), ("showMed_trend", "Show Median Line (Trend)"), ("showMean_trend", "Show Mean Line (Trend)"),
                   ("showHL_histo", "Show Upper Limit (Histo)"), ("showLL_histo", "Show Lower Limit (Histo)"), ("showHSpec_histo", "Show High Specification (Histo)"), ("showLSpec_histo", "Show Low Specification (Histo)"), ("showMed_histo", "Show Median Line (Histo)"), ("showMean_histo", "Show Mean Line (Histo)"), ("showGaus_histo", "Show Gaussian Fit"), ("showBoxp_histo", "Show Boxplot"), ("binCount", "Bin Count"), ("showSigma", "δ Lines"),
                   ("language", "Language"), ("recentFolder", "Recent Folder"), ("dataNotation", "Data Notation"), ("dataPrecision", "Data Precison"), ("cpkThreshold", "Cpk Warning Threshold"), ("checkCpk", "Search Low Cpk"),
                   ("siteColor", "Site Colors"), ("sbinColor", "Software Bin Colors"), ("hbinColor", "Hardware Bin Colors")]
setattr(sys, "CONFIG_NAME", settingNamePair)

#-------------------------
logger = logging.getLogger("STDF Viewer")
logger.setLevel(logging.WARNING)
logPath = os.path.join(rootFolder, "logs", f"{base}.log")
os.makedirs(os.path.dirname(logPath), exist_ok=True)
logFD = logging.FileHandler(logPath, mode="a+")
logFD.setFormatter(logging.Formatter('%(asctime)s : %(name)s : %(levelname)s : %(message)s'))
logger.addHandler(logFD)


def calc_cpk(L:float, H:float, data:np.ndarray) -> tuple:
    '''return mean, sdev and Cpk of given data series, 
    discarding np.nan values'''
    sdev = np.nanstd(data)
    mean = np.nanmean(data)
    
    if np.isnan(L) or np.isnan(H):
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

def deleteWidget(w2delete: QtWidgets.QWidget):
    '''delete QWidget and release its memory'''
    w2delete.setParent(None)
    w2delete.deleteLater()

def getCanvasDicts(qfigLayout: QtWidgets.QBoxLayout) -> dict:
    '''Read canvas info (tn, head, site) from the layout 
    and recording their index into a dict'''
    canvasIndexDict = {}
    for index in range(qfigLayout.count()):
        mp_widget = qfigLayout.itemAt(index).widget()
        mp_head = mp_widget.head
        mp_test_num = mp_widget.test_num
        mp_site = mp_widget.site
        canvasIndexDict[(mp_head, mp_test_num, mp_site)] = index
    return canvasIndexDict

def calculateCanvasIndex(_test_num: int, _head: int, _site: int, canvasIndexDict: dict):
    '''Given test info (tn, head, site) and calculate the proper index
    to which the new canvas should be inserted'''
    tupleList = list(canvasIndexDict.keys())
    tupleList.append( (_head, _test_num, _site) )
    # sort tuple by element 0 first, then 1, finally 2
    tupleList_sort = sorted(tupleList, key=itemgetter(0, 1, 2))
    # find the new tuple and get its index
    newTupleIndex = tupleList_sort.index( (_head, _test_num, _site) )
    return newTupleIndex

# convert from pixel coords to data coords
toDCoord = lambda ax, point: ax.transData.inverted().transform(point)
# check if a test item passed: bit7-6: 00 pass; 10 fail; x1 none, treated as pass; treat negative flag (indicate not tested) as pass
isPass = lambda flag: True if flag < 0 or flag & 0b11000000 == 0 else (False if flag & 0b01000000 == 0 else True)

# dut flag parser
def dut_flag_parser(flag: int) -> str:
    '''return detailed description of a DUT flag'''
    flagString = f"{flag:>08b}"
    bitInfo = {7: "Bit7: Bit reserved",
               6: "Bit6: Bit reserved",
               5: "Bit5: Bit reserved",
               4: "Bit4: No pass/fail indication, ignore Bit3",
               3: "Bit3: DUT failed",
               2: "Bit2: Abnormal end of testing",
               1: "Bit1: Wafer die is retested",
               0: "Bit0: DUT is retested"}
    infoList = []
    for pos, bit in enumerate(reversed(flagString)):
        if bit == "1":
            infoList.append(bitInfo[pos])
    return "\n".join(reversed(infoList))

# test flag parser
def test_flag_parser(flag: int) -> str:
    '''return detailed description of a test flag'''
    # treat negative flag (indicate not tested) as pass
    flag = 0 if flag < 0 else flag
    
    flagString = f"{flag:>08b}"
    bitInfo = {7: "Bit7: Test failed",
               6: "Bit6: Test completed with no pass/fail indication",
               5: "Bit5: Test aborted",
               4: "Bit4: Test not executed",
               3: "Bit3: Timeout occurred",
               2: "Bit2: Test result is unreliable",
               1: "Bit1: The test was executed, but no dataloagged value was taken",
               0: "Bit0: Alarm detected during testing"}
    infoList = []
    for pos, bit in enumerate(reversed(flagString)):
        if bit == "1":
            infoList.append(bitInfo[pos])
    return "\n".join(reversed(infoList))

def genQItemList(dutSumList: list[bytes]) -> list:
    '''Convert a bytes list to a QStandardItem list'''
    qitemRow = []
    fontsize = 13 if isMac else 10
    dutStatus, dutFlagString = dutSumList[-1].split(b"-")
    dutFail = dutStatus.startswith(b"Failed")
    flagInfo = dut_flag_parser(int(dutFlagString, 16))
    
    for item in dutSumList:
        qitem = QtGui.QStandardItem(item.decode("utf-8"))
        qitem.setTextAlignment(QtCore.Qt.AlignCenter)
        qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        qitem.setData(QtGui.QFont("Tahoma", fontsize), QtCore.Qt.FontRole)
        # mark red when failed
        if dutFail: 
            qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
            qitem.setData(QtGui.QColor("#CC0000"), QtCore.Qt.BackgroundRole)
        if flagInfo != "":
            qitem.setToolTip(flagInfo)
        qitemRow.append(qitem)
    return qitemRow

# simulate a Enum in python
# class Tab(tuple): __getattr__ = tuple.index
# tab = Tab(["Info", "Trend", "Histo", "Bin", "Wafer"])
class tab(IntEnum):
    Info = 0
    Trend = 1
    Histo = 2
    Bin = 3
    Wafer = 4
    
class REC(IntEnum):
    '''Constants of STDF Records: typ<<8 | sub'''
    PTR = 3850
    FTR = 3860
    MPR = 3855

# unit prefixes
unit_prefix = {15: "f",
              12: "p",
              9: "n",
              6: "u",
              3: "m",
              2: "%",
              0: "",
              -3: "K",
              -6: "M",
              -9: "G",
              -12: "T"}

# MIR field name to Description Dict
mirFieldNames = ["BYTE_ORD", "SETUP_T", "START_T", "FINISH_T", "STAT_NUM", "MODE_COD", "RTST_COD", "PROT_COD", "BURN_TIM", "CMOD_COD", "LOT_ID", "PART_TYP", "NODE_NAM", "TSTR_TYP",
                 "JOB_NAM", "JOB_REV", "SBLOT_ID", "OPER_NAM", "EXEC_TYP", "EXEC_VER", "TEST_COD", "TST_TEMP", "USER_TXT", "AUX_FILE", "PKG_TYP", "FAMLY_ID",
                 "DATE_COD", "FACIL_ID", "FLOOR_ID", "PROC_ID", "OPER_FRQ", "SPEC_NAM", "SPEC_VER", "FLOW_ID", "SETUP_ID", "DSGN_REV", "ENG_ID", "ROM_COD", "SERL_NUM", "SUPR_NAM", "DISP_COD", "USR_DESC", "EXC_DESC"]

mirDescriptions = ["Byte Order", "Setup Time", "Start Time", "Finish Time", "Station Number", "Test Mode Code", "Retest Code", "Protection Code", "Burn-in Time", "Command Mode Code", "Lot ID", "Product ID", 
                   "Node Name", "Tester Type", "Job Name", "Job Revision", "Sublot ID", "Operator ID", "Tester Software Type", "Tester Software Version", "Step ID", "Test Temperature", 
                   "User Text", "Auxiliary File Name", "Package Type", "Family ID", "Date Code", "Facility ID", "Floor ID", "Process ID", "Operation Frequency", "Test Spec Name", 
                   "Test Spec Version", "Flow ID", "Setup ID", "Design Revision", "Engineer Lot ID", "ROM Code ID", "Serial Number", "Supervisor ID", "Lot Disposition Code", "Lot Description From User", "Lot Description From Exec"]

mirDict = dict(zip(mirFieldNames, mirDescriptions))

rHEX = lambda: "#"+"".join([choice('0123456789ABCDEF') for j in range(6)])
# check if a hex color string
def isHexColor(color: str) -> bool:
    '''Check if a given str is a valid hex color #RRGGBB[AA]'''
    color = color.lower()
    if color.startswith("#") and len(color) in [7, 9]:
        hexNum = list(map(lambda num: f'{num:x}', range(16)))
        for hex in color[1:]:
            if not hex in hexNum:
                return False
        return True
    else:
        return False


class NavigationToolbar(NavigationToolbar2QT):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        
    def save_figure(self, *args):
        # reimplement save fig function, because the original one is weird
        filetypes = self.canvas.get_supported_filetypes_grouped()
        sorted_filetypes = sorted(filetypes.items())
        default_filetype = self.canvas.get_default_filetype()

        startpath = os.path.expanduser(
            matplotlib.rcParams['savefig.directory'])
        start = os.path.join(startpath, self.canvas.get_default_filename())
        filters = []
        selectedFilter = None
        for name, exts in sorted_filetypes:
            exts_list = " ".join(['*.%s' % ext for ext in exts])
            filter = '%s (%s)' % (name, exts_list)
            if default_filetype in exts:
                selectedFilter = filter
            filters.append(filter)
        filters = ';;'.join(filters)

        fname, filter = QFileDialog.getSaveFileName(
            self.canvas.parent(), "Choose a filename to save to", start,
            filters, selectedFilter)
        if fname:
            # Save dir for next time, unless empty str (i.e., use cwd).
            if startpath != "":
                matplotlib.rcParams['savefig.directory'] = (
                    os.path.dirname(fname))
            try:
                self.canvas.figure.savefig(fname, dpi=200, bbox_inches="tight")
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error saving file", str(e),
                    QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)


class PlotCanvas(QtWidgets.QWidget):
    '''Customized QWidget used for displaying a matplotlib figure'''
    def __init__(self, figure, showToolBar=True, parent=None):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.Layout = QtWidgets.QHBoxLayout(self)
        self.Layout.setSpacing(0)
        
        self.canvas = FigureCanvas(figure)
        figw, figh = figure.get_size_inches()
        self.fig_ratio = figw / figh
        self.mpl_connect = self.canvas.mpl_connect
        self.showToolBar = showToolBar
        # prevent the canvas to shrink beyond a point
        # original size looks like a good minimum size
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        # use dpi = 100 for the samllest figure, don't use self.size() <- default size of QWidget
        self.canvas.setMinimumSize(int(figw * 100), int(figh * 100))
        self.canvas.setFocusPolicy(Qt.ClickFocus)    # required for key_press_event to work
        self.head = 0
        self.site = 0
        self.test_num = 0
        self.priority = 0
        if parent:
            self.bindToUI(parent)
        
    def bindToUI(self, parent):
        self.canvas.setParent(parent)
        self.Layout.addWidget(self.canvas)
        if self.showToolBar:
            self.toolbar = NavigationToolbar(self.canvas, parent, coordinates=False)
            self.toolbar.setAllowedAreas(QtCore.Qt.RightToolBarArea)
            self.toolbar.setOrientation(QtCore.Qt.Vertical)
            self.Layout.addWidget(self.toolbar)
            self.Layout.setAlignment(self.toolbar, Qt.AlignVCenter)
            
    def setParent(self, parent):
        # only used for delete instance
        if parent is None:
            if self.showToolBar: 
                self.toolbar.setParent(None)
                self.toolbar.deleteLater()
            self.canvas.setParent(None)
            self.canvas.deleteLater()
            super().setParent(None)
            super().deleteLater()
            
    def resizeEvent(self, event):
        toolbarWidth = self.toolbar.width() if self.showToolBar else 0
        canvasWidth = event.size().width() - toolbarWidth
        self.canvas.setFixedHeight(int(canvasWidth/self.fig_ratio))
        self.updateGeometry()


class MagCursor(QObject):
    '''A class includes interactive callbacks for matplotlib figures'''
    def __init__(self, line=None, histo=None, binchart=None, wafer=None, mainGUI=None, **kargs):
        super().__init__()
        self.lineMode = False
        self.histoMode = False
        self.binMode = False
        self.waferMode = False
        
        if line is not None:
            self.lineMode = True
        elif histo is not None:
            self.histoMode = True
        elif binchart is not None:
            self.binMode = True
        elif wafer is not None:
            self.waferMode = True
            
        if mainGUI is None and not any(self.lineMode, self.histoMode, self.binMode, self.waferMode):
            raise RuntimeError("MagCursor inputs not valid")
        
        self.ax = None
        self.line = None
        self.histo = None
        self.binchart = None
        self.wafer = None
        # image cache for faster interaction
        self.background = None
        # for multi-selection control
        self.shift_pressed = False
        self.picked_points = []
        
        if self.lineMode:
            self.line = line
            self.ax = line.axes
            self.pixRange = 20
            self.rangeX, self.rangeY = [i-j for i,j in zip(toDCoord(self.ax, (self.pixRange, self.pixRange)), toDCoord(self.ax, (0, 0)))]   # convert pixel to data
            # create hover marker and data description tip, hide by default
            self.marker_line = self.ax.scatter(0, 0, s=40, marker="+", color='k')
            self.dcp_line = self.ax.text(s="", x=0, y=0, fontname=mainGUI.imageFont, weight="bold", fontsize=8,
                                    bbox=dict(boxstyle="round,pad=0.5", fc="#FFFFCC"), zorder=1000)
            self.marker_line.set_visible(False)
            self.dcp_line.set_visible(False)
            self.highlights_line = self.ax.scatter([], [], s=30, marker="$S$", color="red")
            
        elif self.histoMode:
            self.histo = histo
            self.ax = histo[0].axes     # container doesn't have axes prop
            self.bin_dut_dict = histo.bin_dut_dict
            self.dcp_histo = self.ax.text(s="", x=0, y=0, fontname=mainGUI.imageFont, weight="bold", fontsize=8,
                                          bbox=dict(boxstyle="round,pad=0.5", fc="#FFFFCC"), zorder=1000)
            self.dcp_histo.set_visible(False)
            # another bar plot indicates highlight selections
            self.highlights_histo = self.ax.bar([rec._x0 for rec in self.histo], self.histo.datavalues, width=self.histo[0]._width, 
                                                align='edge', fc=(0,0,0,0), edgecolor="red", linewidth=2, zorder=1000)
            # hide when none selected
            [rec_hl.set_visible(False) for rec_hl in self.highlights_histo]
        
        elif self.binMode:
            self.binchart = binchart
            self.ax = binchart[0].axes     # container doesn't have axes prop
            # no description for bin chart, already shown on figures
            # another bar plot indicates highlight selections
            self.highlights_bin = self.ax.bar([rec._x0 for rec in self.binchart], self.binchart.datavalues, width=self.binchart[0]._width,
                                              align='edge', fc=(0,0,0,0), edgecolor="red", linewidth=2, zorder=1000)
            # hide when none selected
            [rec_hl.set_visible(False) for rec_hl in self.highlights_bin]
        
        elif self.waferMode:
            self.wafer = wafer
            self.site = kargs["site"]
            self.wafer_num = kargs["wafer_num"]
            self.isStackMap = kargs["wafer_num"] == -1
            self.ax = wafer[0].axes     # container doesn't have axes prop
            self.dcp_wafer = self.ax.text(s="", x=0, y=0, fontname=mainGUI.imageFont, weight="bold", fontsize=8,
                                          bbox=dict(boxstyle="round,pad=0.5", fc="#FFFFCC"), zorder=1000)
            self.dcp_wafer.set_visible(False)
            self.highlights_wafer = []      # a list to store instances of ax.add_patch()
            
        self.hint = self.ax.text(s=self.tr("Press 'Enter' to show DUT data of selection(s)"), 
                                 x=1, y=1, transform=self.ax.transAxes, va="bottom", ha="right", 
                                 fontname=mainGUI.imageFont, fontsize=8, zorder=1000)
        self.hint.set_visible(False)
        # mainGUI for show dut date table
        self.mainGUI = mainGUI
        self.updatePrecision(self.mainGUI.settingParams.dataPrecision, 
                             self.mainGUI.settingParams.dataNotation)
            
    def updatePrecision(self, precision, notation):
        self.valueFormat = "%%.%d%s" % (precision, notation)
        
    def copyBackground(self):
        # hide marker & tips only, be sure to keep highlights visible
        if self.lineMode:
            self.marker_line.set_visible(False)
            self.dcp_line.set_visible(False)
        elif self.histoMode:
            self.dcp_histo.set_visible(False)
        elif self.binMode:
            pass
        elif self.waferMode:
            self.dcp_wafer.set_visible(False)
            
        self.ax.figure.canvas.draw()
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.figure.bbox)

    def mouse_move(self, event):
        if not event.inaxes:
            return
        
        ishover = False
        if self.lineMode:
            ishover, data = self.line.contains(event)
            
        elif self.histoMode:
            for rec in self.histo:
                ishover, _ = rec.contains(event)
                if ishover:
                    data = rec
                    break
                
        elif self.binMode:
            if id(event.inaxes) != id(self.ax):
                # exit if not in the current axis
                return
            
            for rec in self.binchart:
                ishover, _ = rec.contains(event)
                if ishover:
                    data = rec
                    break
        
        elif self.waferMode:
            ishoverOnCol = False
            for pcol in self.wafer:
                # loop PathCollection or quadMesh
                ishoverOnCol, containIndex = pcol.contains(event)
                if ishoverOnCol:
                    data_pcol = pcol
                    if self.isStackMap:
                        for rec_index in containIndex["ind"]:
                            # loop Paths in QuadMesh
                            rec = pcol.get_paths()[rec_index]
                            if rec.contains_point((event.xdata, event.ydata)):
                                ishover = True
                                data = rec
                                break
                    else:
                        for rec in pcol.get_paths():
                            # loop Paths in PathCollection
                            if rec.contains_point((event.xdata, event.ydata)):
                                ishover = True
                                data = rec
                                break
            
        if ishover:
            # restore background original image without any marker or tips
            if self.background:
                self.ax.figure.canvas.restore_region(self.background)
            
            if self.lineMode:
                ind = data["ind"][0]
                x = self.line.get_xdata()[ind]
                y = self.line.get_ydata()[ind]
                if abs(x-event.xdata) > 2*self.rangeX or abs(y-event.ydata) > 2*self.rangeY:
                    return
                # update the line positions
                self.marker_line.set_offsets([[x, y]])
                text = self.tr('Dut# : %d\nValue: ') % x + self.valueFormat % y
                self.dcp_line.set_text(text)
                self.dcp_line.set_position((x+self.rangeX, y+self.rangeY))
                # set visible
                self.marker_line.set_visible(True)
                self.dcp_line.set_visible(True)
                # draw new marker and tip
                self.ax.draw_artist(self.marker_line)
                self.ax.draw_artist(self.dcp_line)
                
            elif self.histoMode:
                count = data.get_height()
                binEdgeL = data.get_x()
                binEdgeR = binEdgeL + data.get_width()
                text = self.tr('Data Range: [%s, %s)\nCount: %d') % \
                               (self.valueFormat % binEdgeL, self.valueFormat % binEdgeR, count)
                self.dcp_histo.set_text(text)
                self.dcp_histo.set_position(self.ax.transData.inverted().transform((event.x+10, event.y+10)))
                self.dcp_histo.set_visible(True)
                self.ax.draw_artist(self.dcp_histo)
            
            elif self.binMode:
                pass
            
            elif self.waferMode:
                rec_bounds = data.get_extents()
                if self.isStackMap:
                    failCount = data_pcol.get_array()[rec_index]
                    if isinstance(failCount, np.ma.core.MaskedConstant):
                        # count will be masked if invalid, return if encountered
                        return
                    text = self.tr('XY: (%d, %d)\nFail Count: %d') % \
                                    (rec_bounds.x0+.5, rec_bounds.y0+.5, failCount)
                else:
                    text = self.tr('XY: (%d, %d)\nSBIN: %s\nBin Name: %s') % \
                                    (rec_bounds.x0+.5, rec_bounds.y0+.5, data_pcol.SBIN, self.tr(data_pcol.BIN_NAME))
                self.dcp_wafer.set_text(text)
                self.dcp_wafer.set_position((rec_bounds.x0+1.5, rec_bounds.y0+1.5))
                self.dcp_wafer.set_visible(True)
                self.ax.draw_artist(self.dcp_wafer)
            
            self.ax.figure.canvas.blit(self.ax.bbox)
        else:
            
            if self.background:
                self.ax.figure.canvas.restore_region(self.background)            
            
            if self.lineMode:
                self.marker_line.set_visible(False)
                self.dcp_line.set_visible(False)
                self.ax.draw_artist(self.marker_line)
                self.ax.draw_artist(self.dcp_line)
                
            elif self.histoMode:
                self.dcp_histo.set_visible(False)
                self.ax.draw_artist(self.dcp_histo)            
            
            elif self.binMode:
                pass
            
            elif self.waferMode:
                self.dcp_wafer.set_visible(False)
                self.ax.draw_artist(self.dcp_wafer)
            
            self.ax.figure.canvas.blit(self.ax.bbox)
            
    def canvas_resize(self, event):
        self.copyBackground()
        if self.lineMode:
            # update range once the canvas is resized
            self.rangeX, self.rangeY = [i-j for i,j in zip(toDCoord(self.ax, (self.pixRange, self.pixRange)), toDCoord(self.ax, (0, 0)))]   # convert pixel to data
        
    def key_press(self, event):
        if event.key == 'shift':
            self.shift_pressed = True
        elif event.key == 'enter':
            if self.picked_points:
                selectedDutIndex = []
                
                if self.lineMode:
                    selectedDutIndex = [x for (x, y) in self.picked_points]
                
                elif self.histoMode:
                    for ind in self.picked_points:
                        selectedDutIndex += self.bin_dut_dict[ind+1]    # ind from digitize starts from 1
                
                elif self.binMode:
                    for ind in self.picked_points:
                        binNum = self.binchart.binList[ind]
                        selectedDutIndex += self.mainGUI.DatabaseFetcher.getDUTIndexFromBin(self.binchart.head, self.binchart.site, 
                                                                                            binNum, self.binchart.binType)
                
                elif self.waferMode:
                    for (x, y) in self.picked_points:
                        selectedDutIndex += self.mainGUI.DatabaseFetcher.getDUTIndexFromXY(x, y, self.wafer[0].wafer_num)
                
                self.mainGUI.showDutDataTable(sorted(selectedDutIndex))
            
    def key_release(self, event):
        if event.key == 'shift':
            self.shift_pressed = False
            
    def button_press(self, event):
        if not event.inaxes:
            return
        
        # do nothing when toolbar is active
        if self.ax.figure.canvas.toolbar.mode.value:
            return
        
        # used to check if user clicked blank area, if so, clear all selected points
        contains = True     # init
        if self.lineMode:
            contains, _ = self.line.contains(event)
        
        elif self.histoMode:
            for rec in self.histo:
                contains, _ = rec.contains(event)
                if contains: break
        
        elif self.binMode:
            if id(event.inaxes) != id(self.ax):
                return
            
            for rec in self.binchart:
                contains, _ = rec.contains(event)
                if contains: break
        
        elif self.waferMode:
            for pcol in self.wafer:
                # loop PathCollection or quadMesh
                contains, containIndex = pcol.contains(event)
                if contains:
                    if self.isStackMap:
                        # for stacked map, we have to make sure
                        # user doesn't clicked on the blank area inside the QuadMesh
                        for rec_index in containIndex["ind"]:
                            # loop Paths in QuadMesh
                            rec = pcol.get_paths()[rec_index]
                            if rec.contains_point((event.xdata, event.ydata)):
                                failCount = pcol.get_array()[rec_index]
                                if isinstance(failCount, np.ma.core.MaskedConstant):
                                    contains = False
                                break
                    else:
                        # for normal wafermap, stop searching as long as 
                        # the collection contains the event
                        break
        
        if not contains:
            self.picked_points = []
            self.resetPointSelection()
            self.copyBackground()
        # otherwise will be handled by pick event
        
    def on_pick(self, event):
        # do nothing when toolbar is active
        if self.ax.figure.canvas.toolbar.mode.value:
            return
        
        if self.lineMode:
            ind = event.ind[0]
            point = (event.artist.get_xdata()[ind], event.artist.get_ydata()[ind])
        
        elif self.histoMode:
            # use the bin index as the point
            leftEdge = event.artist.get_x()
            for ind, rec_hl in enumerate(self.histo):
                if rec_hl.get_x() == leftEdge:
                    point = ind
                    break
            
        elif self.binMode:
            if id(event.artist.axes) != id(self.ax):
                # pick event will be fired if any artist 
                # inside the same canvs is clicked
                # ignore the artist not in the same axis
                return
            
            # use the bin index as the point
            leftEdge = event.artist.get_x()
            for ind, rec_hl in enumerate(self.binchart):
                if rec_hl.get_x() == leftEdge:
                    point = ind
                    break
        
        elif self.waferMode:
            pcol = event.artist
            pickIndex = event.ind
            
            if event.mouseevent.xdata is None or event.mouseevent.ydata is None:
                # clicked outside of axes
                return
                
            for rec_index in pickIndex:
                # loop Paths in QuadMesh
                rec = pcol.get_paths()[rec_index]
                if rec.contains_point((event.mouseevent.xdata, event.mouseevent.ydata)):
                    rec_bounds = rec.get_extents()
                    if self.isStackMap:
                        # check fail count only in stack map
                        failCount = pcol.get_array()[rec_index]
                        if isinstance(failCount, np.ma.core.MaskedConstant):
                            return
                    point = (rec_bounds.x0+.5, rec_bounds.y0+.5)
                    break
            else:
                # in some rare cases, event.artist doesn't contains mouseevent😅
                return
        
        if self.shift_pressed:
            if point in self.picked_points:
                # remove if existed
                self.picked_points.remove(point)
            else:
                # append points to selected points list
                self.picked_points.append(point)
        else:
            # replace with the current point only
            self.picked_points = [point]
        
        if len(self.picked_points) > 0:
            # show selected points on image
            if self.lineMode:
                self.highlights_line.set_offsets(self.picked_points)
                
            elif self.histoMode:
                [rec_hl.set_visible(True) if ind in self.picked_points else rec_hl.set_visible(False) for ind, rec_hl in enumerate(self.highlights_histo)]
            
            elif self.binMode:
                [rec_hl.set_visible(True) if ind in self.picked_points else rec_hl.set_visible(False) for ind, rec_hl in enumerate(self.highlights_bin)]
            
            elif self.waferMode:
                # remove previous
                # [rec.remove() for rec in self.ax.patches]
                self.ax.patches.clear()
                # add new
                for (x, y) in self.picked_points:
                    self.ax.add_patch(matplotlib.patches.Rectangle((x-0.5, y-0.5), 1, 1, fc=(0,0,0,0), ec="red", linewidth=2, zorder=100))
                
            self.hint.set_visible(True)
        else:
            self.resetPointSelection()
        self.copyBackground()
        
    def resetPointSelection(self):
        if self.lineMode:
            self.highlights_line.remove()
            self.highlights_line = self.ax.scatter([], [], s=40, marker='$S$', color='red')
            
        elif self.histoMode:
            [rec_hl.set_visible(False) for rec_hl in self.highlights_histo]
            
        elif self.binMode:
            [rec_hl.set_visible(False) for rec_hl in self.highlights_bin]
        
        elif self.waferMode:
            # [rec.remove() for rec in self.ax.patches]
            self.ax.patches.clear()
        
        self.hint.set_visible(False)


class SettingParams:
    def __init__(self):
        # trend
        self.showHL_trend = True
        self.showLL_trend = True
        self.showHSpec_trend = True
        self.showLSpec_trend = True
        self.showMed_trend = True
        self.showMean_trend = True
        # histo
        self.showHL_histo = True
        self.showLL_histo = True
        self.showHSpec_histo = True
        self.showLSpec_histo = True
        self.showMed_histo = True
        self.showMean_histo = True
        self.showGaus_histo = True
        self.showBoxp_histo = True
        self.binCount = 30
        self.showSigma = "3, 6, 9"
        # General
        self.language = "English"
        self.recentFolder = ""
        self.dataNotation = "G"  # F E G stand for float, Scientific, automatic
        self.dataPrecision = 3
        self.checkCpk = False
        self.cpkThreshold = 1.33
        # colors
        self.siteColor = {-1: "#00CC00", 0: "#00B3FF", 1: "#FF9300", 2: "#EC4EFF", 
                          3: "#00FFFF", 4: "#AA8D00", 5: "#FFB1FF", 6: "#929292", 7: "#FFFB00"}
        self.sbinColor = {}
        self.hbinColor = {}
    

class signals4MainUI(QtCore.QObject):
    parseStatusSignal = Signal(bool)  # get std parse status from loader
    statusSignal = Signal(str, bool, bool, bool)   # status bar


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        sys.excepthook = self.onException
        
        self.preTab = None              # used for detecting tab changes
        self.selData = {}
        self.preSiteSelection = set()    # used for detecting site selection changes
        self.preHeadSelection = set()
        self.preTestSelection = set()
        self.DatabaseFetcher = DatabaseFetcher()
        self.dbConnected = False
        self.containsWafer = False
        self.cursorDict = {}    # init/clear a dict to store cursors instance to prevent garbage collection
        self.init_SettingParams()
        self.translatorUI = QTranslator(self)
        self.translatorCode = QTranslator(self)
        self.imageFont = "Tahoma"
        # std handler
        self.stdHandleList = [None]
        self.std_handle = None
        
        pathList = [item for item in sys.argv[1:] if os.path.isfile(item)]
        if pathList: 
            f = pathList[0]     # only open the first file
            self.updateRecentFolder(f)
            if f.endswith("gz"):
                self.std_handle = IndexedGzipFile(filename=f, mode='rb')
                setattr(self.std_handle, "fpath", f)     # manually add file path to gz/bzip handler
            elif f.endswith("bz2"):
                self.std_handle = IndexedBzip2File(f, parallelization = 4)  # enable back seeking
                setattr(self.std_handle, "fpath", f)
            else:
                self.std_handle = open(f, 'rb')
                setattr(self.std_handle, "fpath", f)
            self.stdHandleList.append(self.std_handle)
            
        # init and connect signals
        self.signals = signals4MainUI()
        self.signals.parseStatusSignal.connect(self.updateData)
        self.signals.statusSignal.connect(self.updateStatus)
        # sub windows
        self.loader = stdfLoader(self.signals, self)
        self.failmarker = FailMarker(self)
        self.exporter = stdfExporter(self)
        self.settingUI = stdfSettings(self)
        self.dutDataReader = DutDataReader(self)
        # update icons for actions and widgets
        self.updateIcons()
        self.init_TestList()
        self.init_DataTable()
        self.needByteSwap = False
        # dict to store site/head checkbox objects
        self.site_cb_dict = {}
        self.head_cb_dict = {}
        self.availableSites = []
        self.availableHeads = []
        self.waferInfoDict = {}
        self.failCntDict = {}
        self.dutArray = np.array([])    # complete dut array in the stdf
        self.dutSiteInfo = {}           # site of each dut in self.dutArray
        self.dutSummaryDict = {}        # complete dut summary dict
        self.fileInfoDict = {}          # info of MIR and WCR
        # dict to store H/SBIN info
        self.HBIN_dict = {}
        self.SBIN_dict = {}
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
        self.completeTestList = []
        self.completeWaferList = []
        
        self.tab_dict = {tab.Trend: {"scroll": self.ui.scrollArea_trend, "layout": self.ui.verticalLayout_trend},
                         tab.Histo: {"scroll": self.ui.scrollArea_histo, "layout": self.ui.verticalLayout_histo},
                         tab.Bin: {"scroll": self.ui.scrollArea_bin, "layout": self.ui.verticalLayout_bin},
                         tab.Wafer: {"scroll": self.ui.scrollArea_wafer, "layout": self.ui.verticalLayout_wafer}}
        self.ui.tabControl.currentChanged.connect(self.onSelect)    # table should be updated as well
        
        self.ui.infoBox.currentChanged.connect(self.onInfoBoxChanged)
        # add a toolbar action at the right side
        self.ui.spaceWidgetTB = QtWidgets.QWidget()
        self.ui.spaceWidgetTB.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.ui.toolBar.addWidget(self.ui.spaceWidgetTB)
        self.ui.toolBar.addAction(self.ui.actionAbout)
        # disable wafer tab in default
        self.ui.tabControl.setTabEnabled(4, False)
        # close database if application is closed
        atexit.register(lambda: self.DatabaseFetcher.closeDB())
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
                msgBox.exec_()
        
    
    def changeLanguage(self):
        _app = QApplication.instance()
        # load language files based on the setting
        curLang = self.settingParams.language
        if curLang == "English":
            self.imageFont = "Tahoma"
            self.translatorUI.loadFromData(transDict["MainUI_en_US"])
            self.translatorCode.loadFromData(transDict["MainCode_en_US"])
            self.loader.translator.loadFromData(transDict["loadingUI_en_US"])
            self.failmarker.translator.loadFromData(transDict["failmarkerCode_en_US"])
            self.exporter.translatorUI.loadFromData(transDict["exportUI_en_US"])
            self.exporter.translatorCode.loadFromData(transDict["exportCode_en_US"])
            self.settingUI.translator.loadFromData(transDict["settingUI_en_US"])
            self.dutDataReader.translator.loadFromData(transDict["dutDataCode_en_US"])
            self.dutDataReader.tableUI.translator.loadFromData(transDict["dutDataUI_en_US"])
            
        elif curLang == "简体中文":
            self.imageFont = "Microsoft Yahei"
            self.translatorUI.loadFromData(transDict["MainUI_zh_CN"])
            self.translatorCode.loadFromData(transDict["MainCode_zh_CN"])
            self.loader.translator.loadFromData(transDict["loadingUI_zh_CN"])
            self.failmarker.translator.loadFromData(transDict["failmarkerCode_zh_CN"])
            self.exporter.translatorUI.loadFromData(transDict["exportUI_zh_CN"])
            self.exporter.translatorCode.loadFromData(transDict["exportCode_zh_CN"])
            self.settingUI.translator.loadFromData(transDict["settingUI_zh_CN"])
            self.dutDataReader.translator.loadFromData(transDict["dutDataCode_zh_CN"])
            self.dutDataReader.tableUI.translator.loadFromData(transDict["dutDataUI_zh_CN"])
            
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
        # failmarker
        _app.installTranslator(self.failmarker.translator)
        # dutData
        _app.installTranslator(self.dutDataReader.translator)
        # exporterCode
        _app.installTranslator(self.exporter.translatorCode)
        # mainCode
        _app.installTranslator(self.translatorCode)
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
            if k in ["language", "recentFolder", "dataNotation", "dataPrecision", "checkCpk", "cpkThreshold"]:
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
    

    def openNewFile(self, f):
        if not f:
            f, _typ = QFileDialog.getOpenFileName(self, 
                                                  caption=self.tr("Select a STD File To Open"), 
                                                  directory=self.settingParams.recentFolder,
                                                  filter=self.tr("All Supported Files (*.std *.stdf *.std* *.gz *.bz2);;STDF (*.std *.stdf);;Compressed STDF (*.gz *.bz2)"),)
        else:
            f = os.path.normpath(f)
            
        if os.path.isfile(f):
            # store folder path
            self.updateRecentFolder(f)
            
            if f.endswith("gz"):
                self.std_handle = IndexedGzipFile(filename=f, mode='rb')
                setattr(self.std_handle, "fpath", f)     # manually add file path to gz/bzip handler
            elif f.endswith("bz2"):
                self.std_handle = IndexedBzip2File(f, parallelization = 4)
                setattr(self.std_handle, "fpath", f)
            else:
                self.std_handle = open(f, 'rb')            
                setattr(self.std_handle, "fpath", f)
            # clear handles on each new file open
            self.stdHandleList.append(self.std_handle)   # if a file is already open, its handle is saved in case the new file not opened successfully
            self.callFileLoader(self.std_handle)
              
    
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
        ckupdateBtn = msgBox.addButton(self.tr("Check For Updates"), QtWidgets.QMessageBox.ActionRole)
        msgBox.addButton(self.tr("OK"), QtWidgets.QMessageBox.YesRole)
        msgBox.exec_()
        if msgBox.clickedButton() == ckupdateBtn:
            self.checkNewVersion()
        else:
            msgBox.close()
        
    
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
  
    
    def onInfoBoxChanged(self):
        # update raw data table if:
        # 1. it is activated;
        # 2. dut list changed (site & head selection changed);
        # 3. test num selection changed;
        # 4. tab changed
        updateInfoBox = False
        selHeads = []
        selSites = []
        selTestNums = []
        currentMask = np.array([])

        if self.ui.infoBox.currentIndex() == 2:              # raw data table activated
            selTestNums = self.getSelectedNums()
            selSites = self.getCheckedSites()
            selHeads = self.getCheckedHeads()
            currentMask = self.getMaskFromHeadsSites(selHeads, selSites)
            
            # test num selection changed
            tnChanged = (self.preTestSelection != set(selTestNums))
            # dut list changed
            dutChanged = np.any(currentMask != self.getMaskFromHeadsSites(self.preHeadSelection, self.preSiteSelection))
            if tnChanged or dutChanged:   
                updateInfoBox = True
            elif self.tmodel_raw.columnCount() == 0:
                updateInfoBox = True
            else:
                # if user switches to the raw table from other tabs or boxes 
                # tn & dut is unchanged, but previous raw table content might be different than current selection
                # we also need to update the table
                tn_in_table = [int(self.tmodel_raw.item(0, col).text()) \
                            for col in \
                            range(3, self.tmodel_raw.columnCount())]    # raw col count == 0 or >= 4, thus index=3 is safe
                if set(tn_in_table) != set(selTestNums):
                    updateInfoBox = True
                        
        if updateInfoBox:
            if not (selTestNums != [] and np.any(currentMask)):
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
                qitemRow = genQItemList(self.dutSummaryDict[dutIndex])
                id_head_site = [qitemRow[i] for i in range(len(hheaderLabels))]     # index0: ID; index1: Head/Site
                self.tmodel_raw.appendRow(id_head_site)
            # row header
            vheaderLabels = vheaderLabels_base + ["#%d"%(i+1) for i in range(len(selectedDUTs))]
            
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
            # Append Test data
            for test_num in selTestNums:
                # get test value of selected DUTs
                testDict = self.getData(test_num, selHeads, selSites)
                test_data_list = self.stringifyTestData(test_num, testDict, valueFormat)
                test_data_list.pop(0)   # remove test name
                test_stat_list = [True] * vh_len + list(map(isPass, testDict["flagList"]))
                test_flagInfo_list = [""] * vh_len + list(map(self.tr, map(test_flag_parser, testDict["flagList"])))
                
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
        # test summary table
        self.tmodel_raw = QtGui.QStandardItemModel()
        self.ui.rawDataTable.setModel(self.tmodel_raw)
        self.ui.rawDataTable.setItemDelegate(StyleDelegateForTable_List(self.ui.rawDataTable))
        self.ui.rawDataTable.addAction(self.ui.actionReadDutData_TS)   # add context menu for reading dut data
        # dut summary table
        self.tmodel_dut = QtGui.QStandardItemModel()
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
        if self.dbConnected:
            for (binColorDict, bin_info) in [(self.settingParams.sbinColor, self.SBIN_dict), 
                                            (self.settingParams.hbinColor, self.HBIN_dict)]:
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
                                if isHexColor(hexColor): 
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
        # clear
        self.tmodel_info.removeRows(0, self.tmodel_info.rowCount())
        
        horizontalHeader = self.ui.fileInfoTable.horizontalHeader()
        verticalHeader = self.ui.fileInfoTable.verticalHeader()
        horizontalHeader.setVisible(False)
        verticalHeader.setVisible(False)
        
        if self.std_handle is None:
            # skip the following steps if no file is loaded
            return
        
        extraInfoList = []
        # manually add rows of std file info
        absPath = os.path.realpath(self.std_handle.fpath)
        extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("File Name: "), os.path.basename(absPath)]])
        extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("Directory Path: "), os.path.dirname(absPath)]])
        extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("File Size: "), "%.2f MB"%(os.stat(self.std_handle.fpath).st_size / 2**20)]])
        if self.containsWafer:
            extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("Wafers Tested: "), str(len(self.completeWaferList))]])    # WIR #
        statsDict = self.DatabaseFetcher.getDUTStats()
        extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("DUTs Tested: "), str(statsDict["Total"])]])    # PIR #
        extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("DUTs Passed: "), str(statsDict["Pass"])]])
        extraInfoList.append([QtGui.QStandardItem(ele) for ele in [self.tr("DUTs Failed: "), str(statsDict["Failed"])]])

        # append mir info
        self.fileInfoDict = self.DatabaseFetcher.getFileInfo()
        for fn in mirFieldNames:
            value:str = self.fileInfoDict.get(fn, "")
            if fn == "BYTE_ORD":
                self.needByteSwap = not (value.lower().startswith(sys.byteorder))
            if value == "" or value == " " : continue
            extraInfoList.append([mirDict[fn] + ": ", value])
            
        # append wafer configuration info
        if self.containsWafer:
            wafer_unit = self.fileInfoDict.get("WF_UNITS", "")
            if "WAFR_SIZ" in self.fileInfoDict:
                extraInfoList.append([self.tr("Wafer Size: "), f'{self.fileInfoDict["WAFR_SIZ"]} {wafer_unit}'])
            if "DIE_WID" in self.fileInfoDict and "DIE_HT" in self.fileInfoDict:
                extraInfoList.append([self.tr("Wafer Die Width × Height: "), f'{self.fileInfoDict["DIE_WID"]} {wafer_unit} × {self.fileInfoDict["DIE_HT"]} {wafer_unit}'])
            if "CENTER_X" in self.fileInfoDict and "CENTER_Y" in self.fileInfoDict:
                extraInfoList.append([self.tr("Wafer Center: "), f'({self.fileInfoDict["CENTER_X"]}, {self.fileInfoDict["CENTER_Y"]})'])
            
            direction_symbol = {"U": self.tr("Up"), 
                                "D": self.tr("Down"), 
                                "L": self.tr("Left"), 
                                "R": self.tr("Right")}
            flat_orient = direction_symbol.get(self.fileInfoDict.get("WF_FLAT", ""), self.tr("Unknown"))
            x_orient = direction_symbol.get(self.fileInfoDict.get("POS_X", ""), self.tr("Unknown"))
            y_orient = direction_symbol.get(self.fileInfoDict.get("POS_Y", ""), self.tr("Unknown"))
            extraInfoList.append([self.tr("Wafer Flat Direction: "), f'{flat_orient}'])
            extraInfoList.append([self.tr("Wafer XY Direction: "), f'({x_orient}, {y_orient})'])
            
        for tmpRow in extraInfoList:
            qitemRow = [QtGui.QStandardItem(ele) for ele in tmpRow]
            if self.settingParams.language != "English":
                # fix weird font when switch to chinese-s
                qfont = QtGui.QFont(self.imageFont)
                [qele.setData(qfont, QtCore.Qt.FontRole) for qele in qitemRow]
            self.tmodel_info.appendRow(qitemRow)
        
        horizontalHeader.resizeSection(0, 250)
        horizontalHeader.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        horizontalHeader.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        # resize to content to show all texts, then add additional height to each row
        for row in range(self.tmodel_info.rowCount()):
            verticalHeader.setSectionResizeMode(row, QtWidgets.QHeaderView.ResizeToContents)
            newHeight = verticalHeader.sectionSize(row) + 20
            verticalHeader.setSectionResizeMode(row, QtWidgets.QHeaderView.Fixed)
            verticalHeader.resizeSection(row, newHeight)
    
    
    def updateDutSummaryTable(self):
        # clear
        self.tmodel_dut.removeRows(0, self.tmodel_dut.rowCount())
        self.tmodel_dut.removeColumns(0, self.tmodel_dut.columnCount())
        headerLabels = [self.tr("Part ID"), self.tr("Test Head - Site"), self.tr("Tests Executed"), self.tr("Test Time"), 
                        self.tr("Hardware Bin"), self.tr("Software Bin"), self.tr("DUT Flag")]
        if self.containsWafer:
            headerLabels[-1:-1] = [self.tr("Wafer ID"), "(X, Y)"]    # insert before "DUT Flag"
        self.tmodel_dut.setHorizontalHeaderLabels(headerLabels)
        header = self.ui.dutInfoTable.horizontalHeader()
        header.setVisible(True)
        
        totalDutCnt = self.dutArray.size
        self.Row_DutIndexDict = dict(zip(range(totalDutCnt), self.dutArray))
            
        # load all duts info into the table, dutArray is ordered and consecutive
        keyPoints = list(range(5, 106, 5))
        self.updateStatus(self.tr("Please wait, reading DUT information..."))
        
        for dutIndex in self.dutArray:
            itemRow = self.dutSummaryDict[dutIndex] if self.containsWafer else \
                self.dutSummaryDict[dutIndex][0:-3]+[self.dutSummaryDict[dutIndex][-1]]
            self.tmodel_dut.appendRow(genQItemList(itemRow))
            
            progress = 100 * dutIndex / totalDutCnt
            if progress >= keyPoints[0]:
                self.updateStatus(self.tr("Please wait, reading DUT information {0}%...").format(keyPoints[0]))
                keyPoints.pop(0)
        self.updateStatus("")
        
        for column in range(header.count()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
        
        
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
    
    
    def getMaskFromHeadsSites(self, selHeads:list, selSites:list) -> np.ndarray:
        # get duts of given heads and sites
        mask = np.zeros(self.dutArray.size, dtype=bool)
        for head in selHeads:
            if -1 in selSites:
                # select all sites (site is unsigned int)
                mask |= (self.dutSiteInfo[head]>=0)
                continue
            
            for site in selSites:
                mask |= (self.dutSiteInfo[head]==site)
        
        return mask
                
    
    def getSelectedNums(self) -> list:
        selectedIndex = None
        numList = []
        
        if self.ui.tabControl.currentIndex() == tab.Wafer:
            selectedIndex = self.selModel_wafer.selection().indexes()
        else:
            selectedIndex = self.selModel.selection().indexes()
        
        if selectedIndex:
            for ind in selectedIndex:
                numString = ind.data().split("\t")[0].strip("#")    # wafer number begins with "#"
                
                if numString == "-":                                # for wafer defect map
                    numList.append(-1)
                else:
                    numList.append(int(numString))
            numList.sort()
        
        return numList
    
    
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
        
        if self.dbConnected:
            itemNums = self.getSelectedNums()
            selSites = self.getCheckedSites()
            selHeads = self.getCheckedHeads()
            hsNotChanged = (self.preHeadSelection == set(selHeads) and self.preSiteSelection == set(selSites))
            tnNotChanged = (self.preTestSelection == set(itemNums))
            
            # prepare the data for plot and table, skip in Bin & Wafer tab to save time
            if (not tnNotChanged) and (not currentTab in [tab.Bin, tab.Wafer]): 
                self.prepareData(itemNums)
                        
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
                self.updateTabContent()             # update tab
            
            # always update pre selection at last
            self.preHeadSelection = set(selHeads)
            self.preSiteSelection = set(selSites)
            self.preTestSelection = set(itemNums)
    
    
    def onSiteChecked(self):
        # call onSelect if there's item selected in listView
        
        # it is safe to call onSelect directly without any items in listView
        # the inner function will detect the items and will skip if there is none
        self.onSelect()
    
    
    def stringifyTestData(self, test_num: int, testDict: dict, valueFormat: str) -> list:
        '''Stringify data for displaying and saving to reports'''
        recHeader = testDict["recHeader"]
        test_data_list = [testDict["TEST_NAME"], 
                          "%d" % test_num,
                          "N/A" if np.isnan(testDict["HL"]) else valueFormat % testDict["HL"],
                          "N/A" if np.isnan(testDict["LL"]) else valueFormat % testDict["LL"],
                          testDict["Unit"]]
            
        if recHeader == REC.FTR:
            # FTR only contains test flag
            test_data_list += [self.tr("Not Tested") if np.isnan(data) else self.tr("Test Flag: %d") % data for data in testDict["dataList"]]
            
        elif recHeader == REC.PTR:
            test_data_list += [self.tr("Not Tested") if np.isnan(data) else valueFormat % data for data in testDict["dataList"]]
            
        else:
            # MPR
            if testDict["dataList"].size == 0:
                # No PMR related and no test data in MPR, use test flag instead
                test_data_list += [self.tr("Not Tested") if flag < 0 else self.tr("Test Flag: %d") % flag for flag in testDict["flagList"]]
            else:
                # Test data may exist, use semicolon to separate multiple test values
                data_string_list = []
                for mprDataList, mprFlag in zip(testDict["dataList"].T, testDict["flagList"]):
                    if mprFlag < 0:
                        # flag of not tested is -1
                        data_string_list.append(self.tr("Not Tested"))
                    else:
                        data_string_list.append("\n".join(["%s: " % pinName + valueFormat % data for pinName, data in zip(testDict["PIN_NAME"], mprDataList)]))
                test_data_list += data_string_list
                
        return test_data_list
    
    
    def isTestFail(self, test_num):        
        if test_num in self.failCntDict:
            # test synopsis for current test item contains valid fail count
            failCount = self.failCntDict[test_num]
            if failCount > 0:
                return "testFailed"
            elif failCount == 0:
                # if user do not need to check Cpk, return to caller
                if self.settingParams.checkCpk:
                    failStateChecked = True      # avoid re-check fail state when calculating Cpk
                else:
                    return "testPassed"
            else:
                # negative indicates invalid fail cnt
                failStateChecked = False

            # when need to check Cpk, fail count for this test_num in TSR is invalid, or TSR is not omitted whatsoever
            # read test data from all heads and sites
            testInfo = self.DatabaseFetcher.getTestInfo_AllDUTs(test_num)
            offsetL = testInfo["Offset"]
            lengthL = testInfo["BinaryLen"]
            recHeader = testInfo["recHeader"]
            record_flag = testInfo["OPT_FLAG"]
            result_scale = testInfo["RES_SCAL"] if recHeader != REC.FTR and testInfo["RES_SCAL"] is not None and (record_flag & 0b00000001 == 0) else 0
            result_lolimit = testInfo["LLimit"] if recHeader != REC.FTR and testInfo["LLimit"] is not None and (record_flag & 0b01010000 == 0) else np.nan
            result_hilimit = testInfo["HLimit"] if recHeader != REC.FTR and testInfo["HLimit"] is not None and (record_flag & 0b10100000 == 0) else np.nan
            
            if recHeader == REC.MPR:
                pinCount = 0 if testInfo["RTN_ICNT"] is None else testInfo["RTN_ICNT"]
                rsltCount = 0 if testInfo["RSLT_PGM_CNT"] is None else testInfo["RSLT_PGM_CNT"]
                parsedData = stdf_MPR_Parser(recHeader, pinCount, rsltCount, offsetL, lengthL, self.std_handle)
            else:
                parsedData = stdf_PFTR_Parser(recHeader, offsetL, lengthL, self.std_handle)
            
            if not failStateChecked:
                for stat in map(isPass, parsedData["flagList"]):
                    if stat == False:
                        self.failCntDict[test_num] = 1
                        return "testFailed"
                    
            self.failCntDict[test_num] = 0
            if self.settingParams.checkCpk:
                # if all tests passed, check if cpk is lower than the threshold
                parsedData["dataList"] = np.array(parsedData["dataList"], dtype='float64')
                for head in self.availableHeads:
                    for site in self.availableSites:
                        selMask = self.getMaskFromHeadsSites([head], [site])
                        
                        if recHeader == REC.MPR:
                            # MPR's datalist can be empty or a 2d array
                            # for 2d array, selMask is for masking columns, transpose is required.
                            datalist = ((parsedData["dataList"].T)[selMask]).T
                            datalist = datalist * 10 ** result_scale
                        
                        elif recHeader == REC.PTR:
                            # PTR, manually increase the dimension to 2d array to match MPR
                            datalist = [parsedData["dataList"][selMask] * 10 ** result_scale]
                            
                        else:
                            # FTR
                            datalist = [parsedData["dataList"][selMask]]
        
                        LL = result_lolimit * 10 ** result_scale
                        HL = result_hilimit * 10 ** result_scale
                        
                        for sublist in datalist:
                            # For PTR and FTR, sublist IS the original datalist
                            # For MPR, sublists are the data of each pin or pin group
                            _, _, cpk = calc_cpk(LL, HL, sublist)
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
                        
                       
    def getDataFromOffsets(self, testInfo:dict) -> dict:
        sel_offset = testInfo.pop("Offset")
        sel_length = testInfo.pop("BinaryLen")
        recHeader = testInfo["recHeader"]
        # parse data on-the-fly
        if recHeader == REC.MPR:
            pinCount = 0 if testInfo["RTN_ICNT"] is None else testInfo["RTN_ICNT"]
            rsltCount = 0 if testInfo["RSLT_PGM_CNT"] is None else testInfo["RSLT_PGM_CNT"]
            testDict = stdf_MPR_Parser(recHeader, pinCount, rsltCount, sel_offset, sel_length, self.std_handle)
            pinNameList = self.DatabaseFetcher.getPinNames(testInfo["TEST_NUM"], "RTN")["LOG_NAM"]
            testDict["PIN_NAME"] = pinNameList
        else:
            testDict = stdf_PFTR_Parser(recHeader, sel_offset, sel_length, self.std_handle)
        
        record_flag = testInfo["OPT_FLAG"]
        result_scale = testInfo["RES_SCAL"] if recHeader != REC.FTR and testInfo["RES_SCAL"] is not None and (record_flag & 0b00000001 == 0) else 0
        result_lolimit = testInfo["LLimit"] if recHeader != REC.FTR and testInfo["LLimit"] is not None and (record_flag & 0b01010000 == 0) else np.nan
        result_hilimit = testInfo["HLimit"] if recHeader != REC.FTR and testInfo["HLimit"] is not None and (record_flag & 0b10100000 == 0) else np.nan
        result_lospec = testInfo["LSpec"] if recHeader != REC.FTR and testInfo["LSpec"] is not None and (record_flag & 0b00000100 == 0) else np.nan
        result_hispec = testInfo["HSpec"] if recHeader != REC.FTR and testInfo["HSpec"] is not None and (record_flag & 0b00001000 == 0) else np.nan
        
        result_unit = testInfo["Unit"] if recHeader != REC.FTR else ""
        
        testDict["recHeader"] = recHeader
        testDict["TEST_NAME"] = testInfo["TEST_NAME"]
        testDict["dataList"] = np.array(testDict["dataList"], dtype="float")
        testDict["flagList"] = np.array(testDict["flagList"], dtype=int)
                
        testDict["dataList"] = testDict["dataList"] if recHeader == REC.FTR else testDict["dataList"] * 10 ** result_scale
        testDict["LL"] = result_lolimit * 10 ** result_scale
        testDict["HL"] = result_hilimit * 10 ** result_scale
        testDict["LSpec"] = result_lospec * 10 ** result_scale
        testDict["HSpec"] = result_hispec * 10 ** result_scale
        testDict["Unit"] = "" if recHeader == REC.FTR else unit_prefix.get(result_scale, "") + result_unit
        testDict["Scale"] = result_scale
        
        return testDict
    
    
    def getTestValueOfDUTs(self, selDUTs: list, test_num: int) -> tuple:
        # read data of test num
        testInfo = self.DatabaseFetcher.getTestInfo_selDUTs(test_num, selDUTs)
        testDict = self.getDataFromOffsets(testInfo)
        valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
        test_data_list = self.stringifyTestData(test_num, testDict, valueFormat)
        test_stat_list = [True] * 5 + list(map(isPass, testDict["flagList"]))
        test_flagInfo_list = [""] * 5 + list(map(self.tr, map(test_flag_parser, testDict["flagList"])))
        
        return (test_data_list, test_stat_list, test_flagInfo_list)
    
                       
    def prepareData(self, selectItemNums: list):        
        # remove test_num that are not selected anymore
        for pre_test_num in self.preTestSelection:
            if (not pre_test_num in selectItemNums) and (pre_test_num in self.selData):
                self.selData.pop(pre_test_num)
                
        for test_num in selectItemNums:
            # skip if test_num has been read
            if test_num in self.selData:
                continue
            
            # read the newly selected test num
            testInfo = self.DatabaseFetcher.getTestInfo_AllDUTs(test_num)
            self.selData[test_num] = self.getDataFromOffsets(testInfo)
            
            
    def getData(self, test_num, selectHeads, selectSites):
        # keys in output: TEST_NAME / TEST_NUM / flagList / LL / HL / Unit / dataList / DUTIndex / Min / Max / Median / Mean / SDev / Cpk
        if not test_num in self.selData: raise KeyError(f"{test_num} is not prepared")
        
        outData = {}
        selMask = self.getMaskFromHeadsSites(selectHeads, selectSites)
        recHeader = self.selData[test_num]["recHeader"]
        outData["recHeader"] = recHeader
        outData["TEST_NAME"] = self.selData[test_num]["TEST_NAME"]
        outData["TEST_NUM"] = test_num
        outData["LL"] = self.selData[test_num]["LL"]
        outData["HL"] = self.selData[test_num]["HL"]
        outData["LSpec"] = self.selData[test_num]["LSpec"]
        outData["HSpec"] = self.selData[test_num]["HSpec"]
        outData["Unit"] = self.selData[test_num]["Unit"]
        outData["Scale"] = self.selData[test_num]["Scale"]
        outData["DUTIndex"] = self.dutArray[selMask]
        outData["flagList"] = self.selData[test_num]["flagList"][selMask]
        
        if recHeader == REC.MPR:
            outData["PIN_NAME"] = self.selData[test_num]["PIN_NAME"]
            outData["dataList"] = ((self.selData[test_num]["dataList"].T)[selMask]).T
            # get statistics of each pin
            outData["Min"] = np.nanmin(outData["dataList"], axis=1)
            outData["Max"] = np.nanmax(outData["dataList"], axis=1)
            outData["Median"] = np.nanmedian(outData["dataList"], axis=1)

            tmpContainer = []
            for pinDataList in outData["dataList"]:
                tmpContainer.append(calc_cpk(outData["LL"], outData["HL"], pinDataList))
            outData["Mean"], outData["SDev"], outData["Cpk"] = np.array(tmpContainer).T
        else:
            outData["dataList"] = self.selData[test_num]["dataList"][selMask]
            outData["Min"] = np.nanmin(outData["dataList"])
            outData["Max"] = np.nanmax(outData["dataList"])
            outData["Median"] = np.nanmedian(outData["dataList"])
            outData["Mean"], outData["SDev"], outData["Cpk"] = calc_cpk(outData["LL"], outData["HL"], outData["dataList"])
        return outData
                
                
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
        selTestNums = self.getSelectedNums()    # test num in trend/histo, wafer index in wafer
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
            [deleteWidget(tabLayout.itemAt(i).widget()) for i in range(tabLayout.count())[::-1]]
            # add new widget
            qfigWidget = QtWidgets.QWidget(self.tab_dict[tabType]["scroll"])
            qfigWidget.setStyleSheet("background-color: transparent")    # prevent plot flicking when updating
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
                qfigWidget.setStyleSheet("background-color: transparent")    # prevent plot flicking when updating
                qfigLayout = QtWidgets.QVBoxLayout()
                qfigWidget.setLayout(qfigLayout)
                tabLayout.addWidget(qfigWidget)
                
            canvasIndexDict = getCanvasDicts(qfigLayout)    # get current indexes
                    
            # delete canvas/toolbars that are not selected
            canvasIndexDict_reverse = {v:k for k, v in canvasIndexDict.items()}     # must delete from large index, invert dict to loop from large index
            for index in sorted(canvasIndexDict_reverse.keys(), reverse=True):
                (mp_head, mp_test_num, mp_site) = canvasIndexDict_reverse[index]
                # if not in Bin tab: no test item selected/ test item is unselected, remove
                # if sites are unselected, remove
                if (tabType != tab.Bin and (selTestNums is None or not mp_test_num in selTestNums)) or (not mp_site in selSites) or (not mp_head in selHeads):
                    # bin don't care about testNum
                    deleteWidget(qfigLayout.itemAt(index).widget())
                    if tabType == tab.Trend:
                        matchString = f"trend_{mp_head}_{mp_test_num}_{mp_site}"
                    elif tabType == tab.Histo:
                        matchString = f"histo_{mp_head}_{mp_test_num}_{mp_site}"
                    elif tabType == tab.Bin:
                        matchString = f"bin_{mp_head}_{mp_test_num}_{mp_site}"
                    else:
                        matchString = f"wafer_{mp_head}_{mp_test_num}_{mp_site}"
                        
                    for key in list(self.cursorDict.keys()):
                        # remove cursors, get a default in case key not found (only happens when data is invalid in some sites)
                        if key.startswith(matchString):
                            self.cursorDict.pop(key, None)
                    
            canvasIndexDict = getCanvasDicts(qfigLayout)    # update after deleting some images
                    
        # generate drawings in trend , histo and bin, but bin doesn't require test items selection
        if tabType == tab.Bin or (tabType in [tab.Trend, tab.Histo, tab.Wafer] and selTestNums != None):
            if tabType == tab.Bin:
                # bin chart is independent of test items
                for site in selSites[::-1]:
                    for head in selHeads[::-1]:
                        if (head, 0, site) in canvasIndexDict:
                            # no need to draw image for a existed testnum and site
                            continue
                        calIndex = calculateCanvasIndex(0, head, site, canvasIndexDict)
                        # draw
                        self.genPlot(head, site, 0, tabType, updateTab=True, insertIndex=calIndex)
            else:
                # trend, histo, wafer
                for test_num in selTestNums[::-1]:
                    for site in selSites[::-1]:
                        for head in selHeads[::-1]:
                            if (head, test_num, site) in canvasIndexDict:
                                # no need to draw image for a existed testnum and site
                                continue
                            calIndex = calculateCanvasIndex(test_num, head, site, canvasIndexDict)
                            # draw
                            self.genPlot(head, site, test_num, tabType, updateTab=True, insertIndex=calIndex)
        # remaining cases are: no test items in tab trend, histo, wafer
        else:
            # when no test item is selected, clear trend, histo & wafer tab content
            if tabType in [tab.Trend, tab.Histo, tab.Wafer]:
                tabLayout = self.tab_dict[tabType]["layout"]
                # clear current content in the layout in reverse order - no use
                [deleteWidget(tabLayout.itemAt(i).widget()) for i in range(tabLayout.count())]
                if tabType == tab.Trend:
                    matchString = "trend"
                elif tabType == tab.Histo:
                    matchString = "histo"
                else:
                    matchString = "wafer"

                for key in list(self.cursorDict.keys()):
                    if key.startswith(matchString):
                        self.cursorDict.pop(key, None)
            
            
    def prepareStatTableContent(self, tabType, **kargs):
        if tabType == tab.Trend or tabType == tab.Histo or tabType == tab.Info:
            head = kargs["head"]
            site = kargs["site"]
            test_num = kargs["test_num"]
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)

            # return data for statistic table
            testDict = self.getData(test_num, [head], [site])
            if testDict:
                if testDict["recHeader"] == REC.MPR:
                    pinNameList = testDict["PIN_NAME"]
                    CpkString = "\n".join(["%s: " % pinName + "%s" % "∞" if cpkPerPin == np.inf else ("N/A" if np.isnan(cpkPerPin) else valueFormat % cpkPerPin)\
                        for pinName, cpkPerPin in zip(pinNameList, testDict["Cpk"])])
                    MeanString = "\n".join(["%s: " % pinName + valueFormat % avgPerPin for pinName, avgPerPin in zip(pinNameList, testDict["Mean"])])
                    MedianString = "\n".join(["%s: " % pinName + valueFormat % medPerPin for pinName, medPerPin in zip(pinNameList, testDict["Median"])])
                    SDevString = "\n".join(["%s: " % pinName + valueFormat % sdevPerPin for pinName, sdevPerPin in zip(pinNameList, testDict["SDev"])])
                    MinString = "\n".join(["%s: " % pinName + valueFormat % minPerPin for pinName, minPerPin in zip(pinNameList, testDict["Min"])])
                    MaxString = "\n".join(["%s: " % pinName + valueFormat % maxPerPin for pinName, maxPerPin in zip(pinNameList, testDict["Max"])])
                
                else:
                    CpkString = "%s" % "∞" if testDict["Cpk"] == np.inf else ("N/A" if np.isnan(testDict["Cpk"]) else valueFormat % testDict["Cpk"])
                    MeanString = valueFormat % testDict["Mean"]
                    MedianString = valueFormat % testDict["Median"]
                    SDevString = valueFormat % testDict["SDev"]
                    MinString = valueFormat % testDict["Min"]
                    MaxString = valueFormat % testDict["Max"]
                
                rowList = ["%d / %s / %s" % (test_num, f"Head {head}", "All Sites" if site == -1 else f"Site{site}"),
                        testDict["TEST_NAME"],
                        testDict["Unit"],
                        "N/A" if np.isnan(testDict["LL"]) else valueFormat % testDict["LL"],
                        "N/A" if np.isnan(testDict["HL"]) else valueFormat % testDict["HL"],
                        "%d" % list(map(isPass, testDict["flagList"])).count(False),
                        CpkString,
                        MeanString,
                        MedianString,
                        SDevString,
                        MinString,
                        MaxString]
            else:
                # some weird files might in this case, in which the number of 
                # test items in different sites are not the same
                rowList = ["N/A"] * 12
            return rowList
        
        elif tabType == tab.Bin:
            bin = kargs["bin"]
            head = kargs["head"]
            site = kargs["site"]
            rowList = []
            
            if bin == "HBIN":
                fullName = self.tr("Hardware Bin")
                bin_dict = self.HBIN_dict
            elif bin == "SBIN":
                fullName = self.tr("Software Bin")
                bin_dict = self.SBIN_dict
            
            binStats = self.DatabaseFetcher.getBinStats(head, site, bin)
            # binNumList = [item[0] for item in binStats]
            total = sum([binStats[bin] for bin in binStats.keys()])
            
            rowList.append("%s / %s / %s" % (f"{fullName}", f"Head{head}", self.tr("All Sites") if site == -1 else f"Site{site}"))
            for bin_num in sorted(binStats.keys()):
                cnt = binStats[bin_num]
                if cnt == 0: continue
                item = ["Bin%d: %.1f%%"%(bin_num, 100*cnt/total), bin_num]
                if bin_num in bin_dict:
                    # add bin name
                    item[0] = self.tr(bin_dict[bin_num]["BIN_NAME"]) + "\n" + item[0]
                rowList.append(item)
                                    
            return rowList
        
        elif tabType == tab.Wafer:
            waferIndex = kargs["waferIndex"]
            head = kargs["head"]
            site = kargs["site"]
            rowList = []
            
            if waferIndex == -1:
                # -1 indicates stacked map, return empty table
                return rowList
            
            # we need sbin dict to retrieve software bin name
            bin_dict = self.SBIN_dict
            
            coordsDict = self.DatabaseFetcher.getWaferCoordsDict(waferIndex, head, site)
            total = sum([len(coordList) for coordList in coordsDict.values()])
            waferID = self.waferInfoDict[waferIndex]["WAFER_ID"]
            
            rowList.append("%s / %s / %s" % (f"{waferID}", f"Head{head}", self.tr("All Sites") if site == -1 else f"Site{site}"))
            for bin_num in sorted(coordsDict.keys()):
                cnt = len(coordsDict[bin_num])
                if cnt == 0: continue
                item = ["Bin%d: %.1f%%"%(bin_num, 100*cnt/total), bin_num]
                if bin_num in bin_dict:
                    # add bin name
                    item[0] = self.tr(bin_dict[bin_num]["BIN_NAME"]) + "\n" + item[0]
                rowList.append(item)
                                    
            return rowList
    
    
    def prepareDUTSummaryForExporter(self, selHeads, selSites, **kargs):
        '''This method is for providing data for report generator'''
        result = []
        
        if "test_num" in kargs and isinstance(kargs["test_num"], int):
            # return test data of the given test_num
            valueFormat = "%%.%d%s"%(self.settingParams.dataPrecision, self.settingParams.dataNotation)
            test_num = kargs["test_num"]
            # get test value of selected DUTs
            testDict = self.getData(test_num, selHeads, selSites)
            test_data_list = self.stringifyTestData(test_num, testDict, valueFormat)
            test_stat_list = [True] * 5 + list(map(isPass, testDict["flagList"]))  # TestName, TestNum, HL, LL, Unit
            result = [test_data_list, test_stat_list]
        
        elif "test_num" not in kargs:
            # return dut info
            currentMask = self.getMaskFromHeadsSites(selHeads, selSites)
            selectedDUTs = self.dutArray[currentMask]
            for dutIndex in selectedDUTs:
                # decode bytes to str
                result.append(list(map(lambda b: b.decode("utf-8"), self.dutSummaryDict[dutIndex])))

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
        selTestNums = self.getSelectedNums()
        verticalHeader = self.ui.dataTable.verticalHeader()
        
        if tabType == tab.Trend or tabType == tab.Histo or tabType == tab.Info:
            # set col headers except Bin Chart
            headerLabels = [self.tr("Test Name"), self.tr("Unit"), self.tr("Low Limit"), self.tr("High Limit"), 
                            self.tr("Fail Num"), "Cpk", self.tr("Average"), self.tr("Median"), 
                            self.tr("St. Dev."), self.tr("Min"), self.tr("Max")]
            indexOfFail = headerLabels.index(self.tr("Fail Num"))    # used for pickup fail number when iterating
            indexOfCpk = headerLabels.index("Cpk")
            self.tmodel.setHorizontalHeaderLabels(headerLabels)     
            self.ui.dataTable.horizontalHeader().setVisible(True)
            verticalHeader.setDefaultSectionSize(25)
 
            if selTestNums:
                # update data
                rowHeader = []
                for test_num in selTestNums:
                    for site in self.getCheckedSites():
                        for head in self.getCheckedHeads():
                            rowList = self.prepareStatTableContent(tabType, head=head, site=site, test_num=test_num)
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
                                    if item != "N/A" and item != "∞":
                                        try:
                                            if float(item) < self.settingParams.cpkThreshold:
                                                qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                                                qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
                                        except ValueError:
                                            # cpk of MPR has the format of pin: value\n...
                                            cpkList = [ele.split(": ")[-1] for ele in item.split("\n")]
                                            for cpkString in cpkList:
                                                if cpkString != "N/A" and cpkString != "∞":
                                                    if float(item) < self.settingParams.cpkThreshold:
                                                        qitem.setData(QtGui.QColor("#FFFFFF"), QtCore.Qt.ForegroundRole)
                                                        qitem.setData(QtGui.QColor("#FE7B00"), QtCore.Qt.BackgroundRole)
                                                        break
                                qitemList.append(qitem)
                            self.tmodel.appendRow(qitemList)
                        
                self.tmodel.setVerticalHeaderLabels(rowHeader)
                self.ui.dataTable.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
                self.tmodel.setColumnCount(len(headerLabels))
            self.resizeCellWidth(self.ui.dataTable)
                
        else:
            # bin or wafer tab
            self.tmodel.setHorizontalHeaderLabels([])
            self.ui.dataTable.horizontalHeader().setVisible(False)
            verticalHeader.setDefaultSectionSize(35)
            rowHeader = []
            tableData = []
            rowColorType = []
            colSize = 0
            
            if tabType == tab.Bin:
                for binType in ["HBIN", "SBIN"]:
                    color_dict = self.settingParams.hbinColor if binType == "HBIN" else self.settingParams.sbinColor
                    for site in self.getCheckedSites():
                        for head in self.getCheckedHeads():
                            rowList = self.prepareStatTableContent(tabType, bin=binType, head=head, site=site)
                            if rowList:
                                # append only if rowList is not empty
                                tableData.append(rowList)
                                rowColorType.append(color_dict)
            else:
                # wafer tab, only cares sbin
                color_dict = self.settingParams.sbinColor
                for waferIndex in selTestNums:
                    for site in self.getCheckedSites():
                        for head in self.getCheckedHeads():
                            rowList = self.prepareStatTableContent(tabType, waferIndex=waferIndex, head=head, site=site)
                            if rowList:
                                # append only if rowList is not empty
                                tableData.append(rowList)
                                rowColorType.append(color_dict)

            for rowList, color_dict in zip(tableData, rowColorType):
                qitemList = []
                rowHeader.append(rowList[0])    # the 1st item as row header
                colSize = len(rowList)-1 if len(rowList)-1>colSize else colSize     # get max length
                for item in rowList[1:]:
                    qitem = QtGui.QStandardItem(item[0])
                    qitem.setTextAlignment(QtCore.Qt.AlignCenter)
                    qitem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    # set color
                    bin_num = item[1]
                    bc = QtGui.QColor(color_dict[bin_num])
                    # https://stackoverflow.com/questions/3942878/how-to-decide-font-color-in-white-or-black-depending-on-background-color
                    fc = QtGui.QColor("#000000") if bc.red()*0.299 + bc.green()*0.587 + bc.blue()*0.114 > 186 else QtGui.QColor("#FFFFFF")
                    qitem.setData(bc, QtCore.Qt.BackgroundRole)
                    qitem.setData(fc, QtCore.Qt.ForegroundRole)
                    qitemList.append(qitem)
                self.tmodel.appendRow(qitemList)
                    
            self.tmodel.setVerticalHeaderLabels(rowHeader)
            self.ui.dataTable.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
            # remove unnecessary blank columns, better than remove columns cuz the latter will cause flicking when updating data
            self.tmodel.setColumnCount(colSize)
            self.resizeCellWidth(self.ui.dataTable, stretchToFit=False)
                
    
    def genPlot(self, head:int, site:int, test_num:int, tabType:tab, **kargs):
        exportImg: bool = ("exportImg" in kargs) and (kargs["exportImg"] == True)
        # create fig & canvas
        figsize = (10, 4)
        fig = plt.Figure(figsize=figsize)
        fig.set_tight_layout(True)
                
        if tabType == tab.Trend:   # Trend
            ax, trendLines = self.genTrendPlot(fig, head, site, test_num)
            
        elif tabType == tab.Histo:   # Histogram
            ax, recGroups = self.genHistoPlot(fig, head, site, test_num)
            
        elif tabType == tab.Bin:   # Bin Chart
            axs, recGroups = self.genBinPlot(fig, head, site)
            
        elif tabType == tab.Wafer:   # Wafermap
            ax = self.genWaferPlot(fig, head, site, test_num)
            
        if exportImg:
            imgData = io.BytesIO()
            fig.savefig(imgData, format="png", dpi=200, bbox_inches="tight")
            return imgData
        else:
            # put figure in a canvas and display in pyqt widgets
            canvas = PlotCanvas(fig)
            # binds to widget
            if "updateTab" in kargs and kargs["updateTab"] and "insertIndex" in kargs:
                qfigWidget = self.tab_dict[tabType]["layout"].itemAt(0).widget()
                qfigLayout = qfigWidget.children()[0]
                
                canvas.bindToUI(qfigWidget)
                canvas.head = head
                canvas.site = site
                canvas.test_num = test_num
                canvas.priority = head + test_num + site
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
                    cursorKey = "trend_%d_%d_%d_%d"%(head, test_num, site, i)
                    self.cursorDict[cursorKey] = MagCursor(line=trendLine,
                                                           mainGUI=self)
                    connectMagCursor(canvas, self.cursorDict[cursorKey], ax)
                    
            elif tabType == tab.Histo and len(recGroups) > 0:
                for i, recGroup in enumerate(recGroups):
                    cursorKey = "histo_%d_%d_%d_%d"%(head, test_num, site, i)
                    self.cursorDict[cursorKey] = MagCursor(histo=recGroup,
                                                           mainGUI=self)
                    connectMagCursor(canvas, self.cursorDict[cursorKey], ax)
                    
            elif tabType == tab.Bin and len(axs) > 0 and len(recGroups) > 0:
                for i, (ax_bin, recGroup) in enumerate(zip(axs, recGroups)):
                    cursorKey = "bin_%d_%d_%d_%d"%(head, test_num, site, i)
                    self.cursorDict[cursorKey] = MagCursor(binchart=recGroup,
                                                           mainGUI=self)
                    connectMagCursor(canvas, self.cursorDict[cursorKey], ax_bin)
            
            elif tabType == tab.Wafer:
                cursorKey = "wafer_%d_%d_%d"%(head, test_num, site)
                self.cursorDict[cursorKey] = MagCursor(wafer=ax.collections,
                                                       mainGUI=self,
                                                       site=site,
                                                       wafer_num=test_num)
                connectMagCursor(canvas, self.cursorDict[cursorKey], ax)
            
            
    def genTrendPlot(self, fig:plt.Figure, head:int, site:int, test_num:int):
        selData = self.getData(test_num, [head], [site])
        ax = fig.add_subplot(111)
        trendLines = []
        ax.set_title("%d %s - %s - %s"%(test_num, selData["TEST_NAME"], "Head%d"%head, self.tr("All Sites") if site == -1 else "Site%d"%site), fontsize=15, fontname=self.imageFont)
        y_raw = selData["dataList"]
        dutListFromSiteHead = self.dutArray[self.getMaskFromHeadsSites([head], [site])]
        dataInvalid = np.all(np.isnan(y_raw))
        testInvalid = np.all(selData["flagList"] < 0)

        if dataInvalid and testInvalid:
            # show a warning text in figure
            ax.text(x=0.5, y=0.5, s=self.tr('No test data for "%s" \nfound in head %d - site %d') % (selData["TEST_NAME"], head, site), color='red', fontsize=18, weight="bold", linespacing=2, ha="center", va="center", transform=ax.transAxes)
        else:
            if selData["recHeader"] == REC.MPR:
                if dataInvalid:
                    # MPR contains only test flag but no data, replace y_raw with test flags
                    y_raw = selData["flagList"]
                    # replace -1 (invalid test flag) with nan
                    y_raw[y_raw < 0] = np.nan
                else:
                    # MPR with multiple data
                    HL = selData["HL"]
                    LL = selData["LL"]
                    HSpec = selData["HSpec"]
                    LSpec = selData["LSpec"]
                    pinList = selData["PIN_NAME"]
                    pinCount = len(pinList)
                    # remove gaps between subplots
                    fig.set_tight_layout(False)
                    fig.subplots_adjust(hspace=0)
                    # resize fig size according to pin#
                    if pinCount > 2:
                        fig.set_size_inches(10, 1.5 * pinCount)
                    # iterate data of each pin
                    for index, pinName, pinData in zip(range(pinCount), pinList, y_raw):
                        # select not nan value
                        x_arr = dutListFromSiteHead[~np.isnan(pinData)]
                        y_arr = pinData[~np.isnan(pinData)]
                        tmpAx = fig.add_subplot(pinCount, 1, index+1, sharex=ax)
                        # trendLine, = 
                        tmpAx.plot(x_arr, y_arr, "-o", markersize=6, markeredgewidth=0.2, markeredgecolor="black", linewidth=0.5, picker=True, color=self.settingParams.siteColor.setdefault(site, rHEX()), zorder = 0, label=pinName)
                        #FIXME disable cursor functino for MPR, performance is really laggy.
                        # trendLines.append(trendLine)
                        # HL/LL lines
                        transXaYd = matplotlib.transforms.blended_transform_factory(tmpAx.transAxes, tmpAx.transData)
                        if self.settingParams.showHL_trend and ~np.isnan(HL): 
                            tmpAx.axhline(y = HL, linewidth=2, color='r', zorder = -10, label="Upper Limit")
                            tmpAx.text(x=0, y=HL, s=" HLimit = %.3f\n"%HL, color='r', fontname="Courier New", fontsize=8, weight="bold", linespacing=2, ha="left", va="center", transform=transXaYd)
                        if self.settingParams.showLL_trend and ~np.isnan(LL): 
                            tmpAx.axhline(y = LL, linewidth=2, color='b', zorder = -10, label="Lower Limit")
                            tmpAx.text(x=0, y=LL, s="\n LLimit = %.3f"%LL, color='b', fontname="Courier New", fontsize=8, weight="bold", linespacing=2, ha="left", va="center", transform=transXaYd)
                        # Spec lines
                        if self.settingParams.showHSpec_trend and ~np.isnan(HSpec): 
                            tmpAx.text(x=1, y=HSpec, s="HiSpec = %.3f \n"%HSpec, color='darkred', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
                            tmpAx.axhline(y = HSpec, linewidth=2, color='darkred', zorder = -10, label="High Spec")
                        if self.settingParams.showLSpec_trend and ~np.isnan(LSpec): 
                            tmpAx.text(x=1, y=LSpec, s="\nLoSpec = %.3f "%LSpec, color='navy', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
                            tmpAx.axhline(y = LSpec, linewidth=2, color='navy', zorder = -10, label="Low Spec")
                        # y limits
                        data_max = np.nanmax([selData["Max"][index], HL, HSpec])
                        data_min = np.nanmin([selData["Min"][index], LL, LSpec])
                        dataDelta = data_max - data_min
                        headroomY = 5 if dataDelta == 0 else dataDelta * 0.2
                        tmpAx.set_ylim((data_min-headroomY, data_max+headroomY))
                        
                        # add pin name at the right side of plots
                        tmpAx.text(x=1, y=0.5, s=pinName, fontsize=10, fontname="Tahoma", ha="left", va="center", rotation=270, transform=tmpAx.transAxes)
                        if index == int(pinCount/2):
                            # middle plot, use ax will cause overlapping
                            tmpAx.set_ylabel("%s%s"%(selData["TEST_NAME"], " (%s)"%selData["Unit"] if selData["Unit"] else ""), fontsize=12, fontname="Tahoma")
                        if index != pinCount-1:
                            tmpAx.xaxis.set_visible(False)                            
                            
                    # x limits
                    if len(x_arr) == 1:
                        ax.set_xlim((x_arr[0]-1, x_arr[0]+1))    # only one point
                    else:
                        headroomX = (x_arr[-1]-x_arr[0]) * 0.1
                        ax.set_xlim(left = x_arr[0] - headroomX, right = x_arr[-1] + headroomX)
                    ax.xaxis.get_major_locator().set_params(integer=True)   # force integer on x axis
                    ax.set_xlabel("%s"%(self.tr("DUT Index")), fontsize=12, fontname=self.imageFont, labelpad=6)
                    ax.set_yticklabels([])
                    ax.yaxis.set_ticks_position('none')
                    return ax, trendLines
            
            # default drawing code for PTR, FTR and "MPR without data"
            # select not nan value
            x_arr = dutListFromSiteHead[~np.isnan(y_raw)]
            y_arr = y_raw[~np.isnan(y_raw)]
            # for dynamic limits
            hasDynamicLow = False
            hasDynamicHigh = False
            dyLLimits = np.array([])
            dyHLimits = np.array([])
            # default limits
            HL = selData["HL"]
            LL = selData["LL"]
            HSpec = selData["HSpec"]
            LSpec = selData["LSpec"]
            med = selData["Median"]
            avg = selData["Mean"]
            # plot            
            trendLine, = ax.plot(x_arr, y_arr, "-o", markersize=6, markeredgewidth=0.2, markeredgecolor="black", linewidth=0.5, picker=True, color=self.settingParams.siteColor.setdefault(site, rHEX()), zorder = 0, label="Data")
            trendLines.append(trendLine)
            # axes label
            ax.ticklabel_format(useOffset=False)    # prevent + sign
            ax.xaxis.get_major_locator().set_params(integer=True)   # force integer on x axis
            ax.set_xlabel("%s"%(self.tr("DUT Index")), fontsize=12, fontname=self.imageFont)
            if selData["recHeader"] == REC.FTR:
                ax.set_ylabel(self.tr("Test Flag"), fontsize=12, fontname=self.imageFont)
            else:
                ax.set_ylabel("%s%s"%(selData["TEST_NAME"], " (%s)"%selData["Unit"] if selData["Unit"] else ""), fontsize=12, fontname="Tahoma")
            # limits
            if len(x_arr) == 1:
                ax.set_xlim((x_arr[0]-1, x_arr[0]+1))    # only one point
            else:
                headroomX = (x_arr[-1]-x_arr[0]) * 0.05
                ax.set_xlim(left = x_arr[0] - headroomX, right = x_arr[-1] + headroomX)
            
            if self.settingParams.showHL_trend or self.settingParams.showMean_trend: 
                # try to get dynamic limits only if one of limits is enabled
                hasDynamicLow, dyLLimits, hasDynamicHigh, dyHLimits = self.DatabaseFetcher.getDynamicLimits(test_num, x_arr, LL, HL, selData["Scale"])
            # when hasDynamic is true, the limit is definitely not np.nan
            limit_max = max(HL, np.max(dyHLimits)) if hasDynamicHigh else HL
            limit_min = min(LL, np.min(dyLLimits)) if hasDynamicLow else LL
            data_max = np.nanmax([selData["Max"], limit_max])
            data_min = np.nanmin([selData["Min"], limit_min])
            dataDelta = data_max - data_min
            
            headroomY = 5 if dataDelta == 0 else dataDelta * 0.15
            ax.set_ylim((data_min-headroomY, data_max+headroomY))

            # blended transformation
            transXaYd = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
            # HL/LL lines
            if self.settingParams.showHL_trend and ~np.isnan(HL): 
                ax.text(x=0, y=HL, s=" HLimit = %.3f\n"%HL, color='r', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left", va="center", transform=transXaYd)
                if hasDynamicHigh: 
                    ax.plot(x_arr, dyHLimits, "-", linewidth=3, color='r', zorder = -10, label="Upper Limit")
                else:
                    ax.axhline(y = HL, linewidth=3, color='r', zorder = -10, label="Upper Limit")
            
            if self.settingParams.showLL_trend and ~np.isnan(LL):
                ax.text(x=0, y=LL, s="\n LLimit = %.3f"%LL, color='b', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left", va="center", transform=transXaYd)
                if hasDynamicLow: 
                    ax.plot(x_arr, dyLLimits, "-", linewidth=3, color='b', zorder = -10, label="Lower Limit")
                else:
                    ax.axhline(y = LL, linewidth=3, color='b', zorder = -10, label="Lower Limit")
            # Spec lines
            if self.settingParams.showHSpec_trend and ~np.isnan(HSpec): 
                ax.text(x=1, y=HSpec, s="HiSpec = %.3f \n"%HSpec, color='darkred', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
                ax.axhline(y = HSpec, linewidth=3, color='darkred', zorder = -10, label="High Spec")
            if self.settingParams.showLSpec_trend and ~np.isnan(LSpec): 
                ax.text(x=1, y=LSpec, s="\nLoSpec = %.3f "%LSpec, color='navy', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
                ax.axhline(y = LSpec, linewidth=3, color='navy', zorder = -10, label="Low Spec")
            # add med and avg text at the right edge of the plot
            m_obj = None
            a_obj = None
            if self.settingParams.showMed_trend:
                med_text = ("$x̃ = %.3f $\n" if med > avg else "\n$x̃ = %.3f $") % med
                m_obj = ax.text(x=0.99, y=med, s=med_text, color='k', fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
                ax.axhline(y = med, linewidth=1, color='k', zorder = 1, label="Median")
            if self.settingParams.showMean_trend:
                avg_text = ("\n$x̅ = %.3f $" if med > avg else "$x̅ = %.3f $\n") % avg
                a_obj = ax.text(x=0.99, y=avg, s=avg_text, color='orange', fontsize=10, weight="bold", linespacing=2, ha="right", va="center", transform=transXaYd)
                ax.axhline(y = avg, linewidth=1, color='orange', zorder = 2, label="Mean")
                
            if self.settingParams.showMed_trend or self.settingParams.showMean_trend:
                if len(x_arr) != 1:
                    # get the length of median text in axes coords
                    text_object = m_obj if m_obj else a_obj     # get the non-None text object
                    if self.textRender is None:
                        self.textRender = RendererAgg(*fig.get_size_inches(), fig.dpi)
                    bb_pixel = text_object.get_window_extent(renderer=self.textRender)
                    text_leftEdge_Axes = ax.transAxes.inverted().transform(bb_pixel)[0][0]
                    # extend x limit to avoid data point overlapped with the text
                    rightLimit = (x_arr[-1] + 2) * 1 / text_leftEdge_Axes
                    ax.set_xlim(right = rightLimit)
                    
        # for cursor binding
        return ax, trendLines
    
    
    def genHistoPlot(self, fig:plt.Figure, head:int, site:int, test_num:int):
        selData = self.getData(test_num, [head], [site])
        ax = fig.add_subplot(111)
        recGroups = []
        ax.set_title("%d %s - %s - %s"%(test_num, selData["TEST_NAME"], "Head%d"%head, self.tr("All Sites") if site == -1 else "Site%d"%site), fontsize=15, fontname=self.imageFont)
        y_raw = selData["dataList"]
        dutListFromSiteHead = self.dutArray[self.getMaskFromHeadsSites([head], [site])]
        dataInvalid = np.all(np.isnan(selData["dataList"]))
        testInvalid = np.all(selData["flagList"] < 0)

        if dataInvalid and testInvalid:
            # show a warning text in figure
            ax.text(x=0.5, y=0.5, s=self.tr('No test data for "%s" \nfound in head %d - site %d') % (selData["TEST_NAME"], head, site), color='red', fontsize=18, weight="bold", linespacing=2, ha="center", va="center", transform=ax.transAxes)
        else:
            if selData["recHeader"] == REC.MPR:
                if dataInvalid:
                    # MPR contains only test flag but no data, replace y_raw with test flags
                    y_raw = selData["flagList"]
                    # replace -1 (invalid test flag) with nan
                    y_raw[y_raw < 0] = np.nan
                else:
                    # MPR with multiple data
                    HL = selData["HL"]
                    LL = selData["LL"]
                    HSpec = selData["HSpec"]
                    LSpec = selData["LSpec"]
                    bin_num = self.settingParams.binCount
                    pinList = selData["PIN_NAME"]
                    pinCount = len(pinList)
                    # remove gaps between subplots
                    fig.set_tight_layout(False)
                    fig.subplots_adjust(hspace=0)
                    # resize fig size according to pin#
                    if pinCount > 2:
                        fig.set_size_inches(10, 1.5 * pinCount)
                    # iterate data of each pin
                    for index, pinName, pinData in zip(range(pinCount), pinList, y_raw):
                        # med = selData["Median"][index]
                        avg = selData["Mean"][index]
                        sd = selData["SDev"][index]
                        # select not nan value
                        dataList = pinData[~np.isnan(pinData)]
                        dutListNoNAN = dutListFromSiteHead[~np.isnan(pinData)]
                        tmpAx = fig.add_subplot(pinCount, 1, index+1, sharex=ax)
                        #TODO filter data beyond 9σ
                        dataFilter = np.logical_and(dataList>=(avg-9*sd), dataList<=(avg+9*sd))
                        filteredDataList = dataList[dataFilter]
                        filteredDutList = dutListNoNAN[dataFilter]
                        
                        hist, bin_edges = np.histogram(filteredDataList, bins = bin_num)
                        bin_width = bin_edges[1]-bin_edges[0]
                        # get histo bin number of each dut
                        bin_ind = np.digitize(filteredDataList, bin_edges, right=False)
                        bin_dut_dict = {}
                        for ind, dut in zip(bin_ind, filteredDutList):
                            if ind in bin_dut_dict:
                                bin_dut_dict[ind].append(dut)
                            else:
                                bin_dut_dict[ind] = [dut]
                        # use bar to draw histogram, only for its "align" option 
                        recGroup = tmpAx.bar(bin_edges[:len(hist)], hist, width=bin_width, align='edge', color=self.settingParams.siteColor.setdefault(site, rHEX()), edgecolor="black", zorder = 0, label=pinName, picker=True)
                        # save to histo group for interaction
                        setattr(recGroup, "bin_dut_dict", bin_dut_dict)
                        # recGroups.append(recGroup)
                        # add pin name at the right side of plots
                        tmpAx.text(x=1, y=0.5, s=pinName, fontsize=10, fontname="Tahoma", ha="left", va="center", rotation=270, transform=tmpAx.transAxes)
                        # draw boxplot
                        if self.settingParams.showBoxp_histo:
                            ax_box = tmpAx.twinx()
                            ax_box.axis('off')  # hide axis and tick for boxplot
                            ax_box.boxplot(dataList, showfliers=False, vert=False, notch=True, widths=0.5, patch_artist=True,
                                        boxprops=dict(color='b', facecolor=(1, 1, 1, 0)),
                                        capprops=dict(color='b'),
                                        whiskerprops=dict(color='b'))
                        # draw LL HL
                        if self.settingParams.showHL_histo and ~np.isnan(HL): 
                            tmpAx.axvline(x = HL, linewidth=3, color='r', zorder = 10, label="Upper Limit")
                        if self.settingParams.showLL_histo and ~np.isnan(LL): 
                            tmpAx.axvline(x = LL, linewidth=3, color='b', zorder = 10, label="Lower Limit")
                        
                        if self.settingParams.showHSpec_histo and ~np.isnan(HSpec): 
                            tmpAx.axvline(x = HSpec, linewidth=3, color='darkred', zorder = -10, label="Hi Spec")
                        if self.settingParams.showLSpec_histo and ~np.isnan(LSpec): 
                            tmpAx.axvline(x = LSpec, linewidth=3, color='navy', zorder = -10, label="Lo Spec")

                        # draw fitting curve only when standard deviation is not 0
                        if sd != 0:
                            if self.settingParams.showGaus_histo:
                                # gauss fitting
                                g_x = np.linspace(avg - sd * 10, avg + sd * 10, 1000)
                                g_y = max(hist) * np.exp( -0.5 * (g_x - avg)**2 / sd**2 )
                                tmpAx.plot(g_x, g_y, "r--", label="Normalized Gauss Curve")
                        tmpAx.set_ylim(top=max(hist)*1.2)
                        tmpAx.yaxis.get_major_locator().set_params(integer=True)   # force integer on x axis
                        
                        if index == int(pinCount/2):
                            # middle plot, use ax will cause overlapping
                            tmpAx.set_ylabel("%s"%(self.tr("DUT Counts")), fontsize=12, fontname=self.imageFont)
                        if index != pinCount-1:
                            tmpAx.xaxis.set_visible(False)
                    
                    # set x limit on common axis (ax)
                    if sd != 0:
                        if bin_edges[0] > avg - sd * 10:
                            ax.set_xlim(left=avg - sd * 10)
                        if bin_edges[-1] < avg + sd * 10:
                            ax.set_xlim(right=avg + sd * 10)
                    else:
                        if avg == 0:
                            ax.set_xlim(-1, 1)
                        else:
                            ax.set_xlim(avg*0.5, avg*1.5)
                        
                    ax.set_xlabel("%s%s"%(selData["TEST_NAME"], " (%s)"%selData["Unit"] if selData["Unit"] else ""), fontsize=12, fontname="Tahoma", labelpad=6)
                    ax.set_yticklabels([])
                    ax.yaxis.set_ticks_position('none')
                    return ax, recGroups
            
            dataList = y_raw[~np.isnan(y_raw)]
            dutListNoNAN = dutListFromSiteHead[~np.isnan(y_raw)]
            HL = selData["HL"]
            LL = selData["LL"]
            HSpec = selData["HSpec"]
            LSpec = selData["LSpec"]
            med = selData["Median"]
            avg = selData["Mean"]
            sd = selData["SDev"]
            bin_num = self.settingParams.binCount
            # note: len(bin_edges) = len(hist) + 1
            # we use a filter to remove the data that's beyond 9 sigma
            # otherwise we cannot to see the detailed distribution of the main data set
            #TODO filter data beyond 9σ
            dataFilter = np.logical_and(dataList>=(avg-9*sd), dataList<=(avg+9*sd))
            filteredDataList = dataList[dataFilter]
            filteredDutList = dutListNoNAN[dataFilter]
            
            hist, bin_edges = np.histogram(filteredDataList, bins = bin_num)
            bin_width = bin_edges[1]-bin_edges[0]
            # get histo bin index (start from 1) of each dut
            bin_ind = np.digitize(filteredDataList, bin_edges, right=False)
            bin_dut_dict = {}
            for ind, dut in zip(bin_ind, filteredDutList):
                if ind in bin_dut_dict:
                    bin_dut_dict[ind].append(dut)
                else:
                    bin_dut_dict[ind] = [dut]
            # use bar to draw histogram, only for its "align" option 
            recGroup = ax.bar(bin_edges[:len(hist)], hist, width=bin_width, align='edge', color=self.settingParams.siteColor.setdefault(site, rHEX()), edgecolor="black", zorder = 100, label="Histo Chart", picker=True)
            # save to histo group for interaction
            setattr(recGroup, "bin_dut_dict", bin_dut_dict)
            recGroups.append(recGroup)
            # draw boxplot
            if self.settingParams.showBoxp_histo:
                ax.boxplot(dataList, showfliers=False, vert=False, notch=True, widths=0.2*max(hist), patch_artist=True, zorder=200, positions=[max(hist)/2], manage_ticks=False,
                            boxprops=dict(color='b', facecolor=(1, 1, 1, 0)),
                            capprops=dict(color='b'),
                            whiskerprops=dict(color='b'))
            
            if self.settingParams.showHL_histo and ~np.isnan(HL): 
                ax.axvline(x = HL, linewidth=3, color='r', zorder = -10, label="Upper Limit")
            if self.settingParams.showLL_histo and ~np.isnan(LL): 
                ax.axvline(x = LL, linewidth=3, color='b', zorder = -10, label="Lower Limit")
            
            if self.settingParams.showHSpec_histo and ~np.isnan(HSpec): 
                ax.axvline(x = HSpec, linewidth=3, color='darkred', zorder = -10, label="Hi Spec")
            if self.settingParams.showLSpec_histo and ~np.isnan(LSpec): 
                ax.axvline(x = LSpec, linewidth=3, color='navy', zorder = -10, label="Lo Spec")

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
                
            # blended transformation
            transXdYa = matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes)
            # vertical lines for n * σ
            sigmaList = [int(i) for i in self.settingParams.showSigma.split(",")]
            for n in sigmaList:
                position_pos = avg + sd * n
                position_neg = avg - sd * n
                ax.axvline(x = position_pos, ymax = 0.95, linewidth=1, ls='-.', color='gray', zorder = 2, label="%dσ"%n)
                ax.axvline(x = position_neg, ymax = 0.95, linewidth=1, ls='-.', color='gray', zorder = 2, label="-%dσ"%n)
                ax.text(x = position_pos, y = 0.99, s="%dσ"%n, c="gray", ha="center", va="top", fontname="Courier New", fontsize=10, transform=transXdYa)
                ax.text(x = position_neg, y = 0.99, s="-%dσ"%n, c="gray", ha="center", va="top", fontname="Courier New", fontsize=10, transform=transXdYa)
            # med avg text labels / lines
            med_text = ("\n $x̃ = %.3f $") % med
            avg_text = ("\n $x̅ = %.3f $") % avg
            if self.settingParams.showMed_histo:
                ax.text(x=med, y=1, s=med_text, color='k', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="left" if med>avg else "right", va="center", transform=transXdYa)
                ax.axvline(x = med, linewidth=1, color='black', zorder = 1, label="Median")
            if self.settingParams.showMean_histo:
                ax.text(x=avg, y=1, s=avg_text, color='orange', fontname="Courier New", fontsize=10, weight="bold", linespacing=2, ha="right" if med>avg else "left", va="center", transform=transXdYa)
                ax.axvline(x = avg, linewidth=1, color='orange', zorder = 2, label="Mean")
            # ax.ticklabel_format(useOffset=False)    # prevent + sign
            if selData["recHeader"] == REC.FTR:
                ax.set_xlabel(self.tr("Test Flag"), fontsize=12, fontname=self.imageFont)
            else:
                ax.set_xlabel("%s%s"%(selData["TEST_NAME"], " (%s)"%selData["Unit"] if selData["Unit"] else ""), fontsize=12, fontname="Tahoma")
            ax.set_ylabel("%s"%(self.tr("DUT Counts")), fontsize=12, fontname=self.imageFont)
            
        return ax, recGroups
    
    
    def genBinPlot(self, fig:plt.Figure, head:int, site:int):
        fig.suptitle("%s - %s - %s"%(self.tr("Bin Summary"), "Head%d"%head, self.tr("All Sites") if site == -1 else "Site%d"%site), fontsize=15, fontname=self.imageFont)
        ax_l = fig.add_subplot(121)
        ax_r = fig.add_subplot(122)
        bin_width = 0.8
        Tsize = lambda barNum: 10 if barNum <= 6 else round(5 + 5 * 2 ** (0.4*(6-barNum)))  # adjust fontsize based on bar count
        # HBIN plot
        binStats = self.DatabaseFetcher.getBinStats(head, site, "HBIN")
        HList = [BIN for BIN in sorted(binStats.keys())]
        HCnt = [binStats[BIN] for BIN in HList]
        HLable = []
        HColor = []
        for ind, i in enumerate(HList):
            HLable.append(self.tr(self.HBIN_dict[i]["BIN_NAME"]))
            HColor.append(self.settingParams.hbinColor[i])
            ax_l.text(x=ind + bin_width/2, y=HCnt[ind], s="Bin%d\n%.1f%%"%(i, 100*HCnt[ind]/sum(HCnt)), ha="center", va="bottom", fontsize=Tsize(len(HCnt)))
            
        recGroup_l = ax_l.bar(np.arange(len(HCnt)), HCnt, align='edge', width=bin_width, color=HColor, edgecolor="black", zorder = 0, label="HardwareBin Summary", picker=True)
        setattr(recGroup_l, "head", head)
        setattr(recGroup_l, "site", site)
        setattr(recGroup_l, "binType", "HBIN")
        setattr(recGroup_l, "binList", HList)
        ax_l.set_xticks(np.arange(len(HCnt)) + bin_width/2)
        ax_l.set_xticklabels(labels=HLable, rotation=30, ha='right', fontsize=1+Tsize(len(HCnt)), fontname=self.imageFont)    # Warning: This method should only be used after fixing the tick positions using Axes.set_xticks. Otherwise, the labels may end up in unexpected positions.
        ax_l.set_xlim(-.1, max(3, len(HCnt))-.9+bin_width)
        ax_l.set_ylim(top=max(HCnt)*1.2)
        ax_l.set_xlabel(self.tr("Hardware Bin"), fontsize=12, fontname=self.imageFont)
        ax_l.set_ylabel(self.tr("Hardware Bin Counts"), fontsize=12, fontname=self.imageFont)

        # SBIN plot
        binStats = self.DatabaseFetcher.getBinStats(head, site, "SBIN")
        SList = [BIN for BIN in sorted(binStats.keys())]
        SCnt = [binStats[BIN] for BIN in SList]
        SLable = []
        SColor = []
        for ind, i in enumerate(SList):
            SLable.append(self.tr(self.SBIN_dict[i]["BIN_NAME"]))
            SColor.append(self.settingParams.sbinColor[i])
            ax_r.text(x=ind + bin_width/2, y=SCnt[ind], s="Bin%d\n%.1f%%"%(i, 100*SCnt[ind]/sum(SCnt)), ha="center", va="bottom", fontsize=Tsize(len(SCnt)))
            
        recGroup_r = ax_r.bar(np.arange(len(SCnt)), SCnt, align='edge', width=bin_width, color=SColor, edgecolor="black", zorder = 0, label="SoftwareBin Summary", picker=True)
        setattr(recGroup_r, "head", head)
        setattr(recGroup_r, "site", site)
        setattr(recGroup_r, "binType", "SBIN")
        setattr(recGroup_r, "binList", SList)
        ax_r.set_xticks(np.arange(len(SCnt)) + bin_width/2)
        ax_r.set_xticklabels(labels=SLable, rotation=30, ha='right', fontsize=1+Tsize(len(SCnt)), fontname=self.imageFont)
        ax_r.set_xlim(-.1, max(3, len(SCnt))-.9+bin_width)
        ax_r.set_ylim(top=max(SCnt)*1.2)
        ax_r.set_xlabel(self.tr("Software Bin"), fontsize=12, fontname=self.imageFont)
        ax_r.set_ylabel(self.tr("Software Bin Counts"), fontsize=12, fontname=self.imageFont)
        
        return [ax_l, ax_r], [recGroup_l, recGroup_r]
    
    
    def genWaferPlot(self, fig:plt.Figure, head:int, site:int, wafer_num:int):
        fig.set_size_inches(7.5, 8)
        fig.set_tight_layout(False)
        ax = fig.add_subplot(111, aspect=1)
        # set limits
        waferBounds = self.DatabaseFetcher.getWaferBounds()
        xmin = waferBounds["xmin"]
        ymin = waferBounds["ymin"]
        xmax = waferBounds["xmax"]
        ymax = waferBounds["ymax"]            
        ax.set_xlim(xmin-1, xmax+1)
        ax.set_ylim(ymin-1, ymax+1)
        # scaling xy coords to be a square
        ax.set_aspect(1.0/ax.get_data_ratio(), adjustable='box')            
        # dynamic label size
        Tsize = lambda barNum: 12 if barNum <= 15 else round(7 + 5 * 2 ** (0.4*(15-barNum)))  # adjust fontsize based on bar count
        labelsize = Tsize(max(xmax-xmin, ymax-ymin))
                    
        if wafer_num == -1:
            # -1 indicates stacked wafer map
            ax.set_title(self.tr("Stacked Wafer Map - %s - %s") % ("Head%d" % head, self.tr("All DUTs") if site == -1 else self.tr("DUT in Site%d") % site), fontsize=15, fontname=self.imageFont)
            failDieDistribution = self.DatabaseFetcher.getStackedWaferData(head, site)
            x_mesh = np.arange(xmin-0.5, xmax+1, 1)     # xmin-0.5, xmin+0.5, ..., xmax+0.5
            y_mesh = np.arange(ymin-0.5, ymax+1, 1)
            # initialize a full -1 2darray
            failCount_meash = np.full((len(x_mesh)-1, len(y_mesh)-1), -1)
            # fill the count into 2darray
            for (xcoord, ycoord), count in failDieDistribution.items():
                failCount_meash[xcoord-xmin, ycoord-ymin] = count
            # x is row and y is col, whereas in xycoords, x should be col and y should be row
            failCount_meash = failCount_meash.transpose()
            # get a colormap segment
            cmap_seg = matplotlib.colors.LinearSegmentedColormap.from_list("seg", plt.get_cmap("nipy_spectral")(np.linspace(0.55, 0.9, 128)))
            # draw color mesh, replace all -1 to NaN to hide rec with no value
            pcmesh = ax.pcolormesh(x_mesh, y_mesh, np.where(failCount_meash == -1, np.nan, failCount_meash), cmap=cmap_seg, picker=100)     # set picker large enough for QuadMask to fire pick event
            setattr(pcmesh, "wafer_num", wafer_num)
            # create a new axis for colorbar
            ax_colorbar = fig.add_axes([ax.get_position().x0, ax.get_position().y0-0.04, ax.get_position().width, 0.02])
            cbar = fig.colorbar(pcmesh, cax=ax_colorbar, orientation="horizontal")
            cbar.ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
            cbar.set_label(self.tr("Total failed dies"), fontname=self.imageFont)
            # ax_colorbar = fig.add_axes([ax.get_position().x1+0.03, ax.get_position().y0, 0.02, ax.get_position().height])
            # cbar = fig.colorbar(pcmesh, cax=ax_colorbar)
            # cbar.ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
            # cbar.set_label("Total failed dies", rotation=270, va="bottom")
            
        else:
            waferDict = self.waferInfoDict[wafer_num]
            ax.set_title(self.tr("Wafer ID: %s - %s - %s") % (waferDict["WAFER_ID"], "Head%d"%head, self.tr("All DUTs") if site == -1 else self.tr("DUT in Site%d") % site), fontsize=15, fontname=self.imageFont)
            # group coords by soft bin
            coordsDict = self.DatabaseFetcher.getWaferCoordsDict(wafer_num, head, site)
            dutCnt = sum([len(coordList) for coordList in coordsDict.values()])
            legendHandles = []
            # draw recs for each SBIN
            for sbin in sorted(coordsDict.keys()):
                sbinName = self.SBIN_dict[sbin]["BIN_NAME"]
                sbinCnt = len(coordsDict[sbin])
                percent = 100 * sbinCnt / dutCnt
                label = "SBIN %d - %s\n[%d - %.1f%%]"%(sbin, sbinName, sbinCnt, percent)
                rects = []
                # skip dut with invalid coords
                for (x, y) in coordsDict[sbin]:
                    rects.append(matplotlib.patches.Rectangle((x-0.5, y-0.5),1,1))
                pc = PatchCollection(patches=rects, match_original=False, facecolors=self.settingParams.sbinColor[sbin], label=label, zorder=-100, picker=True)
                # for interactive plot
                setattr(pc, "SBIN", sbin)
                setattr(pc, "BIN_NAME", self.tr(sbinName))
                setattr(pc, "wafer_num", wafer_num)
                ax.add_collection(pc)
                proxyArtist = matplotlib.patches.Patch(color=self.settingParams.sbinColor[sbin], label=label)
                legendHandles.append(proxyArtist)
            # legend
            ax.legend(handles=legendHandles, loc="upper left", bbox_to_anchor=(0., -0.02, 1, -0.02), ncol=4, borderaxespad=0, mode="expand", fontsize=labelsize)
        
        # set ticks & draw coord lines
        ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(5))            
        ax.tick_params(axis='both', which='both', labeltop=True, labelright=True, length=0, labelsize=labelsize)
        # Turn spines off and create white grid.
        for edge, spine in ax.spines.items():
            spine.set_visible(False)
        ax.set_xticks(np.arange(xmin, xmax+2, 1)-0.5, minor=True)
        ax.set_yticks(np.arange(ymin, ymax+2, 1)-0.5, minor=True)
        ax.grid(which="minor", color="gray", linestyle='-', linewidth=1, zorder=0)
        # switch x, y positive direction if WCR specified the orientation.
        if self.fileInfoDict.get("POS_X", "") == "L":   # x towards left
            ax.invert_xaxis()
        if self.fileInfoDict.get("POS_Y", "") == "D":   # y towards down
            ax.invert_yaxis()
            
        return ax
    
    
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
            [[deleteWidget(self.tab_dict[key]["layout"].itemAt(index).widget()) for index in range(self.tab_dict[key]["layout"].count())] if key != currentTab else None for key in [tab.Trend, tab.Histo, tab.Bin]]
            
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
        [[deleteWidget(self.tab_dict[key]["layout"].itemAt(index).widget()) for index in range(self.tab_dict[key]["layout"].count())] for key in [tab.Trend, tab.Histo, tab.Bin, tab.Wafer]]
        # clear magic cursor as well, it contains copies of figures
        self.cursorDict = {}
            
        gc.collect()
    
    
    def callFileLoader(self, stdHandle):
        if stdHandle:
            self.loader.loadFile(stdHandle.fpath)

        
    @Slot(bool)
    def updateData(self, parseStatus):
        if parseStatus:
            # clear old images & tables
            self.clearAllContents()
            
            # remove old std file handler
            self.stdHandleList = [self.std_handle]
            databasePath = os.path.join(sys.rootFolder, "logs", "tmp.db")
            self.DatabaseFetcher.connectDB(databasePath)
            self.dbConnected = True
            
            # update Bin dict
            self.HBIN_dict = self.DatabaseFetcher.getBinInfo(bin="HBIN")
            self.SBIN_dict = self.DatabaseFetcher.getBinInfo(bin="SBIN")
            
            # update fail cnt dict
            self.failCntDict = self.DatabaseFetcher.getTestFailCnt()
            
            # disable/enable wafer tab
            self.containsWafer = self.DatabaseFetcher.containsWafer()
            self.ui.tabControl.setTabEnabled(4, self.containsWafer)
            if self.containsWafer:
                #read waferDict
                self.waferInfoDict = self.DatabaseFetcher.getWaferInfo()
    
            # update listView
            self.completeTestList = self.DatabaseFetcher.getTestItemsList()
            self.updateModelContent(self.sim_list, self.completeTestList)
            self.completeWaferList = self.DatabaseFetcher.getWaferList()
            self.updateModelContent(self.sim_list_wafer, self.completeWaferList)
            
            # remove site/head checkbox for invalid sites/heads
            current_exist_site = list(self.site_cb_dict.keys())     # avoid RuntimeError: dictionary changed size during iteration
            current_exist_head = list(self.head_cb_dict.keys())
            sites_in_file = self.DatabaseFetcher.getSiteList()
            heads_in_file = self.DatabaseFetcher.getHeadList()
            
            for site in current_exist_site:
                if site not in sites_in_file:
                    self.site_cb_dict.pop(site)
                    row = 1 + site//4
                    col = site % 4
                    cb_layout = self.ui.gridLayout_site_select.itemAtPosition(row, col)
                    if cb_layout is not None:
                        cb_layout.widget().deleteLater()
                        self.ui.gridLayout_site_select.removeItem(cb_layout)
                        
            for headnum in current_exist_head:
                if headnum not in heads_in_file:
                    self.head_cb_dict.pop(headnum)
                    row = headnum//3
                    col = headnum % 3
                    cb_layout_h = self.ui.gridLayout_head_select.itemAtPosition(row, col)
                    if cb_layout_h is not None:
                        cb_layout_h.widget().deleteLater()
                        self.ui.gridLayout_head_select.removeItem(cb_layout_h)                    
                                 
            # add & enable checkboxes for each sites and heads
            self.availableSites = list(sites_in_file)
            self.availableHeads = list(heads_in_file)
            
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
            self.dutArray, self.dutSiteInfo = self.DatabaseFetcher.getDUT_SiteInfo()
            # get complete dut summary dict from stdf
            self.dutSummaryDict = self.DatabaseFetcher.getDUT_Summary()
            
            self.settingUI.removeColorBtns()               # remove existing color btns
            self.settingUI.initColorBtns()
            self.exporter.removeSiteCBs()
            self.exporter.refreshUI()
            self.init_SettingParams()
            self.init_Head_SiteCheckbox()
            self.updateFileHeader()
            setByteSwap(self.needByteSwap)   # specify the parse endian
            self.updateDutSummaryTable()
            self.updateStatTableContent()
            self.updateTabContent(forceUpdate=True)
            
        else:
            # aborted, restore to original stdf file handler
            self.std_handle = self.stdHandleList[0]
            self.stdHandleList = [self.std_handle]

    
    @Slot(str, bool, bool, bool)
    def updateStatus(self, new_msg, info=False, warning=False, error=False):
        self.statusBar().showMessage(new_msg)
        if info: 
            QtWidgets.QMessageBox.information(None, self.tr("Info"), new_msg)
        elif warning: 
            QtWidgets.QMessageBox.warning(None, self.tr("Warning"), new_msg)
            logger.warning(new_msg)
        elif error:
            QtWidgets.QMessageBox.critical(None, self.tr("Error"), new_msg)
            sys.exit()
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
                    url = event.mimeData().urls()[0]   # get first url
                    event.accept()  # doesnt appear to be needed
                    self.openNewFile(url.toLocalFile())
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
    # reverse to put courier at the rear
    for fn in sorted(os.listdir("fonts"), key=lambda x:x.lower(), reverse=True):
        if not fn.endswith(".ttf"): continue
        fontPath = "fonts/" + fn
        QtGui.QFontDatabase.addApplicationFont(fontPath)
        fm.fontManager.addfont(fontPath)
        font_names.append(fm.FontProperties(fname=fontPath).get_name())
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = font_names
    
    window = MyWindow()
    window.show()
    window.callFileLoader(window.std_handle)
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    run()