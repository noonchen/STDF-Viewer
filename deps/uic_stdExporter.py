#
# uic_stdExporter.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 11th 2020
# -----
# Last Modified: Mon Apr 12 2021
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
import os
# import io
# import threading
from enum import IntEnum
from xlsxwriter import Workbook
import subprocess, platform
# pyqt5
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractItemView, QFileDialog
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from deps.ui.stdfViewer_exportUI import Ui_exportUI
from deps.ui.stdfViewer_loadingUI import Ui_loadingUI
# pyside2
# from PySide2 import QtCore, QtWidgets
# from PySide2.QtWidgets import QAbstractItemView, QFileDialog
# from deps.ui.stdfViewer_exportUI_side import Ui_exportUI
# from deps.ui.stdfViewer_loadingUI_side import Ui_loadingUI
# from PySide2.QtCore import Signal, Slot

# def print_thread(fname):
#     print("Thread: %s, function name: %s" % (threading.currentThread().getName(), fname))
    
# simulate a Enum in python
# class Tab(tuple): __getattr__ = tuple.index
# tab = Tab(["DUT", "Trend", "Histo", "Bin", "Stat", "FileInfo"])
class tab(IntEnum):
    DUT = 0
    Trend = 1   # Do not change
    Histo = 2   # Int number
    Bin = 3     # of these items
    Wafer = 4   # It should match tab order of the main window
    Stat = 5
    FileInfo = 6


def list_operation(main, method, other):
    main = [] if main is None else main
    other = [] if other is None else other
    
    if method == "+":
        tmp = set(main) | set(other)
        return sorted(tmp, key=lambda item: int(item.split("\t")[0]))
    
    elif method == "-":
        tmp = set(main) - set(other)
        return sorted(tmp, key=lambda item: int(item.split("\t")[0]))



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
    prepareDataSignal = Signal(int, int, int)    # head, site, test_num
    retrieveImageSignal = Signal(int, int, int, int)     # head, site, test_num, chartType
    retrieveDataListSignal = Signal(int, dict)      # chartType, {site, test_num} / {site, bin} / {site, test_num, RawData}
    retrieveTableDataSignal = Signal(int)           # FileInfo table
    retrieveDutSummarySignal = Signal(list, list, dict)   # selected heads, selected sites, {test_num}, get dut info or dut test data
    # signals for sending data to qthread
    # sendImage = Signal(io.BytesIO)
    # sendDataList = Signal(list)
    
    
    
