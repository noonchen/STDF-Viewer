#
# uic_stdExporter.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 11th 2020
# -----
# Last Modified: Sat Dec 03 2022
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



import re
import os, io, logging
from enum import IntEnum
from itertools import product
from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet

from .ui.stdfViewer_exportUI import Ui_exportUI
from .ui.stdfViewer_loadingUI import Ui_loadingUI
from .SharedSrc import *

# pyqt5
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractItemView, QFileDialog, QMessageBox
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QTranslator

# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtWidgets import QAbstractItemView, QFileDialog
# from PySide2.QtCore import Signal, Slot, QTranslator
# from .ui.stdfViewer_exportUI_side2 import Ui_exportUI
# from .ui.stdfViewer_loadingUI_side2 import Ui_loadingUI
# pyside6
# from PySide6 import QtCore, QtWidgets
# from PySide6.QtWidgets import QAbstractItemView, QFileDialog
# from PySide6.QtCore import Signal, Slot, QTranslator
# from .ui.stdfViewer_exportUI_side6 import Ui_exportUI
# from .ui.stdfViewer_loadingUI_side6 import Ui_loadingUI


logger = logging.getLogger("STDF Viewer")

    
class ReportSelection(IntEnum):
    FileInfo = 0
    DUT = 1
    Trend = 2
    Histo = 3
    Bin = 4
    Wafer = 5
    Stat = 6
    GDR_DTR = 7
    PPQQ = 8
    Correlation = 9


class sv:
    '''static variables'''
    # file info
    finfoRow     = 0
    finfoCol     = 0
    # GDR/DTR
    drRow        = 0
    drCol        = 0
    
    trendRow     = 0
    histoRow     = 0
    binRow       = 0
    statRow      = 0
    # dut summary
    dutRow       = 0
    dutCol       = 0
    
    waferRow     = 0
    
    @staticmethod
    def init_variables():
        # file info
        sv.finfoRow  = 0
        sv.finfoCol  = 0
        # GDR/DTR
        sv.drRow     = 0
        sv.drCol     = 0
        
        sv.trendRow  = 0
        sv.histoRow  = 0
        sv.binRow    = 0
        sv.statRow   = 0
        # dut summary
        sv.dutRow    = 0
        sv.dutCol    = 0
        
        sv.waferRow  = 0


def list_operation(main, method, other):
    main = [] if main is None else main
    other = [] if other is None else other
    
    if method == "+":
        tmp = set(main) | set(other)
        return sorted(tmp, key=lambda item: int(item.split("\t")[0]))
    
    elif method == "-":
        tmp = set(main) - set(other)
        return sorted(tmp, key=lambda item: int(item.split("\t")[0]))


