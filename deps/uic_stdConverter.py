#
# uic_stdXlsxConverter.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: Dec 12 2022
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


import os
# pyqt5
from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog
from PyQt5.QtCore import (QTranslator, QThread, 
                          QObject, 
                          pyqtSignal as Signal, 
                          pyqtSlot as Slot)
from .ui.stdfViewer_convertUI import Ui_ConvertUI
from .SharedSrc import FILE_FILTER, showCompleteMessage

class flags:
    stop = False


class signal4Converter(QObject):
    progressBarSignal = Signal(int)
    finishMsgSignal = Signal(tuple)    # (hasErr?, errMsg, outPath)


class StdfConverter(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.translator = QTranslator(self)
        self.closeEventByThread = False    # used to determine the source of close event
        self.extOut = ""
        self.c = None
        self.convertFunc = None
        
        self.signals = signal4Converter()
        self.signals.progressBarSignal.connect(self.updateProgressBar)
        self.signals.finishMsgSignal.connect(self.cleanUp)
        
        self.convertUI = Ui_ConvertUI()
        self.convertUI.setupUi(self)
        self.convertUI.progressBar.setMaximum(100)
        
        self.convertUI.start.clicked.connect(self.convert)
        self.convertUI.cancel.clicked.connect(self.cancel)
        self.convertUI.stdf_in_btn.clicked.connect(self.openFileDialog)
        self.convertUI.convert_out_btn.clicked.connect(self.saveFileDialog)
        
    def setupConverter(self, title: str, groupName: str, extOut: str, convertFunc):
        self.setWindowTitle(title)
        self.convertUI.convert_out.setTitle(groupName)
        self.extOut = extOut
        self.convertFunc = convertFunc
    
    def openFileDialog(self):
        pathIn, _  = QFileDialog.getOpenFileName(None, caption=self.tr("Select a STDF File To Convert"),
                                                 filter=self.tr(FILE_FILTER))
        if pathIn:
            self.convertUI.stdf_in_text.setPlainText(pathIn)
    
    def saveFileDialog(self):
        pathOut, _  = QFileDialog.getSaveFileName(None, caption=self.tr("Convert To"))
        if pathOut:
            self.convertUI.convert_out_text.setPlainText(pathOut + self.extOut)
    
    def getPaths(self):
        pathIn = self.convertUI.stdf_in_text.toPlainText()
        pathOut = self.convertUI.convert_out_text.toPlainText()
        return (pathIn, pathOut)
    
    def showUI(self):
        self.closeEventByThread = False
        self.convertUI.progressBar.setFormat("")
        self.convertUI.progressBar.setValue(0)        
        self.exec()
    
    def convert(self):
        pathIn, pathOut = self.getPaths()
        
        if os.path.isfile(pathIn) and os.access(os.path.dirname(pathOut) , os.W_OK):
            self.workThread = QThread(parent=self)
            self.c = ConverterWrapper(pathIn, pathOut, self.convertFunc, self.signals)
            self.c.moveToThread(self.workThread)
            self.workThread.started.connect(self.c.startConvertion)
            self.workThread.start()
        else:
            QMessageBox.warning(self, self.tr("Warning"), 
                                self.tr("Input invalid or output directory is not writable\n"))
    
    def cancel(self):
        '''
        cancel the convertion if it's in progress
        otherwise close window
        '''
        if self.c and self.c.converting:
            close = QMessageBox.question(self, "QUIT", "Are you sure want to stop reading?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if close == QMessageBox.StandardButton.Yes:
                self.c.flag.stop = True
        else:
            self.close()
    
    def closeEvent(self, event):
        '''
        same as cancel
        '''
        if self.c and self.c.converting:
            self.cancel()
            event.ignore()
        else:
            event.accept()

    @Slot(int)
    def updateProgressBar(self, num: int):
        self.convertUI.progressBar.setFormat(f"{num}%")
        self.convertUI.progressBar.setValue(num)
        
    @Slot(tuple)
    def cleanUp(self, finishMsg: tuple):
        self.workThread.quit()
        self.workThread.wait()
        hasErr, errMsg, pathOut = finishMsg
        if hasErr:
            title = self.tr("Error occurred")
            msg = self.tr("{}, report path:").format(errMsg)
        elif self.c.aborted:
            title = self.tr("Process Aborted!")
            msg = self.tr("Partial report is saved in:")
        else:
            title = self.tr("Export completed!")
            msg = self.tr("Report path:")        
            
        self.c = None
        showCompleteMessage(self.tr, 
                            pathOut, 
                            title, 
                            '%s\n\n%s\n'%(msg, pathOut), 
                            QMessageBox.Icon.Information)
        
        
class ConverterWrapper(QObject):
    def __init__(self, stdPath:str, outPath: str, convertFunc, QSignal: signal4Converter):
        super().__init__()
        if (QSignal is None or
            QSignal.progressBarSignal is None or
            QSignal.finishMsgSignal is None):
            raise ValueError("Qsignal is invalid, parse is terminated")
        
        self.converting = False
        self.aborted = False
        self.stdPath = stdPath
        self.outPath = outPath
        self.convertFunc = convertFunc
        self.QSignals = QSignal
        self.progressSignal = self.QSignals.progressBarSignal
        self.finishMsgSignal = self.QSignals.finishMsgSignal
        self.flag = flags()
        
    @Slot()
    def startConvertion(self):
        try:
            self.converting = True
            self.convertFunc(self.stdPath, self.outPath, self.progressSignal, self.flag)
            self.aborted = self.flag.stop
            self.progressSignal.emit(100)
            self.finishMsgSignal.emit( (False, "", self.outPath) )
        except Exception as e:
            self.finishMsgSignal.emit( (True, repr(e), self.outPath) )