class reportGenerator(QtCore.QObject):
    def __init__(self, signals, mutex, conditionWait, settings, channel):
        super().__init__()
        self.forceQuit = False
        self.mutex = mutex
        self.condWait = conditionWait
        self.contL, self.numL, self.headL, self.siteL, self.path, self.numWafer, self.totalLoopCnt = settings
        # for sharing data from gui thread
        self.channel = channel
        # signals for updating progress bar dialog
        self.msgSignal = signals.msgSignal
        self.progressBarSignal = signals.progressBarSignal
        self.closeSignal = signals.closeSignal
        # signals for data communication
        self.prepareDataSignal = signals.prepareDataSignal
        self.retrieveImageSignal = signals.retrieveImageSignal
        self.retrieveDataListSignal = signals.retrieveDataListSignal
        self.retrieveTableDataSignal = signals.retrieveTableDataSignal
        self.retrieveDutSummarySignal = signals.retrieveDutSummarySignal
        
    # @Slot(io.BytesIO)
    # def getImage(self, image):
    #     print_thread("getImage")
    #     self.tmp_image = image
    
    # @Slot(list)
    # def getDataList(self, datalist):
    #     print_thread("getDataList")
    #     self.tmp_dataList = datalist
    
    
    def waitForImage(self, head, site, test_num, chartType):
        # print_thread("waitForImage")
        # pause thread until the data is received from gui thread
        self.mutex.lock()
        self.retrieveImageSignal.emit(head, site, test_num, chartType)
        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        # by the time the thread is waked, the data is already published in imageChannel in mainthread
        return self.channel.imageChannel
            
            
    def waitForDataList(self, chartType, kargs):
        #FIXME
        # print_thread("waitForDataList")
        # pause thread until the data is received from gui thread
        self.mutex.lock()        
        self.retrieveDataListSignal.emit(chartType, kargs)

        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        # same as waitForImage
        return self.channel.dataListChannel        
    
    
    def waitForTableData(self, conType):
        #FIXME
        self.mutex.lock()        
        self.retrieveTableDataSignal.emit(conType)

        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        return self.channel.dataListChannel        
    
    
    def waitForDutSummary(self, selectedHeads, selectedSites, kargs):
        #FIXME
        self.mutex.lock()        
        self.retrieveDutSummarySignal.emit(selectedHeads, selectedSites, kargs)

        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        return self.channel.dataListChannel        
            
        
    @Slot()
    def generate_report(self):
        # print_thread("generate_report")
        def write_row(sheet, row, scol, dataL, format):
            # write as number in default, otherwise as string
            for i in range(len(dataL)):
                try:
                    sheet.write_number(row, scol+i, float(dataL[i]), format)
                except (TypeError, ValueError):
                    sheet.write_string(row, scol+i, dataL[i], format)
                    
        def write_col(sheet, row, scol, dataL, format):
            # write as number in default, otherwise as string
            for i in range(len(dataL)):
                try:
                    sheet.write_number(row+i, scol, float(dataL[i]), format)
                except (TypeError, ValueError):
                    sheet.write_string(row+i, scol, dataL[i], format)                    
                    
        sendProgress = lambda loopCnt: self.progressBarSignal.emit(int(10000 * loopCnt/self.totalLoopCnt))
        
        with Workbook(self.path) as wb:
            centerStyle = wb.add_format({"align": "center", "valign": "vjustify"})
            header_stat = ["Test Number / Site", "Test Name", "Unit", "Low Limit", "High Limit", "Fail Count", "Cpk", "Average", "Median", "St. Dev.", "Min", "Max"]
            imageHeight_in_rowHeight = 20
            x_scale = imageHeight_in_rowHeight * 0.21 / 4      # default cell height = 0.21 inches, image height = 4 inches
            loopCnt = 0     # used for representing generation progress

            for cont in self.contL:
                if cont == tab.Trend:
                    # Sheet for trend plot and test data
                    TrendSheet = wb.add_worksheet("Trend Chart")
                    currentRow = 0
                    startCol = 0
                    col_width = [len(s) for s in header_stat]
                    for test_num in self.numL:
                        for site in self.siteL:
                            for head in self.headL:
                                if self.forceQuit: return
                                # self.ExportWind.parent.prepareData([test_num], [site])
                                self.prepareDataSignal.emit(head, site, test_num)
                                # image_io = self.ExportWind.parent.genPlot(None, None, site, test_num, tab.Trend, exportImg=True)
                                # dataList = self.ExportWind.parent.prepareTableContent(tab.Trend, site=site, test_num=test_num)
                                image_io = self.waitForImage(head, site, test_num, tab.Trend)
                                dataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "test_num": test_num})
                                rawDataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "test_num": test_num, "RawData": True})
                                TrendSheet.insert_image(currentRow, startCol, "", {'x_scale': x_scale, 'y_scale': x_scale, 'image_data': image_io})
                                currentRow += imageHeight_in_rowHeight
                                TrendSheet.write_row(currentRow, startCol, header_stat, centerStyle)
                                currentRow += 1
                                write_row(TrendSheet, currentRow, startCol, dataList, centerStyle)
                                col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
                                # Add raw data source of trend chart below
                                currentRow += 1
                                TrendSheet.write_row(currentRow, startCol, ["Raw data:"])
                                currentRow += 1
                                write_row(TrendSheet, currentRow, startCol, [row[6] for row in rawDataList], centerStyle)   # data in index 6
                                currentRow += 2
                                loopCnt += 1
                                sendProgress(loopCnt)
                        currentRow += 2     # add gap between different test items
                    [TrendSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                                                    
                elif cont == tab.Histo:
                    # Sheet for histogram plot and test data
                    HistoSheet = wb.add_worksheet("Histogram")
                    currentRow = 0
                    startCol = 0
                    col_width = [len(s) for s in header_stat]
                    for test_num in self.numL:
                        for site in self.siteL:
                            for head in self.headL:
                                if self.forceQuit: return
                                # self.ExportWind.parent.prepareData([test_num], [site])
                                self.prepareDataSignal.emit(head, site, test_num)
                                # image_io = self.ExportWind.parent.genPlot(None, None, site, test_num, tab.Histo, exportImg=True)
                                # dataList = self.ExportWind.parent.prepareTableContent(tab.Histo, site=site, test_num=test_num)
                                image_io = self.waitForImage(head, site, test_num, tab.Histo)
                                dataList = self.waitForDataList(tab.Histo, {"head": head, "site": site, "test_num": test_num})                                
                                HistoSheet.insert_image(currentRow, startCol, "", {'x_scale': x_scale, 'y_scale': x_scale, 'image_data': image_io})
                                currentRow += imageHeight_in_rowHeight
                                HistoSheet.write_row(currentRow, startCol, header_stat, centerStyle)
                                currentRow += 1                                     
                                write_row(HistoSheet, currentRow, startCol, dataList, centerStyle)
                                col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
                                # HistoSheet.write_row(currentRow, startCol, dataList)
                                currentRow += 2
                                loopCnt += 1
                                sendProgress(loopCnt)
                        currentRow += 2     # add gap between different test items                            
                    [HistoSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                    
                elif cont == tab.Bin:
                    # Sheet for bin distribution
                    BinSheet = wb.add_worksheet("Bin Chart")
                    currentRow = 0
                    startCol = 0
                    extractData = lambda L: [ele if ind == 0 else ele[0] for ind, ele in enumerate(L)]
                    col_width = []
                    for site in self.siteL:
                        for head in self.headL:
                            if self.forceQuit: return
                            # image_io = self.ExportWind.parent.genPlot(None, None, site, 0, tab.Bin, exportImg=True)
                            image_io = self.waitForImage(head=head, site=site, test_num=0, chartType=tab.Bin)
                            BinSheet.insert_image(currentRow, startCol, "", {'x_scale': x_scale, 'y_scale': x_scale, 'image_data': image_io})
                            currentRow += imageHeight_in_rowHeight
                            # dataList_HB = extractData(self.ExportWind.parent.prepareTableContent(tab.Bin, bin="HBIN", site=site))
                            dataList_HB = extractData(self.waitForDataList(tab.Bin, {"head": head, "site": site, "bin": "HBIN"}))
                            BinSheet.write_row(currentRow, startCol, dataList_HB, centerStyle)
                            col_width = [max([len(s) for s in s.split("\n")]) if col_width[col:col+1] == [] or max([len(s) for s in s.split("\n")]) > col_width[col] else col_width[col] for col, s in enumerate(dataList_HB)]
                            currentRow += 1
                            # dataList_SB = extractData(self.ExportWind.parent.prepareTableContent(tab.Bin, bin="SBIN", site=site))
                            dataList_SB = extractData(self.waitForDataList(tab.Bin, {"head": head, "site": site, "bin": "SBIN"}))
                            BinSheet.write_row(currentRow, startCol, dataList_SB, centerStyle)
                            col_width = [max([len(s) for s in s.split("\n")]) if col_width[col:col+1] == [] or max([len(s) for s in s.split("\n")]) > col_width[col] else col_width[col] for col, s in enumerate(dataList_SB)]
                            currentRow += 3
                            loopCnt += 1
                            sendProgress(loopCnt)
                    [BinSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                    
                elif cont == tab.Stat:
                    # Sheet for statistics of test items, e.g. cpk, mean, etc.
                    StatSheet = wb.add_worksheet("Test Statistics")
                    currentRow = 0
                    startCol = 0
                    StatSheet.write_row(currentRow, startCol, header_stat, centerStyle)
                    col_width = [len(s) for s in header_stat]
                    currentRow += 1
                    for test_num in self.numL:
                        for site in self.siteL:
                            for head in self.headL:
                                if self.forceQuit: return
                                # self.ExportWind.parent.prepareData([test_num], [site])
                                self.prepareDataSignal.emit(head, site, test_num)
                                # dataList = self.ExportWind.parent.prepareTableContent(tab.Trend, site=site, test_num=test_num)
                                dataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "test_num": test_num})
                                write_row(StatSheet, currentRow, startCol, dataList, centerStyle)
                                # StatSheet.write_row(currentRow, startCol, dataList)
                                col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
                                currentRow += 1
                                loopCnt += 1
                                sendProgress(loopCnt)
                        currentRow += 1     # add gap between different test items
                    [StatSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]

                elif cont == tab.FileInfo:
                    # Sheet for file information
                    FileInfoSheet = wb.add_worksheet("File Info")
                    headerLabels = ["Property Name", "Value"]
                    col_width = [len(s) for s in headerLabels]
                    
                    currentRow = 0
                    startCol = 0
                    FileInfoSheet.write_row(currentRow, startCol, headerLabels, centerStyle)
                    currentRow += 1
                    data = self.waitForTableData(cont)   
                                            
                    for row in data:
                        if self.forceQuit: return
                        write_row(FileInfoSheet, currentRow, startCol, row, centerStyle)
                        col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(row)]
                        currentRow += 1
                        
                    loopCnt += 1
                    sendProgress(loopCnt)
                    [FileInfoSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                        
                elif cont == tab.DUT:
                    # Sheet for DUT summary & Test raw data
                    DutSheet = wb.add_worksheet("DUT Summary")
                    headerLabelList = [["", "Part ID", "Test Head", "Test Site", "Tests Executed", "Test Time", "Hardware Bin", "Software Bin", "DUT Flag"],
                                        ["Test Number"],
                                        ["Upper Limit"],
                                        ["Lower Limit"],
                                        ["Unit"]]
                    col_width = [len(s) for s in headerLabelList[0]]
                    col_width[0] = max([len(row[0]) for row in headerLabelList])
                    currentRow = 0
                    startCol = 0
                    # write headers
                    for h in headerLabelList:
                        DutSheet.write_row(currentRow, startCol, h, centerStyle)
                        currentRow += 1
                    # write DUT info
                    DutInfoList = self.waitForDutSummary(self.headL, self.siteL, {})    # 2d, row: dut info of a dut, col: [id, site, ...]
                    for count, infoRow in enumerate(DutInfoList):
                        L = ["#%d" % (count+1)] + infoRow
                        write_row(DutSheet, currentRow, startCol, L, centerStyle)
                        col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(L)]
                        currentRow += 1                            
                    [DutSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                    #append test raw data to the last column
                    startRow = 0
                    currentCol = len(headerLabelList[0])
                    for test_num in self.numL:
                        if self.forceQuit: return
                        max_width = 0
                        DutDataList = self.waitForDutSummary(self.headL, self.siteL, {"test_num": test_num})
                        write_col(DutSheet, startRow, currentCol, DutDataList, centerStyle)
                        max_width = max([len(s) for s in DutDataList])
                        DutSheet.set_column(currentCol, currentCol, max_width*1.1)
                        currentCol += 1
                        loopCnt += 1
                        sendProgress(loopCnt)
                        
                elif cont == tab.Wafer:
                    imageHeight_in_rowHeight = 50
                    y_scale = imageHeight_in_rowHeight * 0.21 / 10
                    # Sheet for wafer map
                    WaferSheet = wb.add_worksheet("Wafer Map")
                    currentRow = 0
                    startCol = 0
                    for wafer in self.numWafer:
                        for site in self.siteL:
                            for head in self.headL:
                                if self.forceQuit: return
                                image_io = self.waitForImage(head=head, site=site, test_num=wafer, chartType=tab.Wafer)
                                WaferSheet.insert_image(currentRow, startCol, "", {'x_scale': y_scale, 'y_scale': y_scale, 'image_data': image_io})
                                currentRow += imageHeight_in_rowHeight + 1
                                # dataList_HB = extractData(self.waitForDataList(tab.Bin, {"site": site, "bin": "HBIN"}))
                                # WaferSheet.write_row(currentRow, startCol, dataList_HB)
                                # currentRow += 1
                                loopCnt += 1
                                sendProgress(loopCnt)
                        currentRow += 3
                                                                                            
        self.closeSignal.emit(True)
        
          

class progressDisplayer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.UI = Ui_loadingUI()
        self.UI.setupUi(self)
        self.closeEventByThread = False
        # thread sync
        self.mutex = QtCore.QMutex()
        self.condWait = QtCore.QWaitCondition()
        self.thread = QtCore.QThread(parent=self)
        # for sharing data between threads
        self.channel = dataChannel()
                
        self.setWindowTitle("Generating XLSX report...")
        self.UI.progressBar.setMaximum(10000)
        self.signals = signals()
        self.signals.progressBarSignal.connect(self.updateProgressBar)
        self.signals.closeSignal.connect(self.closeExporter)
        self.signals.prepareDataSignal.connect(self.prepareData)
        self.signals.retrieveImageSignal.connect(self.getImageFromParentMethod)
        self.signals.retrieveDataListSignal.connect(self.getDataListFromParentMethod)
        self.signals.retrieveTableDataSignal.connect(self.getTableDataFromParent)
        self.signals.retrieveDutSummarySignal.connect(self.getDutSummaryFromParent)
        
        self.rg = reportGenerator(self.signals, 
                                  self.mutex, 
                                  self.condWait, 
                                  (parent.contL, parent.numL, parent.headL, parent.siteL, parent.path, parent.numWafer, parent.totalLoopCnt),
                                  self.channel)
        # send data from parent to qthread, bind before moveToThread
        # -- Deprecated --
        # self.signals.sendImage.connect(self.rg.getImage)
        # self.signals.sendDataList.connect(self.rg.getDataList)
        
        self.rg.moveToThread(self.thread)
        self.thread.started.connect(self.rg.generate_report)
        self.thread.start()
        self.exec_()
        
        
    def closeEvent(self, event):
        if self.closeEventByThread:
            event.accept()
        else:
            # close by clicking X
            close = QtWidgets.QMessageBox.question(self, "QUIT", "Report is not finished,\nwanna terminate the process?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.No)
            if close == QtWidgets.QMessageBox.Yes:
                # if user clicked yes, temrinate thread and close window
                self.rg.forceQuit = True
                self.thread.quit()
                # self.thread.wait()
                event.accept()
            else:
                event.ignore()
             
                    
    @Slot(int)
    def updateProgressBar(self, num):
        self.UI.progressBar.setValue(num)
        self.UI.progressBar.setFormat("Writing: %.02f%%" %(num/100))
      
      
    @Slot(bool)
    def closeExporter(self, closeUI):
        self.closeEventByThread = closeUI
        if closeUI:
            # gracefully quit thread before close export ui
            self.thread.quit()
            self.thread.wait()
            self.close()


    @Slot(int, int, int)
    def prepareData(self, head, site, test_num):
        # print_thread("prepareData")
        self.parent().parent.prepareData([test_num], [site], [head])
    
    
    @Slot(int, int, int, int)
    def getImageFromParentMethod(self, head, site, test_num, chartType):
        '''
        Lessons:
        1. Never access GUI objects from another thread, it will raise a segfault which is nearly not debuggable.
        2. use signal to transfer the data back to the thread might not be a great practice when the thread needs
        the data immediately, because the executaion of slot is not determinable. Use a shared class instead.
        3. the mutex.lock() is used for preventing wakeAll() is called before wait().
        '''
        # print_thread("getImageFromParentMethod")
        self.channel.imageChannel = self.parent().parent.genPlot(head, site, test_num, chartType, exportImg=True)
        self.mutex.lock()   # wait the mutex to unlock once the thread paused
        # self.signals.sendImage.emit(imageIO)
        self.condWait.wakeAll()
        self.mutex.unlock()
    
    
    @Slot(int, dict)
    def getDataListFromParentMethod(self, chartType, kargs):
        # print_thread("getDataListFromParentMethod")
        self.channel.dataListChannel = self.parent().parent.prepareTableContent(chartType, **kargs)
        self.mutex.lock()   # wait the mutex to unlock once the thread paused
        # self.signals.sendDataList.emit(dataList)
        self.condWait.wakeAll()
        self.mutex.unlock()
          
          
    @Slot(int)
    def getTableDataFromParent(self, conType):
        model = None
        data = []
        if conType == tab.DUT:
            model = self.parent().parent.tmodel_dut
        elif conType == tab.FileInfo:
            model = self.parent().parent.tmodel_info
            
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
        self.channel.dataListChannel = self.parent().parent.prepareDataForDUTSummary(selectedHeads, seletedSites, **kargs)
        self.mutex.lock()   # wait the mutex to unlock once the thread paused
        # self.signals.sendDataList.emit(dataList)
        self.condWait.wakeAll()
        self.mutex.unlock()
        
                

class stdfExporter(QtWidgets.QDialog):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self.closeEventByThread = False    # used to determine the source of close event

        # self.exportUI = uic.loadUi('ui/stdfViewer_exportUI.ui', self)    # uic
        self.exportUI = Ui_exportUI()
        self.exportUI.setupUi(self)
        self.parent = parent
        # store head, site cb objects
        self.head_cb_dict = {}
        self.site_cb_dict = {}
        self.AllTestItems = None
        self.remainTestItems = []
        self.exportTestItems = []
        # init search-related UI
        self.exportUI.SearchBox.textChanged.connect(self.searchInBox)
        self.exportUI.Clear.clicked.connect(lambda: self.exportUI.SearchBox.clear())
        # bind func to buttons
        self.exportUI.Addbutton.clicked.connect(self.onAdd)
        self.exportUI.AddAllbutton.clicked.connect(self.onAddAll)
        self.exportUI.Removebutton.clicked.connect(self.onRM)
        self.exportUI.RemoveAllbutton.clicked.connect(self.onRMAll)
        
        self.exportUI.toolButton.clicked.connect(self.outFileDialog)
        self.exportUI.Confirm.clicked.connect(self.check_inputs)
        self.exportUI.Cancel.clicked.connect(lambda: self.close())
        
        try:
            # get all test items from mainUI
            self.remainTestItems = self.parent.completeTestList      # mutable
            self.AllTestItems = tuple(self.remainTestItems)     # immutable
            self.initSiteCBs()
            self.initTestItems()
        except Exception as e:
            print(repr(e))

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
        outPath = QFileDialog.getSaveFileName(None, caption="Save Report As", filter="Excel file (*.xlsx)")
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
        if remainList != None: self.slm_remain.setStringList(remainList)
        if exportList != None: self.slm_export.setStringList(exportList)


    def initTestItems(self):
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
        
        self.updateTestLists(remainList = list(self.AllTestItems))
    
    
    def initSiteCBs(self):
        # add & enable checkboxes for each heads
        for i, headNum in enumerate(self.parent.availableHeads):
            headName = "Head %d" % headNum
            self.head_cb_dict[headNum] = QtWidgets.QCheckBox(self.exportUI.site_selection)
            self.head_cb_dict[headNum].setObjectName(headName)
            self.head_cb_dict[headNum].setText(headName)
            row = i
            col = 0
            self.exportUI.gridLayout_head.addWidget(self.head_cb_dict[headNum], row, col)
                    
        # add & enable checkboxes for each sites
        for siteNum in self.parent.availableSites:
            siteName = "Site %d" % siteNum
            self.site_cb_dict[siteNum] = QtWidgets.QCheckBox(self.exportUI.site_selection)
            self.site_cb_dict[siteNum].setObjectName(siteName)
            self.site_cb_dict[siteNum].setText(siteName)
            row = 1 + siteNum//8
            col = siteNum % 8
            self.exportUI.gridLayout_site.addWidget(self.site_cb_dict[siteNum], row, col)
        # bind check/cancel button to function
        self.exportUI.checkAll.clicked.connect(lambda: self.toggleSite(True))
        self.exportUI.cancelAll.clicked.connect(lambda: self.toggleSite(False))
        
        
    def toggleSite(self, on=True):
        self.exportUI.All.setChecked(on)
        for siteNum, cb in self.site_cb_dict.items():
            cb.setChecked(on)
       
       
    def getHeads_Sites(self):
        checkedHeads = []
        checkedSites = []
        
        if self.exportUI.All.isChecked():
            checkedSites.append(-1)
            
        for head_num, cb_h in self.head_cb_dict.items():
            if cb_h.isChecked():
                checkedHeads.append(head_num)        
        for site_num, cb_s in self.site_cb_dict.items():
            if cb_s.isChecked():
                checkedSites.append(site_num)
        
        checkedSites.sort()
        return [checkedHeads, checkedSites]
    
    
    def getSelectedContents(self):
        selectedContents = []
        if self.exportUI.Trend_cb.isChecked(): selectedContents.append(tab.Trend)
        if self.exportUI.Histo_cb.isChecked(): selectedContents.append(tab.Histo)
        if self.exportUI.Bin_cb.isChecked(): selectedContents.append(tab.Bin)
        if self.exportUI.Stat_cb.isChecked(): selectedContents.append(tab.Stat)
        if self.exportUI.DUT_cb.isChecked(): selectedContents.append(tab.DUT)
        if self.exportUI.FileInfo_cb.isChecked(): selectedContents.append(tab.FileInfo)
        if self.exportUI.Wafer_cb.isChecked(): selectedContents.append(tab.Wafer)
        
        return selectedContents
    
    
    def getExportTestNums(self):
        return [int(item.split("\t")[0]) for item in self.exportTestItems]
    
    
    def getOutPath(self):
        path_out = self.exportUI.plainTextEdit.toPlainText()
        
        if path_out:
            if not os.access(os.path.dirname(path_out) , os.W_OK):
                return None
            return path_out
        else:
            return None
    
  
    def check_inputs(self):
        self.numL = self.getExportTestNums()
        self.headL, self.siteL = self.getHeads_Sites()
        self.contL = self.getSelectedContents()
        self.path = self.getOutPath()
        self.numWafer = sorted([i for i in self.parent.dataInfo.waferDict.keys()])
       
        if len(self.numL) == 0 or len(self.headL) == 0 or len(self.siteL) == 0 or len(self.contL) == 0 or self.path is None:
            # input not complete
            message = ""
            if len(self.numL) == 0: message += "No test item is selected\n\n"
            if len(self.headL) == 0: message += "No head is selected\n\n"
            if len(self.siteL) == 0: message += "No site is selected\n\n"
            if len(self.contL) == 0: message += "No content is selected\n\n"
            if self.path is None: message += "Output directory is invalid, not writable or not existed\n"
            
            QtWidgets.QMessageBox.warning(self, "Warning", message)
            
        else:
            # report generation code here
            # self.parent.prepareData(selectItemNums, selectSites)
            # self.parent.genPlot(None, None, site, test_num, tabIndex, exportImg=True)
            # self.parent.prepareTableContent(tabType, site=site, test_num=test_num)
            self.totalLoopCnt = 0
            for cont in self.contL:
                if cont == tab.Trend or cont == tab.Histo or cont == tab.Stat:
                    self.totalLoopCnt += len(self.numL) * len(self.siteL) * len(self.headL)
                elif cont == tab.Bin:
                    self.totalLoopCnt += len(self.siteL) * len(self.headL)
                elif cont == tab.FileInfo:
                    self.totalLoopCnt += 1
                elif cont == tab.DUT:
                    self.totalLoopCnt += len(self.numL)
                elif cont == tab.Wafer:
                    self.totalLoopCnt += len(self.numWafer) * len(self.siteL) * len(self.headL)
                # elif False:
                #     # Update loopcnt if more contents are added
                #     # self.totalLoopCnt += len(self.siteL)
                #     pass
                    
            self.pd = progressDisplayer(parent=self)
            # self.generate_report()
            if self.pd.closeEventByThread:
                # end normally
                title = "Export completed!"
                msg = "Report path:"
            else:
                # aborted
                title = "Process Aborted!"
                msg = "Partial report is saved in:"
                
            msgbox = QtWidgets.QMessageBox(None)
            msgbox.setText(title)
            msgbox.setInformativeText('%s\n\n%s\n'%(msg, self.path))
            msgbox.setIcon(QtWidgets.QMessageBox.Information)
            revealBtn = msgbox.addButton(" Reveal in folder ", QtWidgets.QMessageBox.ApplyRole)
            openBtn = msgbox.addButton("Open...", QtWidgets.QMessageBox.ActionRole)
            okBtn = msgbox.addButton("OK", QtWidgets.QMessageBox.YesRole)
            msgbox.setDefaultButton(okBtn)
            msgbox.exec_()
            if msgbox.clickedButton() == revealBtn:
                self.revealFile(self.path)
            elif msgbox.clickedButton() == openBtn:
                self.openFileInOS(self.path)
                
                
    def openFileInOS(self, filepath):
        # https://stackoverflow.com/a/435669
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', filepath))
        elif platform.system() == 'Windows':    # Windows
            os.startfile(filepath)
        else:                                   # linux variants
            subprocess.call(('xdg-open', filepath))        
        
        
    def revealFile(self, filepath):
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', '-R', filepath))
        elif platform.system() == 'Windows':    # Windows
            subprocess.Popen(f'explorer /select,{filepath}')
        else:                                   # linux variants
            subprocess.call(('xdg-open', os.path.dirname(filepath)))
            
                
    def closeEvent(self, event):
        # close by clicking X
        # close = QtWidgets.QMessageBox.question(self, "QUIT", "All changes will be lost,\nstill wanna quit?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.No)
        # if close == QtWidgets.QMessageBox.Yes:
        #     # if user clicked yes, temrinate thread and close window
        event.accept()
        # else:
        #     event.ignore()

                 
        
        
        
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication([])
    path1 = "Test path"
    test = stdfExporter()
    # progressDisplayer()
    sys.exit(app.exec_())
    
    
