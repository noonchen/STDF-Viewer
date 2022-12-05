#
# uic_stdDebug.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 10th 2021
# -----
# Last Modified: Mon Dec 05 2022
# Modified By: noonchen
# -----
# Copyright (c) 2021 noonchen
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



import sys, os
from .ui.stdfViewer_debugUI import Ui_debugPanel
from deps.SharedSrc import *
import rust_stdf_helper

# pyqt5
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QTranslator, pyqtSignal as Signal, pyqtSlot as Slot



prefixRed = '''<span style="color:red"><b>'''
prefixGreen = '''<span style="color:green"><b>'''
prefixBlue = '''<span style="color:blue"><b>'''
suffix = '''</b></span>'''
suffix_LF = '''</b></span><br><br>'''


class flags:
    stop = False


class signal4Analyzer(QtCore.QObject):
    # get text from analyzer
    resultSignal = Signal(str)
    progressSignal = Signal(int)
    # get finish signal from analyzer
    finishSignal = Signal(bool)


class stdDebugPanel(QtWidgets.QDialog):
    def __init__(self, parent) -> None:
        super().__init__()
        self.dbgUI = Ui_debugPanel()
        self.dbgUI.setupUi(self)
        self.parent = parent
        self.translator = QTranslator(self)
        self.translator_code = QTranslator(self)
        self.readingInProgress = False
        # connect signals
        self.signals = signal4Analyzer()
        self.signals.resultSignal.connect(self.updateResult)
        self.signals.progressSignal.connect(self.updateProgress)
        self.signals.finishSignal.connect(self.finishAnalyze)
        # connect btns
        self.dbgUI.readerBtn.clicked.connect(self.onRecordAnalyzer)
        self.dbgUI.logBtn.clicked.connect(self.onLogDisplay)
        self.dbgUI.saveBtn.clicked.connect(self.onSave)
        self.dbgUI.ExitBtn.clicked.connect(self.close)
        
        
    def showUI(self):
        self.dbgUI.textBrowser.clear()
        self.exec_()
                
    
    def onRecordAnalyzer(self):
        f, _typ = QFileDialog.getOpenFileName(self, caption=self.tr("Select a STD File To Analyze"),
                                              directory=getSetting().recentFolder,
                                              filter=self.tr(FILE_FILTER),)
            
        if os.path.isfile(f):
            # store folder path
            updateRecentFolder(f)
            self.updateResult(self.tr("{0}Selected STD File Path: {1}").format(prefixBlue, suffix))
            self.updateResult("{0}{1}{2}".format(prefixGreen, f, suffix))
            self.updateResult(self.tr("{0}Reading...{1}").format(prefixBlue, suffix))
            self.updateResult(self.tr("{0}##### Report Start #####{1}").format(prefixBlue, suffix))
            
            self.readThread = QtCore.QThread(parent=self)
            self.analyzer = RecordAnalyzerWrapper(f, self.signals)
            # self.analyzer.analyzeBegin()
            self.analyzer.moveToThread(self.readThread)
            self.readThread.started.connect(self.analyzer.analyzeBegin)
            self.readThread.start()
            self.readingInProgress = True
            
            
    @Slot(str)
    def updateResult(self, text):
        self.dbgUI.textBrowser.append(text)
        sbar = self.dbgUI.textBrowser.verticalScrollBar()
        sbar.setValue(sbar.maximum())
    
    
    @Slot(int)
    def updateProgress(self, progress):
        self.dbgUI.progressBar.setValue(progress)
    
    
    @Slot(bool)
    def finishAnalyze(self, finished):
        self.readingInProgress = not finished
        self.updateResult(self.tr("{0}##### Report End #####{1}").format(prefixBlue, suffix_LF))
        self.readThread.quit()
        self.readThread.wait()
    
    
    def onLogDisplay(self):
        logFolder = sys.LOG_PATH
        allLogFiles = sorted([os.path.join(logFolder, f)
                              for f in os.listdir(logFolder)
                              if f.endswith('.log') and os.path.isfile(os.path.join(logFolder, f))])
        # loop thru log files and display their contents
        for i, logPath in enumerate(allLogFiles):
            logName = os.path.basename(logPath)
            self.updateResult(self.tr("{0}##### Log Content of [{1}] {2} Start #####{3}").format(prefixBlue, i+1, logName, suffix))
            with open(logPath, "r") as logf:
                for line in logf.readlines():
                    if "ERROR" in line or "Error" in line:
                        self.updateResult("{0}{1}{2}".format(prefixRed, line, suffix))
                    else:
                        self.updateResult(line)
            self.updateResult(self.tr("{0}##### Log Content of [{1}] {2} End #####{3}").format(prefixBlue, i+1, logName, suffix_LF))
        
        
    def onSave(self):
        outPath, _ = QFileDialog.getSaveFileName(None, caption=self.tr("Save Content As"), filter=self.tr("Text file (*.txt)"))
        if outPath:
            with open(outPath, "w") as f:
                f.write(self.dbgUI.textBrowser.toPlainText())
                
            showCompleteMessage(self.tr, outPath)

            
    def closeEvent(self, event):
        if self.readingInProgress:
            close = QMessageBox.question(self, self.tr("QUIT"), 
                                         self.tr("You need to stop analyzing before closing, stop now?"), 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if close == QMessageBox.StandardButton.Yes:
                # if user clicked yes, change thread flag and close window
                self.analyzer.flag.stop = True
            
        else:
            self.dbgUI.textBrowser.clear()
            self.dbgUI.progressBar.setValue(0)
            event.accept()
        
        

class RecordAnalyzerWrapper(QtCore.QObject):
    def __init__(self, stdPath:str, QSignal:signal4Analyzer):
        super().__init__()
        self.parseStatus = True     # default success
        if (QSignal is None or
            QSignal.resultSignal is None or
            QSignal.progressSignal is None or
            QSignal.finishSignal is None):
            raise ValueError("Qsignal is invalid, parse is terminated")
        
        self.stdPath = stdPath
        self.QSignals = QSignal
        self.resultSignal = self.QSignals.resultSignal
        self.progressSignal = self.QSignals.progressSignal
        self.finishSignal = self.QSignals.finishSignal
        self.flag = flags()     # used for stopping parser
        
        
    @Slot()
    def analyzeBegin(self):
        try:
            rust_stdf_helper.analyzeSTDF(self.stdPath, self.resultSignal, self.progressSignal, self.flag)
            if self.flag.stop:
                # user terminated
                if self.resultSignal: self.resultSignal.emit(self.tr("### User terminated ###\n"))
                
        except Exception as e:
            if self.resultSignal: self.resultSignal.emit(self.tr("### Error occurred: {0} ###\n").format(repr(e)))
            
        finally:
            if self.finishSignal: self.finishSignal.emit(True)
    