def ceil(n):
    return int(-1 * n // 1 * -1)


def write_row_col(sheet:Worksheet, row:int, col:int, dataL:list, cellFormat, writeRow:bool):
    # if cellFormat is a list, assign cellFormat to the corresponding data, 
    # else assign the same cellFormat to all data
    broadcast = (not isinstance(cellFormat, list))
    if not broadcast:
        if len(dataL) != len(cellFormat):
            raise ValueError("The length of data and formats should be the same")
            
    for i in range(len(dataL)):
        if writeRow:
            # row not changed, col increases with i
            tmpRow = row
            tmpCol = col+i
        else:
            # row increases with i, col not changed
            tmpRow = row+i
            tmpCol = col
            
        # write as number in default, otherwise as string
        try:
            sheet.write_number(tmpRow, tmpCol, float(dataL[i]), cellFormat if broadcast else cellFormat[i])
        except (TypeError, ValueError):
            sheet.write_string(tmpRow, tmpCol, dataL[i], cellFormat if broadcast else cellFormat[i])


def getMaxLength(lenList: list[int], dataList: list[str]) -> list[int]:
    return [max(w, len(d)) for w, d in zip(lenList, dataList)]


class dataChannel:
    # for sharing data between threads
    imageChannel = None
    dataListChannel = None



class signals(QtCore.QObject):
    # get message
    msgSignal = Signal(str)
    # get progress
    progressBarSignal = Signal(int)
    # get close signal
    closeSignal = Signal(bool)
    # signals from report generation thread for requesting data
    retrieveImageSignal = Signal(int, int, tuple, int)     # head, site, testTuple, chartType
    retrieveDataListSignal = Signal(int, dict)      # chartType, {site, testTuple} / {site, bin}
    retrieveTableDataSignal = Signal(int)           # FileInfo table
    retrieveDutSummarySignal = Signal(list, list, dict)   # selected heads, selected sites, {testTuple}, get dut info or dut test data
    
    
    
class reportGenerator(QtCore.QObject):
    def __init__(self, signals:signals, mutex:QtCore.QMutex, conditionWait:QtCore.QWaitCondition, reportInfo:tuple, channel:dataChannel):
        super().__init__()
        self.forceQuit = False
        self.mutex = mutex
        self.condWait = conditionWait
        self.loopCount = 0
        (self.selectedContents, 
         self.testTuples, 
         self.selectedFiles, 
         self.selectedHeads, 
         self.selectedSites, 
         self.reportPath, 
         self.waferTuples, 
         self.totalLoopCnt) = reportInfo
        # for sharing data from gui thread
        self.channel = channel
        # signals for updating progress bar dialog
        self.msgSignal = signals.msgSignal
        self.progressBarSignal = signals.progressBarSignal
        self.closeSignal = signals.closeSignal
        # signals for data communication
        self.retrieveImageSignal = signals.retrieveImageSignal
        self.retrieveDataListSignal = signals.retrieveDataListSignal
        self.retrieveTableDataSignal = signals.retrieveTableDataSignal
        self.retrieveDutSummarySignal = signals.retrieveDutSummarySignal
        
    
    def waitForImage(self, head, site, testTuple, chartType) -> io.BytesIO:
        # pause thread until the data is received from gui thread
        self.mutex.lock()
        self.retrieveImageSignal.emit(head, site, testTuple, chartType)
        self.condWait.wait(self.mutex)      # self.mutex is unlocked here
        self.mutex.unlock()
        # by the time the thread is waked, the data is already published in imageChannel in mainthread
        return self.channel.imageChannel
            
            
    def waitForDataList(self, chartType, kargs) -> list:
        # pause thread until the data is received from gui thread
        self.mutex.lock()
        self.retrieveDataListSignal.emit(chartType, kargs)
        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        # same as waitForImage
        return self.channel.dataListChannel
    
    
    def waitForTableData(self, conType) -> list[str]:
        self.mutex.lock()
        self.retrieveTableDataSignal.emit(conType)
        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        return self.channel.dataListChannel
    
    
    def waitForDutSummary(self, selectedHeads, selectedSites, kargs):
        self.mutex.lock()
        self.retrieveDutSummarySignal.emit(selectedHeads, selectedSites, kargs)
        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        return self.channel.dataListChannel
            
        
    def sendProgress(self):
        self.progressBarSignal.emit(int(10000 * self.loopCount/self.totalLoopCnt))
    
    
    def writeFileInfo(self):
        InfoSheet = self.sheetDict.get(ReportSelection.FileInfo, None)
        if InfoSheet is None:
            return
        
        headerLabels = [self.tr("Property Name"), self.tr("Value")]
        maxColWidth = [len(s) for s in headerLabels]
        
        InfoSheet.write_row(sv.finfoRow, sv.finfoCol, headerLabels, self.centerStyle)
        sv.finfoRow += 1
        #TODO get file info table
        dataTable = self.waitForTableData(tab.FileInfo)
                                
        for dataRow in dataTable:
            if self.forceQuit: return
            write_row_col(InfoSheet, 
                          sv.finfoRow, sv.finfoCol, 
                          dataRow, self.centerStyle, 
                          writeRow=True)
            maxColWidth = getMaxLength(maxColWidth, dataRow)
            sv.finfoRow += 1
            
        self.loopCount += 1
        self.sendProgress()
        _ = [InfoSheet.set_column(col, col, width*1.1) for col, width in enumerate(maxColWidth)]


    def writeGDR_DTR(self):
        GDR_DTR_Sheet = self.sheetDict.get(ReportSelection.GDR_DTR, None)
        if GDR_DTR_Sheet is None:
            return
        
        headerLabels = [self.tr("Record Type"), self.tr("Value"), self.tr("Approx. Location")]
        maxColWidth = [len(s) for s in headerLabels]
        
        GDR_DTR_Sheet.write_row(sv.drRow, sv.drCol, headerLabels, self.centerStyle)
        sv.drRow += 1
        #TODO
        dataTable = self.waitForTableData(tab.GDR_DTR)
                                
        for dataRow in dataTable:
            if self.forceQuit: return
            # remove \n that added besides values
            dataRow = [ele.strip("\n") for ele in dataRow]
            write_row_col(GDR_DTR_Sheet, 
                          sv.drRow, sv.drCol, 
                          dataRow, self.centerStyle, 
                          writeRow=True)
            maxColWidth = getMaxLength(maxColWidth, dataRow)
            sv.drRow += 1
            
        self.loopCount += 1
        self.sendProgress()
        _ = [GDR_DTR_Sheet.set_column(col, col, width*1.1) for col, width in enumerate(maxColWidth)]


    def writeDUT_Summary(self):
        DutSheet = self.sheetDict.get(ReportSelection.DUT, None)
        if DutSheet is None:
            return
        
        headerLabelList = [["", self.tr("Part ID"), self.tr("Test Head - Site"), self.tr("Tests Executed"), self.tr("Test Time"), self.tr("Hardware Bin"), self.tr("Software Bin"), self.tr("Wafer ID"), "(X, Y)", self.tr("DUT Flag")],
                            [self.tr("Test Number")],
                            [self.tr("Upper Limit")],
                            [self.tr("Lower Limit")],
                            [self.tr("Unit")]]
        maxColWidth = [len(s) for s in headerLabelList[0]]
        maxColWidth[0] = max([len(row[0]) for row in headerLabelList])
        
        # write headers
        for h in headerLabelList:
            DutSheet.write_row(sv.dutRow, sv.dutCol, h, self.centerStyle)
            sv.dutRow += 1
        # write DUT info
        # 2d, row: dut info of a dut, col: [id, site, ...]
        summaryTable = self.waitForDutSummary(self.selectedHeads, self.selectedSites, {})
        for ind, dataRow in enumerate(summaryTable):
            if self.forceQuit: return
            
            dataRow = ["#%d" % (ind+1)] + dataRow
            # choose style by dut flag
            dutFlag: str = dataRow[-1]
            if dutFlag.startswith("P"):
                cellStyle = self.centerStyle
            elif dutFlag.startswith("F"):
                cellStyle = self.failedStyle
            elif dutFlag.startswith("Super"):
                cellStyle = self.overrideStyle
            else:
                cellStyle = self.unknownStyle
            write_row_col(DutSheet, sv.dutRow, sv.dutCol, dataRow, cellStyle, writeRow=True)
            maxColWidth = getMaxLength(maxColWidth, dataRow)
            sv.dutRow += 1
            
        self.loopCount += 1
        self.sendProgress()
        _ = [DutSheet.set_column(col, col, width*1.1) for col, width in enumerate(maxColWidth)]
        # set current col to the last empty column
        sv.dutCol = len(headerLabelList[0])
    
    
    def writeDUT_Testdata(self, testTuple):
        DutSheet = self.sheetDict.get(ReportSelection.DUT, None)
        if DutSheet is None:
            return

        #append test raw data to the last column
        max_width = 0
        test_data_list, test_stat_list = self.waitForDutSummary(self.selectedHeads, self.selectedSites, {"testTuple": testTuple})
        data_style_list = [self.centerStyle if stat else self.failedStyle for stat in test_stat_list]
        write_row_col(DutSheet, 0, sv.dutCol, test_data_list, data_style_list, writeRow=False)
        max_width = max([len(s) for s in test_data_list])
        DutSheet.set_column(sv.dutCol, sv.dutCol, max_width*1.1)
        sv.dutCol += 1
        # loop cnt + 1 at the end
        self.loopCount += 1
        self.sendProgress()


    def writeBinChart(self, BinSheet: Worksheet):
        BinSheet = self.sheetDict.get(ReportSelection.Bin, None)
        if BinSheet is None:
            return
        
        # discard bin number (ele[1])
        extractData = lambda L: [ele if ind == 0 else ele[0] for ind, ele in enumerate(L)]
        maxColWidth = []
        for head, site in product(self.selectedHeads, self.selectedSites):
            if self.forceQuit: return
            # get bin image from GUI thread and insert to the sheet
            image_io = self.waitForImage(head=head, site=site, testTuple=(0, 0, ""), chartType=tab.Bin)
            image_width, image_height = get_png_size(image_io)
            
            # rescale the width of the image to 12 inches
            bin_scale = 12 / (image_width / 200)  # inches = pixel / dpi
            BinSheet.insert_image(sv.binRow, 0, "", {'x_scale': bin_scale, 'y_scale': bin_scale, 'image_data': image_io})
            sv.binRow += ceil((image_height / 200) * bin_scale / 0.21)
            
            # get hard bin list
            dataList_HB = extractData(self.waitForDataList(tab.Bin, {"head": head, "site": site, "bin": "HBIN"}))
            BinSheet.write_row(sv.binRow, 0, dataList_HB, self.txWrapStyle)
            # col_width = [max([len(s) for s in s.split("\n")]) if col_width[col:col+1] == [] or max([len(s) for s in s.split("\n")]) > col_width[col] else col_width[col] for col, s in enumerate(dataList_HB)]
            sv.binRow += 1
            # get soft bin list
            dataList_SB = extractData(self.waitForDataList(tab.Bin, {"head": head, "site": site, "bin": "SBIN"}))
            BinSheet.write_row(sv.binRow, 0, dataList_SB, self.txWrapStyle)
            # col_width = [max([len(s) for s in s.split("\n")]) if col_width[col:col+1] == [] or max([len(s) for s in s.split("\n")]) > col_width[col] else col_width[col] for col, s in enumerate(dataList_SB)]
            sv.binRow += 3
            
        self.loopCount += 1
        self.sendProgress()
        # _ = [BinSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]


    def writeWaferMap(self):
        WaferSheet = self.sheetDict.get(ReportSelection.Wafer, None)
        if WaferSheet is None:
            return
        
        for wafer in self.waferTuples:
            if self.forceQuit: return
            image_io = self.waitForImage(chartType=tab.Wafer)
            image_width, image_height = get_png_size(image_io)
            # rescale the width of the image to 12 inches
            wafer_scale = 12 / (image_width / 200)  # inches = pixel / dpi
            WaferSheet.insert_image(sv.waferRow, 0, "", {'x_scale': wafer_scale, 'y_scale': wafer_scale, 'image_data': image_io})
            sv.waferRow += ceil((image_height / 200) * wafer_scale / 0.21) + 2
            # gap between images
            sv.waferRow += 3
            self.loopCount += 1
            self.sendProgress()


    def writeTrendPlot(self, testTuple, head, site):
        TrendSheet:Worksheet = self.sheetDict.get(ReportSelection.Trend, None)
        if TrendSheet is None:
            return
        
        # get image and stat from main thread
        image_io = self.waitForImage(head, site, testTuple, tab.Trend)
        image_width, image_height = get_png_size(image_io)
        # rescale the width of the image to 12 inches
        trend_scale = 12 / (image_width / 200)  # inches = pixel / dpi
        dataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "testTuple": testTuple})
        # insert into the work sheet
        TrendSheet.insert_image(sv.trendRow, 0, "", {'x_scale': trend_scale, 'y_scale': trend_scale, 'image_data': image_io})
        sv.trendRow += ceil((image_height / 200) * trend_scale / 0.21)
        # TrendSheet.write_row(sv.trendRow, 0, header_stat, self.centerStyle)
        sv.trendRow += 1
        write_row_col(TrendSheet, sv.trendRow, 0, dataList, self.centerStyle, writeRow=True)
        trend_col_width = [trend_col_width[col] if trend_col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
        sv.trendRow += 2
        
        self.loopCount += 1
        self.sendProgress()


    def writeHistogram(self, testTuple, head, site):
        HistoSheet:Worksheet = self.sheetDict.get(ReportSelection.Histo, None)
        if HistoSheet is None:
            return
        
        image_io = self.waitForImage(head, site, testTuple, tab.Histo)
        dataList = self.waitForDataList(tab.Histo, {"head": head, "site": site, "testTuple": testTuple})
        #
        image_width, image_height = get_png_size(image_io)
        # rescale the width of the image to 12 inches
        histo_scale = 12 / (image_width / 200)  # inches = pixel / dpi
        HistoSheet.insert_image(sv.histoRow, 0, "", {'x_scale': histo_scale, 'y_scale': histo_scale, 'image_data': image_io})
        sv.histoRow += ceil((image_height / 200) * histo_scale / 0.21)
        # HistoSheet.write_row(sv.histoRow, 0, header_stat, self.centerStyle)
        sv.histoRow += 1
        write_row_col(HistoSheet, sv.histoRow, 0, dataList, self.centerStyle, writeRow=True)
        histo_col_width = [histo_col_width[col] if histo_col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
        sv.histoRow += 2

        self.loopCount += 1
        self.sendProgress()
        
    
    def writeStatistic(self, testTuple, head, site):
        # Sheet for statistics of test items, e.g. cpk, mean, etc.
        StatSheet:Worksheet = self.sheetDict.get(ReportSelection.Stat, None)
        if StatSheet is None:
            return
        
        if not hasStatHeader:
            # StatSheet.write_row(sv.statRow, 0, header_stat, self.centerStyle)
            sv.statRow += 1
            hasStatHeader = True    # avoid duplicated header
            
        dataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "testTuple": testTuple})
        write_row_col(StatSheet, sv.statRow, 0, dataList, self.centerStyle, writeRow=True)
        stat_col_width = [stat_col_width[col] if stat_col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
        sv.statRow += 1
        
        self.loopCount += 1
        self.sendProgress()
        
        
    
    @Slot()
    def generate_report(self):
        import time
        time.sleep(5)
        print("done")
        print(self.selectedContents, 
         self.testTuples, 
         self.selectedFiles, 
         self.selectedHeads, 
         self.selectedSites, 
         self.reportPath, 
         self.waferTuples, 
         self.totalLoopCnt)
        self.closeSignal.emit(True)
        return
        # test if the filepath is writable
        try:
            test_f = open(self.reportPath, "ab+")
            test_f.close()
        except Exception as e:
            self.msgSignal.emit("Error@@@" + repr(e))
            self.closeSignal.emit(True)
            return
            
        with Workbook(self.reportPath) as wb:
            self.centerStyle = wb.add_format({"align": "center", "valign": "vjustify"})
            self.failedStyle = wb.add_format({"align": "center", "valign": "vjustify", "bg_color": "#CC0000", "bold": True})
            self.unknownStyle = wb.add_format({"align": "center", "valign": "vjustify", "bg_color": "#FE7B00", "bold": True})
            # style with newline
            self.txWrapStyle = wb.add_format({"align": "center", "valign": "vjustify"})
            self.txWrapStyle.set_text_wrap()
            
            # 1. create sheets for each selected contents, create a dict to store the sheet object.
            # 2. write the contents that don't relay on the test numbers: file header, bin, wafer, dut summary (dut info part)
            # 3. loop thru test numbers, write dut summary (test data part).
            # 4. loop thru site & head to get images
            self.sheetDict = {}
            loopCnt = 0
            sv.init_variables()
                        
            for cont in [ReportSelection.FileInfo, ReportSelection.DUT, 
                         ReportSelection.GDR_DTR, ReportSelection.Stat, 
                         ReportSelection.Trend, ReportSelection.Histo, 
                         ReportSelection.Bin, ReportSelection.Wafer,
                         ReportSelection.PPQQ, ReportSelection.Correlation]:
                # sheet order in the xlsx is fixed
                if   cont == ReportSelection.FileInfo:  sheetName = self.tr("File Info")
                elif cont == ReportSelection.DUT:       sheetName = self.tr("DUT Summary")
                elif cont == ReportSelection.GDR_DTR:   sheetName = self.tr("GDR & DTR Summary")
                elif cont == ReportSelection.Stat:      sheetName = self.tr("Test Statistics")
                elif cont == ReportSelection.Trend:     sheetName = self.tr("Trend Chart")
                elif cont == ReportSelection.Histo:     sheetName = self.tr("Histogram")
                elif cont == ReportSelection.Bin:       sheetName = self.tr("Bin Chart")
                elif cont == ReportSelection.Wafer:     sheetName = self.tr("Wafer Map")
                elif cont == ReportSelection.PPQQ:      sheetName = self.tr("Normal Validation")
                else:                                   sheetName = self.tr("Correlation")
                if cont in self.selectedContents:       self.sheetDict[cont] = wb.add_worksheet(sheetName)
            
            # ** write contents independent of test numbers
            # file info                
            self.writeFileInfo()
            if self.forceQuit: return
            # GDR & DTR Summary
            self.writeGDR_DTR()
            if self.forceQuit: return
            # dut summary (dut part)
            self.writeDUT_Summary()
            if self.forceQuit: return
            # bin sheet
            self.writeBinChart()
            if self.forceQuit: return
            # wafer sheet
            self.writeWaferMap()
            if self.forceQuit: return
            
            # ** write contents related to test numbers
            trend_col_width = []#[len(s) for s in header_stat]
            histo_col_width = []#[len(s) for s in header_stat]
            stat_col_width = []#[len(s) for s in header_stat]
            hasStatHeader = False
            
            for testTuple in self.testTuples:                
                self.writeDUT_Testdata()
                
                for head, site in product(self.selectedHeads, self.selectedSites):
                    if self.forceQuit: return

                    self.writeTrendPlot(testTuple, head, site)
                    self.writeHistogram(testTuple, head, site)
                    self.writeStatistic(testTuple, head, site)
                
                # we can safely modify these constants without if statement checking
                sv.trendRow += 2     # add gap between different test items
                sv.histoRow += 2     # add gap between different test items
                sv.statRow += 1     # add gap between different test items
            
            # if tab.Trend in self.contL: [TrendSheet.set_column(col, col, width*1.1) for col, width in enumerate(trend_col_width)]
            # if tab.Histo in self.contL: [HistoSheet.set_column(col, col, width*1.1) for col, width in enumerate(histo_col_width)]
            # if tab.Stat in self.contL: [StatSheet.set_column(col, col, width*1.1) for col, width in enumerate(stat_col_width)]
        self.closeSignal.emit(True)
        
          

class progressDisplayer(QtWidgets.QDialog):
    '''a instance in GUI thread that passes data to generater thread'''
    def __init__(self, parent):
        super().__init__(parent)
        self.UI = Ui_loadingUI()
        self.UI.setupUi(self)
        self.closeEventByThread = False
        self.errorOccured = False
        # thread sync
        self.mutex = QtCore.QMutex()
        self.condWait = QtCore.QWaitCondition()
        self.workThread = QtCore.QThread(parent=self)
        # for sharing data between threads
        self.channel = dataChannel()
        
        self.setWindowTitle(self.tr("Generating XLSX report..."))
        self.UI.progressBar.setMaximum(10000)
        self.signals = signals()
        self.signals.msgSignal.connect(self.showMsg)
        self.signals.progressBarSignal.connect(self.updateProgressBar)
        self.signals.closeSignal.connect(self.closeExporter)
        self.signals.retrieveImageSignal.connect(self.getImageFromParentMethod)
        self.signals.retrieveDataListSignal.connect(self.getDataListFromParentMethod)
        self.signals.retrieveTableDataSignal.connect(self.getTableDataFromParent)
        self.signals.retrieveDutSummarySignal.connect(self.getDutSummaryFromParent)
        
        
    def setReportInfo(self, reportInfo: tuple):
        self.rg = reportGenerator(self.signals, 
                                  self.mutex, 
                                  self.condWait, 
                                  reportInfo,
                                  self.channel)
        self.rg.moveToThread(self.workThread)
        self.workThread.started.connect(self.rg.generate_report)


    def start(self):
        self.workThread.start()
        self.exec_()
    
    
    def closeEvent(self, event):
        if self.closeEventByThread:
            event.accept()
        else:
            # close by clicking X
            close = QMessageBox.question(self, self.tr("QUIT"), self.tr("Report is not finished,\nwanna terminate the process?"), QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.No)
            if close == QMessageBox.Yes:
                # if user clicked yes, temrinate thread and close window
                self.rg.forceQuit = True
                self.workThread.quit()
                # self.thread.wait()
                event.accept()
            else:
                event.ignore()
             
                    
    @Slot(str)
    def showMsg(self, msg:str):
        msgType, msgContent = msg.split("@@@")
        if msgType == "Error":
            self.errorOccured = True
            QMessageBox.critical(self, msgType, msgContent)
            logger.critical(msgContent)
        elif msgType == "Warning":
            QMessageBox.warning(self, msgType, msgContent)
            logger.warning(msgContent)
        else:
            logger.info(msgContent)
    
    
    @Slot(int)
    def updateProgressBar(self, num):
        self.UI.progressBar.setValue(num)
        self.UI.progressBar.setFormat(self.tr("Writing: %.02f%%") %(num/100))
      
      
    @Slot(bool)
    def closeExporter(self, closeUI):
        self.closeEventByThread = closeUI
        if closeUI:
            # gracefully quit thread before close export ui
            self.workThread.quit()
            self.workThread.wait()
            self.close()


    @Slot(int, int, tuple, int)
    def getImageFromParentMethod(self, head, site, testTuple, chartType):
        '''
        Lessons:
        1. Never access GUI objects from another thread, it will raise a segfault which is nearly not debuggable.
        2. use signal to transfer the data back to the thread might not be a great practice when the thread needs
        the data immediately, because the executaion of slot is not determinable. Use a shared class instead.
        3. the mutex.lock() is used for preventing wakeAll() is called before wait().
        '''
        self.channel.imageChannel = self.parent().parent.genPlot(head, site, testTuple, chartType, exportImg=True)
        self.mutex.lock()   # wait the mutex to unlock once the thread paused
        self.condWait.wakeAll()
        self.mutex.unlock()
    
    
    @Slot(int, dict)
    def getDataListFromParentMethod(self, chartType, kargs):
        self.channel.dataListChannel = self.parent().parent.prepareStatTableContent(chartType, **kargs)
        self.mutex.lock()   # wait the mutex to unlock once the thread paused
        self.condWait.wakeAll()
        self.mutex.unlock()
          
          
    @Slot(int)
    def getTableDataFromParent(self, conType):
        model = None
        data = []
        if conType == tab.DUT:
            # source model, contains all dut regardless of head/site selection
            model = self.parent().parent.tmodel_dut
        elif conType == tab.FileInfo:
            model = self.parent().parent.tmodel_info
        elif conType == tab.GDR_DTR:
            model = self.parent().parent.tmodel_datalog
            
        if model:
            for row in range(model.rowCount()):
                data.append([])
                for column in range(model.columnCount()):
                    index = model.index(row, column)
                    data[row].append(str(model.data(index)))
                    
        self.channel.dataListChannel = data
        self.mutex.lock()
        self.condWait.wakeAll()
        self.mutex.unlock()
        
        
    @Slot(list, list, dict)
    def getDutSummaryFromParent(self, selectedHeads, seletedSites, kargs):
        self.channel.dataListChannel = self.parent().parent.prepareDUTSummaryForExporter(selectedHeads, seletedSites, **kargs)
        self.mutex.lock()   # wait the mutex to unlock once the thread paused
        self.condWait.wakeAll()
        self.mutex.unlock()
        
                

class stdfExporter(QtWidgets.QDialog):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.exportUI = Ui_exportUI()
        self.exportUI.setupUi(self)
        self.mainUI = parent
        self.translatorUI = QTranslator(self)
        self.translatorCode = QTranslator(self)
        # store file, head, site cb objects
        self.file_cb_dict = {}
        self.head_cb_dict = {}
        self.site_cb_dict = {}
        self.AllTestItems = tuple()
        self.AllWaferItems = tuple()
        self.remainTestItems = []
        self.exportTestItems = []
        self.initTestListBox()
        # init search-related UI
        self.exportUI.SearchBox.textChanged.connect(self.searchInBox)
        self.exportUI.Clear.clicked.connect(lambda: self.exportUI.SearchBox.clear())
        # bind func to buttons
        self.exportUI.Addbutton.clicked.connect(self.onAdd)
        self.exportUI.AddAllbutton.clicked.connect(self.onAddAll)
        self.exportUI.Removebutton.clicked.connect(self.onRM)
        self.exportUI.RemoveAllbutton.clicked.connect(self.onRMAll)
        
        self.exportUI.toolButton.clicked.connect(self.outFileDialog)
        self.exportUI.nextBtn.clicked.connect(self.gotoNextPage)
        self.exportUI.previousBtn.clicked.connect(self.gotoPreviousPage)
        
        self.exportUI.Trend_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Histo_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Bin_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Stat_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.DUT_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.FileInfo_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Wafer_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.GDR_DTR_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.PPQQ_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Correlation_cb.clicked.connect(self.changeBtnStyle)
        # bind check/cancel button to function
        self.exportUI.checkAll.clicked.connect(lambda: self.toggleSite(True))
        self.exportUI.cancelAll.clicked.connect(lambda: self.toggleSite(False))
        
                
    def showUI(self):
        # used to determine the source of close event
        self.closeEventByThread = False
        # init UI
        self.exportUI.stackedWidget.setCurrentIndex(0)
        self.exportUI.previousBtn.setDisabled(True)
        self.previousPageIndex = 0
        self.changeBtnStyle()
        self.exec_()
        
    
    def onAdd(self):
        selectedIndex = self.selModel_remain.selection().indexes()
        
        if selectedIndex:
            items = [i.data() for i in selectedIndex]
            self.remainTestItems = list_operation(self.remainTestItems, "-", items)
            self.exportTestItems = list_operation(self.exportTestItems, "+", items)
            self.updateTestLists(exportList=self.exportTestItems)
            
        # if user add items from the filtered list, filter should be applied to the updated remainTestItems
        self.searchInBox()
    
    
    def onAddAll(self):
        self.remainTestItems = []
        self.exportTestItems = list(self.AllTestItems)
        self.updateTestLists(self.remainTestItems, self.exportTestItems)
    
    
    def onRM(self):
        selectedIndex = self.selModel_export.selection().indexes()
        
        if selectedIndex:
            items = [i.data() for i in selectedIndex]
            self.remainTestItems = list_operation(self.remainTestItems, "+", items)
            self.exportTestItems = list_operation(self.exportTestItems, "-", items)
            self.updateTestLists(self.remainTestItems, self.exportTestItems)
                
    
    def onRMAll(self):
        self.remainTestItems = list(self.AllTestItems)
        self.exportTestItems = []
        self.updateTestLists(self.remainTestItems, self.exportTestItems)
                
        
    def outFileDialog(self):
        outPath = QFileDialog.getSaveFileName(None, caption=self.tr("Save Report As"), filter=self.tr("Excel file (*.xlsx)"))
        if outPath[0]:
            self.exportUI.plainTextEdit.setPlainText(outPath[0])
            
            
    def searchInBox(self):
        # get current string in search box as re pattern
        SString = self.exportUI.SearchBox.text()
        if SString:
            try:
                cpl_pattern = re.compile(SString, re.IGNORECASE)
                filterList = [item for item in self.remainTestItems if cpl_pattern.search(item)]
                self.updateTestLists(remainList=filterList)
            except re.error:
                self.updateTestLists(self.remainTestItems)
        else:
            # if the string is empty, skip filter process
            self.updateTestLists(self.remainTestItems)
        
        
    def updateTestLists(self, remainList=None, exportList=None):
        if remainList is not None: self.slm_remain.setStringList(remainList)
        if exportList is not None: self.slm_export.setStringList(exportList)


    def initTestListBox(self):
        self.slm_remain = QtCore.QStringListModel()
        self.exportUI.TestList.setModel(self.slm_remain)
        self.exportUI.TestList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.exportUI.TestList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exportUI.TestList.doubleClicked.connect(self.onAdd)
        self.selModel_remain = self.exportUI.TestList.selectionModel()
        
        self.slm_export = QtCore.QStringListModel()
        self.exportUI.ExportTestList.setModel(self.slm_export)
        self.exportUI.ExportTestList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.exportUI.ExportTestList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exportUI.ExportTestList.doubleClicked.connect(self.onRM)
        self.selModel_export = self.exportUI.ExportTestList.selectionModel()
    
    
    def removeSiteCBs(self):
        '''
        Called by main UI after loading database
        '''
        for layout in [self.exportUI.gridLayout_file, 
                       self.exportUI.gridLayout_head,
                       self.exportUI.gridLayout_site]:
            cBList = []
            for i in range(layout.count()):
                cB = layout.itemAt(i).widget()
                if cB.objectName() in ["All", "checkAll", "cancelAll"]:
                    # do not delete default buttons
                    continue
                cBList.append(cB)
            deleteWidget(cBList)
        self.file_cb_dict = {}
        self.head_cb_dict = {}
        self.site_cb_dict = {}
    
    
    def refreshUI(self, completeTestList: list, completeWaferList: list, heads: list, sites: list, num_files: int):
        '''
        Called by main UI after loading database
        '''
        # get all test items from mainUI
        self.remainTestItems = completeTestList      # mutable
        self.exportTestItems = []
        # immutable, prevent parent list from modifying
        self.AllTestItems = tuple(self.remainTestItems)
        self.AllWaferItems = tuple(completeWaferList)
        self.updateTestLists(remainList=list(self.AllTestItems), exportList=self.exportTestItems)
        
        # add & enable checkboxes for files, heads and sites
        for fid in range(num_files):
            fileCB = QtWidgets.QCheckBox(self.exportUI.file_selection)
            fileCB.setText(f"File {fid}")
            # all file checkbox is checked by default
            fileCB.setChecked(True)
            self.exportUI.gridLayout_file.addWidget(fileCB, fid, 0)
            self.file_cb_dict[fid] = fileCB
        
        for i, headNum in enumerate(heads):
            headName = "Head %d" % headNum
            headCB = QtWidgets.QCheckBox(self.exportUI.site_selection)
            headCB.setObjectName(headName)
            headCB.setText(headName)
            self.exportUI.gridLayout_head.addWidget(headCB, i, 0)
            self.head_cb_dict[headNum] = headCB
                    
        for siteNum in sites:
            siteName = "Site %d" % siteNum
            siteCB = QtWidgets.QCheckBox(self.exportUI.site_selection)
            siteCB.setObjectName(siteName)
            siteCB.setText(siteName)
            row = 1 + siteNum//8
            col = siteNum % 8
            self.exportUI.gridLayout_site.addWidget(siteCB, row, col)
            self.site_cb_dict[siteNum] = siteCB
    
    
    def toggleSite(self, on=True):
        self.exportUI.All.setChecked(on)
        for cb in self.site_cb_dict.values():
            cb.setChecked(on)
       
       
    def getSelected_FileHeadSite(self) -> tuple:
        checkedFiles = []
        checkedHeads = []
        checkedSites = []
        
        if self.exportUI.All.isChecked():
            checkedSites.append(-1)
            
        for fid, cb_f in self.file_cb_dict.items():
            if cb_f.isChecked():
                checkedFiles.append(fid)
        for head_num, cb_h in self.head_cb_dict.items():
            if cb_h.isChecked():
                checkedHeads.append(head_num)        
        for site_num, cb_s in self.site_cb_dict.items():
            if cb_s.isChecked():
                checkedSites.append(site_num)
        
        checkedSites.sort()
        return checkedFiles, checkedHeads, checkedSites
    
    
    def getSelectedContents(self):
        selectedContents = []
        if self.exportUI.Trend_cb.isChecked(): selectedContents.append(ReportSelection.Trend)
        if self.exportUI.Histo_cb.isChecked(): selectedContents.append(ReportSelection.Histo)
        if self.exportUI.Bin_cb.isChecked(): selectedContents.append(ReportSelection.Bin)
        if self.exportUI.Stat_cb.isChecked(): selectedContents.append(ReportSelection.Stat)
        if self.exportUI.DUT_cb.isChecked(): selectedContents.append(ReportSelection.DUT)
        if self.exportUI.FileInfo_cb.isChecked(): selectedContents.append(ReportSelection.FileInfo)
        if self.exportUI.Wafer_cb.isChecked(): selectedContents.append(ReportSelection.Wafer)
        if self.exportUI.GDR_DTR_cb.isChecked(): selectedContents.append(ReportSelection.GDR_DTR)
        if self.exportUI.PPQQ_cb.isChecked(): selectedContents.append(ReportSelection.PPQQ)
        if self.exportUI.Correlation_cb.isChecked(): selectedContents.append(ReportSelection.Correlation)
        
        return selectedContents
    
    
    def getExportTestTuples(self):
        return [parseTestString(item) for item in self.exportTestItems]
    
    
    def getOutPath(self):
        path_out = self.exportUI.plainTextEdit.toPlainText()
        
        if path_out:
            if not os.access(os.path.dirname(path_out) , os.W_OK):
                return None
            return path_out
        else:
            return None
    
    
    def changeBtnStyle(self):
        currentPage = self.exportUI.stackedWidget.currentIndex()
        
        changeToConfirm = False
        if currentPage == 0:
            # change to "Confirm" only if file info & GDR/DTR are selected
            info_dr_set = {ReportSelection.FileInfo, ReportSelection.GDR_DTR}
            if set(self.getSelectedContents()) | info_dr_set == info_dr_set:
                changeToConfirm = True
        elif currentPage == 2:
            changeToConfirm = True
            
        if changeToConfirm:
            # in site page, change to Confirm
            # change the next button to Confirm
            self.exportUI.nextBtn.setStyleSheet("QPushButton {\n"
            "color: white;\n"
            "background-color: rgb(0, 120, 0); \n"
            "border: 1px solid rgb(0, 120, 0); \n"
            "border-radius: 5px;}\n"
            "\n"
            "QPushButton:pressed {\n"
            "background-color: rgb(0, 50, 0); \n"
            "border: 1px solid rgb(0, 50, 0);}")
            self.exportUI.nextBtn.setText(self.tr("Confirm"))
        
        else:
            # restore to Next>
            self.exportUI.nextBtn.setStyleSheet("QPushButton {\n"
            "color: white;\n"
            "background-color: rgb(120, 120, 120); \n"
            "border: 1px solid rgb(120, 120, 120); \n"
            "border-radius: 5px;}\n"
            "\n"
            "QPushButton:pressed {\n"
            "background-color: rgb(50, 50, 50); \n"
            "border: 1px solid rgb(50, 50, 50);}")
            self.exportUI.nextBtn.setText(self.tr("Next >"))
    
    
    def gotoPreviousPage(self):
        self.exportUI.stackedWidget.setCurrentIndex(self.previousPageIndex)
        if self.previousPageIndex == 0:
            self.exportUI.previousBtn.setDisabled(True)
        if self.previousPageIndex == 1:
            # make sure the user can return to the 1st page
            self.previousPageIndex = 0
        # ensure the next button shows "Next >"
        self.changeBtnStyle()
    
    
    def gotoNextPage(self):
        currentPage = self.exportUI.stackedWidget.currentIndex()
        if currentPage == 0:
            # content page
            if self.getOutPath() is None:
                QMessageBox.warning(self, self.tr("Warning"), self.tr("Output directory is invalid, not writable or not existed\n"))
                return
            
            selectedContents = self.getSelectedContents()
            if len(set(selectedContents) & {ReportSelection.Trend, 
                                            ReportSelection.Histo, 
                                            ReportSelection.DUT, 
                                            ReportSelection.Stat,
                                            ReportSelection.PPQQ}) > 0:
                # go to test page
                self.previousPageIndex = 0
                self.exportUI.previousBtn.setEnabled(True)
                self.exportUI.stackedWidget.setCurrentIndex(1)
                
            elif len(set(selectedContents) & {ReportSelection.Bin, 
                                              ReportSelection.Wafer,
                                              ReportSelection.Correlation}) > 0:
                # go to site page
                self.previousPageIndex = 0
                self.exportUI.previousBtn.setEnabled(True)
                self.exportUI.stackedWidget.setCurrentIndex(2)
                self.changeBtnStyle()
                
            else:
                # only file info & GDR/DTR are selected
                self.start()
        
        elif currentPage == 1:
            # test page
            testCount = len(self.getExportTestTuples())
            if (testCount > 0 or 
                len(set(self.getSelectedContents()) & {ReportSelection.Trend, 
                                                       ReportSelection.Histo,
                                                       ReportSelection.Stat,
                                                       ReportSelection.PPQQ}) == 0):
                # go to site page
                self.previousPageIndex = 1
                self.exportUI.previousBtn.setEnabled(True)
                self.exportUI.stackedWidget.setCurrentIndex(2)
                self.changeBtnStyle()
            else:
                QMessageBox.warning(self, self.tr("Warning"), 
                                    self.tr("At least one test item should be selected when Trend/Histo/Statistic/NormalValidation is checked\n"))
        
        else:
            # site page
            fileList, headList, siteList = self.getSelected_FileHeadSite()
            if 0 in [len(fileList), len(headList), len(siteList)]:
                QMessageBox.warning(self, self.tr("Warning"), 
                                    self.tr("File, Head and Site cannot be empty\n"))
            else:
                # start exporting
                self.start()
    
    
    def start(self):
        selectedContents = self.getSelectedContents()
        reportPath = self.getOutPath()
        selectedFiles, selectedHeads, selectedSites = self.getSelected_FileHeadSite()
        testTuples = self.getExportTestTuples()
        waferTuples = [parseTestString(witem, True) for witem in self.AllWaferItems]
        if len(waferTuples) == 1:
            # only default stacked wafer is in list, no actual wafer data exists
            waferTuples = []
       
        # determine the max value of progress bar
        totalLoopCnt = 0
        if ReportSelection.Trend in selectedContents:
            totalLoopCnt += len(testTuples) * len(selectedSites) * len(selectedHeads)
        if ReportSelection.Histo in selectedContents:
            totalLoopCnt += len(testTuples) * len(selectedSites) * len(selectedHeads)
        if ReportSelection.Stat in selectedContents:
            totalLoopCnt += len(testTuples) * len(selectedSites) * len(selectedHeads)
        if ReportSelection.Bin in selectedContents:
            totalLoopCnt += len(selectedSites) * len(selectedHeads)
        if ReportSelection.FileInfo in selectedContents:
            totalLoopCnt += 1
        if ReportSelection.DUT in selectedContents:
            totalLoopCnt += (1 + len(testTuples))   # dut info part + test part
        if ReportSelection.Wafer in selectedContents:
            totalLoopCnt += len(waferTuples) * len(selectedSites) * len(selectedHeads)
        if ReportSelection.GDR_DTR in selectedContents:
            totalLoopCnt += 1
                    
        self.pd = progressDisplayer(parent=self)
        rinfo = (selectedContents, testTuples,
                 selectedFiles, selectedHeads, 
                 selectedSites, reportPath, 
                 waferTuples, totalLoopCnt)
        self.pd.setReportInfo(rinfo)
        self.pd.start()
        if self.pd.errorOccured:
            # error occured
            title = self.tr("Error occurred")
            msg = self.tr("Something's wrong when exporting, you can still check the report in:")
        elif self.pd.closeEventByThread:
            # end normally
            title = self.tr("Export completed!")
            msg = self.tr("Report path:")
        else:
            # aborted
            title = self.tr("Process Aborted!")
            msg = self.tr("Partial report is saved in:")
            
        msgbox = QMessageBox(None)
        msgbox.setText(title)
        msgbox.setInformativeText('%s\n\n%s\n'%(msg, reportPath))
        msgbox.setIcon(QMessageBox.Icon.Information)
        revealBtn = msgbox.addButton(self.tr(" Reveal in folder "), QMessageBox.ButtonRole.ApplyRole)
        openBtn = msgbox.addButton(self.tr("Open..."), QMessageBox.ButtonRole.ActionRole)
        okBtn = msgbox.addButton(self.tr("OK"), QMessageBox.ButtonRole.YesRole)
        msgbox.setDefaultButton(okBtn)
        msgbox.exec_()
        if msgbox.clickedButton() == revealBtn:
            revealFile(reportPath)
        elif msgbox.clickedButton() == openBtn:
            openFileInOS(reportPath)

                
    def closeEvent(self, event):
        # close by clicking X
        # close = QMessageBox.question(self, "QUIT", "All changes will be lost,\nstill wanna quit?", QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.No)
        # if close == QMessageBox.Yes:
        #     # if user clicked yes, temrinate thread and close window
        event.accept()
        # else:
        #     event.ignore()

