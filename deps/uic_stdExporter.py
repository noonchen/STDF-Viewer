#
# uic_stdExporter.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 11th 2020
# -----
# Last Modified: Thu Nov 04 2021
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
import os, io
from enum import IntEnum
from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet
import subprocess, platform, logging
# pyqt5
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractItemView, QFileDialog
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QTranslator
from .ui.stdfViewer_exportUI import Ui_exportUI
from .ui.stdfViewer_loadingUI import Ui_loadingUI
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

    
class tab(IntEnum):
    DUT = 0
    Trend = 1   # Do not change
    Histo = 2   # Int number
    Bin = 3     # of these items
    Wafer = 4   # It should match tab order of the main window
    Stat = 5
    FileInfo = 6


class sv:
    '''static variables'''
    # file info
    finfoRow     = 0
    finfoCol     = 0
    
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


def get_png_size(image: io.BytesIO):
    '''http://coreygoldberg.blogspot.com/2013/01/python-verify-png-file-and-get-image.html '''
    image.seek(0)
    data = image.read(24)
    image.seek(0, 2)    # restore position
    
    if data[:8] == b'\211PNG\r\n\032\n'and (data[12:16] == b'IHDR'):
        # is png
        width = int.from_bytes(data[16:20], byteorder="big")
        height = int.from_bytes(data[20:24], byteorder="big")
        return (width, height)
    else:
        raise TypeError("Input is not a PNG image")


def ceil(n):
    return int(-1 * n // 1 * -1)


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
    prepareDataSignal = Signal(int)    # test_num
    retrieveImageSignal = Signal(int, int, int, int)     # head, site, test_num, chartType
    retrieveDataListSignal = Signal(int, dict)      # chartType, {site, test_num} / {site, bin} / {site, test_num, RawData}
    retrieveTableDataSignal = Signal(int)           # FileInfo table
    retrieveDutSummarySignal = Signal(list, list, dict)   # selected heads, selected sites, {test_num}, get dut info or dut test data
    
    
    
class reportGenerator(QtCore.QObject):
    def __init__(self, signals:signals, mutex:QtCore.QMutex, conditionWait:QtCore.QWaitCondition, settings:tuple, channel:dataChannel):
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
        
    
    def waitForImage(self, head, site, test_num, chartType):
        # pause thread until the data is received from gui thread
        self.mutex.lock()
        self.retrieveImageSignal.emit(head, site, test_num, chartType)
        self.condWait.wait(self.mutex)      # self.mutex is unlocked here
        self.mutex.unlock()
        # by the time the thread is waked, the data is already published in imageChannel in mainthread
        return self.channel.imageChannel
            
            
    def waitForDataList(self, chartType, kargs):
        # pause thread until the data is received from gui thread
        self.mutex.lock()
        self.retrieveDataListSignal.emit(chartType, kargs)

        self.condWait.wait(self.mutex)
        self.mutex.unlock()
        # same as waitForImage
        return self.channel.dataListChannel
    
    
    def waitForTableData(self, conType):
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
            
        
    @Slot()
    def generate_report(self):
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
                    
        sendProgress = lambda loopCnt: self.progressBarSignal.emit(int(10000 * loopCnt/self.totalLoopCnt))
        
        # test if the filepath is writable
        try:
            test_f = open(self.path, "ab+")
            test_f.close()
        except Exception as e:
            self.msgSignal.emit("Error@@@" + repr(e))
            self.closeSignal.emit(True)
            return
            
        with Workbook(self.path) as wb:
            centerStyle = wb.add_format({"align": "center", "valign": "vjustify"})
            failedStyle = wb.add_format({"align": "center", "valign": "vjustify", "bg_color": "#CC0000", "bold": True})
            # style with newline
            txWrapStyle = wb.add_format({"align": "center", "valign": "vjustify"})
            txWrapStyle.set_text_wrap()
            # header for thrend/histo
            header_stat = [self.tr("Test Number / Site"), self.tr("Test Name"), self.tr("Unit"), self.tr("Low Limit"), 
                           self.tr("High Limit"), self.tr("Fail Count"), self.tr("Cpk"), self.tr("Average"), 
                           self.tr("Median"), self.tr("St. Dev."), self.tr("Min"), self.tr("Max")]
            sheetDict = {}
            loopCnt = 0     # used for representing generation progress
            sv.init_variables()
            '''
            1. create sheets for each selected contents, create a dict to fetch the sheet object.
            2. write the contents that don't relay on the test numbers: file header, bin, wafer, dut summary (dut info part)
            3. loop thru test numbers, prepare the test data, write dut summary (test data part), then loop thru site & head to get trend/histo images
            '''
            for cont in [tab.FileInfo, tab.DUT, tab.Stat, tab.Trend, tab.Histo, tab.Bin, tab.Wafer]:
                # sheet order in the xlsx is fixed
                sheetName = ""
                if   cont == tab.FileInfo:  sheetName = self.tr("File Info")
                elif cont == tab.DUT:       sheetName = self.tr("DUT Summary")
                elif cont == tab.Stat:      sheetName = self.tr("Test Statistics")
                elif cont == tab.Trend:     sheetName = self.tr("Trend Chart")
                elif cont == tab.Histo:     sheetName = self.tr("Histogram")
                elif cont == tab.Bin:       sheetName = self.tr("Bin Chart")
                elif cont == tab.Wafer:     sheetName = self.tr("Wafer Map")
                if cont in self.contL:      sheetDict[cont] = wb.add_worksheet(sheetName)
            
            # ** write contents independent of test numbers
            # file info
            if tab.FileInfo in self.contL:
                # Sheet for file information
                FileInfoSheet:Worksheet = sheetDict[tab.FileInfo]
                headerLabels = [self.tr("Property Name"), self.tr("Value")]
                col_width = [len(s) for s in headerLabels]
                
                FileInfoSheet.write_row(sv.finfoRow, sv.finfoCol, headerLabels, centerStyle)
                sv.finfoRow += 1
                data = self.waitForTableData(tab.FileInfo)
                                        
                for row in data:
                    if self.forceQuit: return
                    write_row_col(FileInfoSheet, sv.finfoRow, sv.finfoCol, row, centerStyle, writeRow=True)
                    col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(row)]
                    sv.finfoRow += 1
                    
                loopCnt += 1
                sendProgress(loopCnt)
                [FileInfoSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                
            # dut summary (dut part)
            if tab.DUT in self.contL:
                # Sheet for DUT summary & Test raw data
                DutSheet:Worksheet = sheetDict[tab.DUT]
                headerLabelList = [["", self.tr("Part ID"), self.tr("Test Head - Site"), self.tr("Tests Executed"), self.tr("Test Time"), self.tr("Hardware Bin"), self.tr("Software Bin"), self.tr("Wafer ID"), "(X, Y)", self.tr("DUT Flag")],
                                    [self.tr("Test Number")],
                                    [self.tr("Upper Limit")],
                                    [self.tr("Lower Limit")],
                                    [self.tr("Unit")]]
                col_width = [len(s) for s in headerLabelList[0]]
                col_width[0] = max([len(row[0]) for row in headerLabelList])
                
                # write headers
                for h in headerLabelList:
                    DutSheet.write_row(sv.dutRow, sv.dutCol, h, centerStyle)
                    sv.dutRow += 1
                # write DUT info
                DutInfoList = self.waitForDutSummary(self.headL, self.siteL, {})    # 2d, row: dut info of a dut, col: [id, site, ...]
                for count, infoRow in enumerate(DutInfoList):
                    L = ["#%d" % (count+1)] + infoRow
                    cellStyle = failedStyle if infoRow[-1].startswith("F") else centerStyle     # the last element is dut status: "Failed / 0x08" or "Passed / 0x00"
                    write_row_col(DutSheet, sv.dutRow, sv.dutCol, L, cellStyle, writeRow=True)
                    col_width = [col_width[col] if col_width[col]>len(s) else len(s) for col, s in enumerate(L)]
                    sv.dutRow += 1
                    
                loopCnt += 1
                sendProgress(loopCnt)
                [DutSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
                # set current col to the last empty column
                sv.dutCol = len(headerLabelList[0])
            
            # bin sheet
            if tab.Bin in self.contL:
                # Sheet for bin distribution
                BinSheet:Worksheet = sheetDict[tab.Bin]
                extractData = lambda L: [ele if ind == 0 else ele[0] for ind, ele in enumerate(L)]  # discard bin number (ele[1])
                col_width = []
                for head in self.headL:
                    for site in self.siteL:
                        if self.forceQuit: return
                        # get bin image from GUI thread and insert to the sheet
                        image_io = self.waitForImage(head=head, site=site, test_num=0, chartType=tab.Bin)
                        image_width, image_height = get_png_size(image_io)
                        # rescale the width of the image to 12 inches
                        bin_scale = 12 / (image_width / 200)  # inches = pixel / dpi
                        BinSheet.insert_image(sv.binRow, 0, "", {'x_scale': bin_scale, 'y_scale': bin_scale, 'image_data': image_io})
                        sv.binRow += ceil((image_height / 200) * bin_scale / 0.21)
                        # get hard bin list
                        dataList_HB = extractData(self.waitForDataList(tab.Bin, {"head": head, "site": site, "bin": "HBIN"}))
                        BinSheet.write_row(sv.binRow, 0, dataList_HB, txWrapStyle)
                        col_width = [max([len(s) for s in s.split("\n")]) if col_width[col:col+1] == [] or max([len(s) for s in s.split("\n")]) > col_width[col] else col_width[col] for col, s in enumerate(dataList_HB)]
                        sv.binRow += 1
                        # get soft bin list
                        dataList_SB = extractData(self.waitForDataList(tab.Bin, {"head": head, "site": site, "bin": "SBIN"}))
                        BinSheet.write_row(sv.binRow, 0, dataList_SB, txWrapStyle)
                        col_width = [max([len(s) for s in s.split("\n")]) if col_width[col:col+1] == [] or max([len(s) for s in s.split("\n")]) > col_width[col] else col_width[col] for col, s in enumerate(dataList_SB)]
                        sv.binRow += 3
                        
                        loopCnt += 1
                        sendProgress(loopCnt)
                [BinSheet.set_column(col, col, width*1.1) for col, width in enumerate(col_width)]
            
            # wafer sheet
            if tab.Wafer in self.contL:
                # Sheet for wafer map
                WaferSheet:Worksheet = sheetDict[tab.Wafer]

                for wafer in self.numWafer:
                    for head in self.headL:
                        for site in self.siteL:
                            if self.forceQuit: return
                            image_io = self.waitForImage(head=head, site=site, test_num=wafer, chartType=tab.Wafer)
                            image_width, image_height = get_png_size(image_io)
                            # rescale the width of the image to 12 inches
                            wafer_scale = 12 / (image_width / 200)  # inches = pixel / dpi
                            WaferSheet.insert_image(sv.waferRow, 0, "", {'x_scale': wafer_scale, 'y_scale': wafer_scale, 'image_data': image_io})
                            sv.waferRow += ceil((image_height / 200) * wafer_scale / 0.21) + 2
                            
                            loopCnt += 1
                            sendProgress(loopCnt)
                    sv.waferRow += 3
            
            # ** write contents related to test numbers
            trend_col_width = [len(s) for s in header_stat]
            histo_col_width = [len(s) for s in header_stat]
            stat_col_width = [len(s) for s in header_stat]
            hasStatHeader = False
            
            for test_num in self.numL:
                # prepare data (all sites all heads)
                self.prepareDataSignal.emit(test_num)
                
                # if dut summary is selected
                if tab.DUT in self.contL:
                    DutSheet:Worksheet = sheetDict[tab.DUT]
                    #append test raw data to the last column
                    max_width = 0
                    test_data_list, test_stat_list = self.waitForDutSummary(self.headL, self.siteL, {"test_num": test_num})
                    data_style_list = [centerStyle if stat else failedStyle for stat in test_stat_list]
                    write_row_col(DutSheet, 0, sv.dutCol, test_data_list, data_style_list, writeRow=False)
                    max_width = max([len(s) for s in test_data_list])
                    DutSheet.set_column(sv.dutCol, sv.dutCol, max_width*1.1)
                    sv.dutCol += 1
                    # loop cnt + 1 at the end
                    loopCnt += 1
                    sendProgress(loopCnt)
                
                for head in self.headL:
                    for site in self.siteL:
                        if self.forceQuit: return
                                                
                        # if Trend is selected
                        if tab.Trend in self.contL:
                            # Sheet for trend plot and test data
                            TrendSheet:Worksheet = sheetDict[tab.Trend]
                            # get image and stat from main thread
                            image_io = self.waitForImage(head, site, test_num, tab.Trend)
                            image_width, image_height = get_png_size(image_io)
                            # rescale the width of the image to 12 inches
                            trend_scale = 12 / (image_width / 200)  # inches = pixel / dpi
                            dataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "test_num": test_num})
                            # insert into the work sheet
                            TrendSheet.insert_image(sv.trendRow, 0, "", {'x_scale': trend_scale, 'y_scale': trend_scale, 'image_data': image_io})
                            sv.trendRow += ceil((image_height / 200) * trend_scale / 0.21)
                            TrendSheet.write_row(sv.trendRow, 0, header_stat, centerStyle)
                            sv.trendRow += 1
                            write_row_col(TrendSheet, sv.trendRow, 0, dataList, centerStyle, writeRow=True)
                            trend_col_width = [trend_col_width[col] if trend_col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
                            sv.trendRow += 2
                            # loop cnt + 1 at the end
                            loopCnt += 1
                            sendProgress(loopCnt)
                        
                        # if histo is selected
                        if tab.Histo in self.contL:
                            # Sheet for histogram plot and test data
                            HistoSheet:Worksheet = sheetDict[tab.Histo]
                            #
                            image_io = self.waitForImage(head, site, test_num, tab.Histo)
                            dataList = self.waitForDataList(tab.Histo, {"head": head, "site": site, "test_num": test_num})
                            #
                            image_width, image_height = get_png_size(image_io)
                            # rescale the width of the image to 12 inches
                            histo_scale = 12 / (image_width / 200)  # inches = pixel / dpi
                            HistoSheet.insert_image(sv.histoRow, 0, "", {'x_scale': histo_scale, 'y_scale': histo_scale, 'image_data': image_io})
                            sv.histoRow += ceil((image_height / 200) * histo_scale / 0.21)
                            HistoSheet.write_row(sv.histoRow, 0, header_stat, centerStyle)
                            sv.histoRow += 1
                            write_row_col(HistoSheet, sv.histoRow, 0, dataList, centerStyle, writeRow=True)
                            histo_col_width = [histo_col_width[col] if histo_col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
                            sv.histoRow += 2
                            # loop cnt + 1 at the end
                            loopCnt += 1
                            sendProgress(loopCnt)
                        
                        # if stat is selected
                        if tab.Stat in self.contL:
                            # Sheet for statistics of test items, e.g. cpk, mean, etc.
                            StatSheet:Worksheet = sheetDict[tab.Stat]
                            if not hasStatHeader:
                                StatSheet.write_row(sv.statRow, 0, header_stat, centerStyle)
                                sv.statRow += 1
                                hasStatHeader = True    # avoid duplicated header
                                
                            dataList = self.waitForDataList(tab.Trend, {"head": head, "site": site, "test_num": test_num})
                            write_row_col(StatSheet, sv.statRow, 0, dataList, centerStyle, writeRow=True)
                            stat_col_width = [stat_col_width[col] if stat_col_width[col]>len(s) else len(s) for col, s in enumerate(dataList)]
                            sv.statRow += 1
                            # loop cnt + 1 at the end
                            loopCnt += 1
                            sendProgress(loopCnt)
                        
                # we can safely modify these constants without if statement checking
                sv.trendRow += 2     # add gap between different test items
                sv.histoRow += 2     # add gap between different test items
                sv.statRow += 1     # add gap between different test items
            
            if tab.Trend in self.contL: [TrendSheet.set_column(col, col, width*1.1) for col, width in enumerate(trend_col_width)]
            if tab.Histo in self.contL: [HistoSheet.set_column(col, col, width*1.1) for col, width in enumerate(histo_col_width)]
            if tab.Stat in self.contL: [StatSheet.set_column(col, col, width*1.1) for col, width in enumerate(stat_col_width)]
        
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
        self.thread = QtCore.QThread(parent=self)
        # for sharing data between threads
        self.channel = dataChannel()
        
        self.setWindowTitle(self.tr("Generating XLSX report..."))
        self.UI.progressBar.setMaximum(10000)
        self.signals = signals()
        self.signals.msgSignal.connect(self.showMsg)
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
        
        self.rg.moveToThread(self.thread)
        self.thread.started.connect(self.rg.generate_report)
        self.thread.start()
        # self.rg.generate_report()
        self.exec_()
        
        
    def closeEvent(self, event):
        if self.closeEventByThread:
            event.accept()
        else:
            # close by clicking X
            close = QtWidgets.QMessageBox.question(self, self.tr("QUIT"), self.tr("Report is not finished,\nwanna terminate the process?"), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, defaultButton=QtWidgets.QMessageBox.No)
            if close == QtWidgets.QMessageBox.Yes:
                # if user clicked yes, temrinate thread and close window
                self.rg.forceQuit = True
                self.thread.quit()
                # self.thread.wait()
                event.accept()
            else:
                event.ignore()
             
                    
    @Slot(str)
    def showMsg(self, msg:str):
        msgType, msgContent = msg.split("@@@")
        if msgType == "Error":
            self.errorOccured = True
            QtWidgets.QMessageBox.critical(self, msgType, msgContent)
            logger.critical(msgContent)
        elif msgType == "Warning":
            QtWidgets.QMessageBox.warning(self, msgType, msgContent)
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
            self.thread.quit()
            self.thread.wait()
            self.close()


    @Slot(int)
    def prepareData(self, test_num):
        # print_thread("prepareData")
        self.parent().parent.prepareData([test_num])
    
    
    @Slot(int, int, int, int)
    def getImageFromParentMethod(self, head, site, test_num, chartType):
        '''
        Lessons:
        1. Never access GUI objects from another thread, it will raise a segfault which is nearly not debuggable.
        2. use signal to transfer the data back to the thread might not be a great practice when the thread needs
        the data immediately, because the executaion of slot is not determinable. Use a shared class instead.
        3. the mutex.lock() is used for preventing wakeAll() is called before wait().
        '''
        self.channel.imageChannel = self.parent().parent.genPlot(head, site, test_num, chartType, exportImg=True)
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
        # self.exportUI = uic.loadUi('ui/stdfViewer_exportUI.ui', self)    # uic
        self.exportUI = Ui_exportUI()
        self.exportUI.setupUi(self)
        self.parent = parent
        self.translatorUI = QTranslator(self)
        self.translatorCode = QTranslator(self)
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
        self.exportUI.nextBtn.clicked.connect(self.gotoNextPage)
        self.exportUI.previousBtn.clicked.connect(self.gotoPreviousPage)
        
        self.exportUI.Trend_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Histo_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Bin_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Stat_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.DUT_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.FileInfo_cb.clicked.connect(self.changeBtnStyle)
        self.exportUI.Wafer_cb.clicked.connect(self.changeBtnStyle)
        
                
    def showUI(self):
        self.closeEventByThread = False    # used to determine the source of close event
        # init UI
        self.exportUI.stackedWidget.setCurrentIndex(0)
        self.exportUI.previousBtn.setDisabled(True)
        self.previousPageIndex = 0
        # get all test items from mainUI
        self.remainTestItems = self.parent.completeTestList      # mutable
        self.AllTestItems = tuple(self.remainTestItems)     # immutable
        self.initSiteCBs()
        self.initTestItems()
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
    
    
    def changeBtnStyle(self):
        changeToConfirm = False
        currentPage = self.exportUI.stackedWidget.currentIndex()
        
        if currentPage == 0:
            # change to "Confirm" only if file info is selected
            if self.getSelectedContents() == [tab.FileInfo]:
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
            self.exportUI.nextBtn.setText(QtCore.QCoreApplication.translate("exportUI", "Confirm"))
        
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
            self.exportUI.nextBtn.setText(QtCore.QCoreApplication.translate("exportUI", "Next >"))
    
    
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
                QtWidgets.QMessageBox.warning(self, self.tr("Warning"), self.tr("Output directory is invalid, not writable or not existed\n"))
                return
            
            selectedContents = self.getSelectedContents()
            if len(set(selectedContents) & {tab.Trend, tab.Histo, tab.DUT, tab.Stat}) > 0:
                # go to test page
                self.previousPageIndex = 0
                self.exportUI.previousBtn.setEnabled(True)
                self.exportUI.stackedWidget.setCurrentIndex(1)
                
            elif len(set(selectedContents) & {tab.Bin, tab.Wafer}) > 0:
                # go to site page
                self.previousPageIndex = 0
                self.exportUI.previousBtn.setEnabled(True)
                self.exportUI.stackedWidget.setCurrentIndex(2)
                self.changeBtnStyle()
                
            else:
                # only file info is selected
                self.start()
        
        elif currentPage == 1:
            # test page
            testCount = len(self.getExportTestNums())
            if testCount > 0 or (testCount == 0 and len(set(self.getSelectedContents()) & {tab.Trend, tab.Histo, tab.Stat}) == 0):
                # go to site page
                self.previousPageIndex = 1
                self.exportUI.previousBtn.setEnabled(True)
                self.exportUI.stackedWidget.setCurrentIndex(2)
                self.changeBtnStyle()
            else:
                QtWidgets.QMessageBox.warning(self, self.tr("Warning"), self.tr("At least one test item should be selected if Trend/Histo/Statistic is checked\n"))
                return
        
        else:
            # site page
            headList, siteList = self.getHeads_Sites()
            if len(headList) == 0 or len(siteList) == 0: 
                QtWidgets.QMessageBox.warning(self, self.tr("Warning"), self.tr("Head and Site cannot be empty\n"))
            else:
                # start exporting
                self.start()
    
    
    def start(self):
        self.numL = self.getExportTestNums()
        self.headL, self.siteL = self.getHeads_Sites()
        self.contL = self.getSelectedContents()
        self.path = self.getOutPath()
        self.numWafer = sorted([-1 if item.split("\t")[0] == "-" else int(item.split("\t")[0].strip("#")) for item in self.parent.completeWaferList])
        if len(self.numWafer) < 2:
            # only default stacked wafer is in list, no actual wafer data exists
            self.numWafer = []
       
        # report generation code here
        self.totalLoopCnt = 0
        if tab.Trend in self.contL:     self.totalLoopCnt += len(self.numL) * len(self.siteL) * len(self.headL)
        if tab.Histo in self.contL:     self.totalLoopCnt += len(self.numL) * len(self.siteL) * len(self.headL)
        if tab.Stat in self.contL:      self.totalLoopCnt += len(self.numL) * len(self.siteL) * len(self.headL)
        if tab.Bin in self.contL:       self.totalLoopCnt += len(self.siteL) * len(self.headL)
        if tab.FileInfo in self.contL:  self.totalLoopCnt += 1
        if tab.DUT in self.contL:       self.totalLoopCnt += (1 + len(self.numL))   # dut info part + test part
        if tab.Wafer in self.contL:     self.totalLoopCnt += len(self.numWafer) * len(self.siteL) * len(self.headL)
                    
        self.pd = progressDisplayer(parent=self)
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
            
        msgbox = QtWidgets.QMessageBox(None)
        msgbox.setText(title)
        msgbox.setInformativeText('%s\n\n%s\n'%(msg, self.path))
        msgbox.setIcon(QtWidgets.QMessageBox.Information)
        revealBtn = msgbox.addButton(self.tr(" Reveal in folder "), QtWidgets.QMessageBox.ApplyRole)
        openBtn = msgbox.addButton(self.tr("Open..."), QtWidgets.QMessageBox.ActionRole)
        okBtn = msgbox.addButton(self.tr("OK"), QtWidgets.QMessageBox.YesRole)
        msgbox.setDefaultButton(okBtn)
        msgbox.exec_()
        if msgbox.clickedButton() == revealBtn:
            self.revealFile(self.path)
        elif msgbox.clickedButton() == openBtn:
            self.openFileInOS(self.path)
                
                
    def openFileInOS(self, filepath):
        # https://stackoverflow.com/a/435669
        filepath = os.path.normpath(filepath)   # fix slash orientation in different OSs
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', filepath))
        elif platform.system() == 'Windows':    # Windows
            subprocess.call(f'cmd /c start "" "{filepath}"', creationflags = \
                subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
        else:                                   # linux variants
            subprocess.call(('xdg-open', filepath))
        
        
    def revealFile(self, filepath):
        filepath = os.path.normpath(filepath)
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', '-R', filepath))
        elif platform.system() == 'Windows':    # Windows
            subprocess.call(f'explorer /select,"{filepath}"', creationflags = \
                subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
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
    
    
