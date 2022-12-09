#
# ChartWidgets.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 25th 2022
# -----
# Last Modified: Fri Dec 09 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
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



from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import Qt, QPoint, QRectF
import numpy as np
import pyqtgraph as pg
import pyqtgraph.functions as fn
from pyqtgraph.icons import getGraphIcon
from pyqtgraph.Point import Point
from pyqtgraph.graphicsItems.ScatterPlotItem import drawSymbol
import deps.SharedSrc as ss

pg.setConfigOptions(foreground='k', background='w', antialias=False)


def addFileLabel(parent, fid: int, yoffset = -50):
    file_text = pg.LabelItem(f"File {fid}", size="15pt", color="#000000", anchor=(1, 0))
    file_text.setParentItem(parent)
    file_text.anchor(itemPos=(1, 1), parentPos=(1, 1), offset=(0, yoffset))


class PlotMenu(QMenu):
    def __init__(self):
        QMenu.__init__(self)
        # actions
        self.restoreMode = QAction("Restore View", self)
        self.scaleMode = QAction("Scale Mode", self)
        self.panMode = QAction("Pan Mode", self)
        self.pickMode = QAction("Data Pick Mode", self)
        self.showDutData = QAction("Show Selected DUT Data", self)
        # set left mouse button mode to checkable
        self.scaleMode.setCheckable(True)
        self.panMode.setCheckable(True)
        self.pickMode.setCheckable(True)
        # set scale mode as default
        self.scaleMode.setChecked(True)
        self.addActions([self.restoreMode,
                         self.scaleMode,
                         self.panMode,
                         self.pickMode,
                         self.showDutData])
        
    def connectRestore(self, restoreMethod):
        self.restoreMode.triggered.connect(restoreMethod)
        
    def connectScale(self, scaleMethod):
        self.scaleMode.triggered.connect(scaleMethod)
        
    def connectPan(self, panMethod):
        self.panMode.triggered.connect(panMethod)
        
    def connectPick(self, pickMethod):
        self.pickMode.triggered.connect(pickMethod)
        
    def connectShowDut(self, showDutMethod):
        self.showDutData.triggered.connect(showDutMethod)
        
    def uncheckOthers(self, currentName: str):
        for n, act in [("scale", self.scaleMode), ("pan", self.panMode), ("pick", self.pickMode)]:
            if n != currentName:
                act.setChecked(False)


class GraphicViewWithMenu(pg.GraphicsView):
    def __init__(self, minWidth=800, minHeight=400):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, 
                           QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumWidth(minWidth)
        self.setMinimumHeight(minHeight)
        self.plotlayout = pg.GraphicsLayout()
        self.setCentralWidget(self.plotlayout)
        self.menu = PlotMenu()
        # storing all viewboxes for changing 
        # options
        self.view_list = []
        
    def getAllViewBox(self):
        return self.view_list
    
    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() == Qt.MouseButton.RightButton:
            ev.accept()
            self.showContextMenu(ev)
            return
        return super().mousePressEvent(ev)

    def showContextMenu(self, ev):
        # add export... from scene()
        export = self.sceneObj.contextMenu[0]
        if export not in self.menu.actions() and len(self.view_list) > 0:
            # export dialog is usually triggered from a viewbox
            # but in our case, menu is shown in GraphicView, 
            # we don't have a MouseClickEvent that contains a viewbox
            # As a workaround, manually assign a viewbox to `contextMenuItem`
            # ao that the export dialog have somethings to display
            setattr(self.sceneObj, "contextMenuItem", self.view_list[0])
            self.menu.addSeparator()
            self.menu.addAction(export)
        self.menu.popup(ev.screenPos().toPoint())
        
    def connectActions(self):
        '''
        call this func after all views are stored
        in self.view_list
        '''
        self.menu.connectRestore(self.onRestoreMode)
        self.menu.connectPan(self.onPanMode)
        self.menu.connectScale(self.onScaleMode)
        self.menu.connectPick(self.onPickMode)
    
    def onRestoreMode(self):
        for view in self.view_list:
            view.autoRange()
    
    def onScaleMode(self):
        self.menu.uncheckOthers("scale")
        for view in self.view_list:
            view.setLeftButtonAction('rect')
            view.enableWheelScale = True
            view.enablePickMode = False

    def onPanMode(self):
        self.menu.uncheckOthers("pan")
        for view in self.view_list:
            view.setLeftButtonAction('pan')
            view.enableWheelScale = False

    def onPickMode(self):
        self.menu.uncheckOthers("pick")
        for view in self.view_list:
            view.setLeftButtonAction('rect')
            view.enablePickMode = True


class StdfViewrViewBox(pg.ViewBox):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.setMenuEnabled(False)
        # scale mode is enabled by default
        # wheel scale should be enabled as well
        self.enableWheelScale = True
        self.enablePickMode = False
    
    def wheelEvent(self, ev, axis=None):
        if self.enableWheelScale:
            super().wheelEvent(ev, axis)
        else:
            ev.ignore()
    
    def mouseDragEvent(self, ev, axis=None):
        # view box handle left button only, middlebutton?
        if ev.button() not in [Qt.MouseButton.LeftButton, 
                               Qt.MouseButton.MiddleButton]:
            return
        
        ev.accept()
        pos = ev.pos()
        
        if self.state['mouseMode'] == pg.ViewBox.RectMode and axis is None:
            pixelBox = QRectF(Point(ev.buttonDownPos(ev.button())), Point(pos))
            coordBox = self.childGroup.mapRectFromParent(pixelBox)
            xrange = (coordBox.x(), coordBox.x() + coordBox.width())
            yrange = (coordBox.y(), coordBox.y() + coordBox.height())
            # Zoom mode or Pick mode
            if ev.isFinish():
                self.rbScaleBox.hide()
                if self.enablePickMode:
                    # select objects in the scale box
                    self.selectItemsWithin(xrange, yrange)
                else:
                    # zoom in rect selection
                    self.showAxRect(coordBox)
                    self.axHistoryPointer += 1
                    self.axHistory = self.axHistory[:self.axHistoryPointer] + [coordBox]
            else:
                ## update shape of scale box
                self.updateScaleBox(coordBox)
                if self.enablePickMode:
                    # highlight shapes that are contained by scale box
                    self.highlightitemsWithin(xrange, yrange)
        else:
            # Pan mode
            lastPos = ev.lastPos()
            dif = pos - lastPos
            dif = dif * -1
            ## Ignore axes if mouse is disabled
            mouseEnabled = np.array(self.state['mouseEnabled'], dtype=np.float64)
            mask = mouseEnabled.copy()
            if axis is not None:
                mask[1-axis] = 0.0

            tr = self.childGroup.transform()
            tr = fn.invertQTransform(tr)
            tr = tr.map(dif*mask) - tr.map(Point(0,0))

            x = tr.x() if mask[0] == 1 else None
            y = tr.y() if mask[1] == 1 else None
            
            self._resetTarget()
            if x is not None or y is not None:
                self.translateBy(x=x, y=y)
            self.sigRangeChangedManually.emit(self.state['mouseEnabled'])
            
    def updateScaleBox(self, coordBox):
        self.rbScaleBox.setPos(coordBox.topLeft())
        tr = QtGui.QTransform.fromScale(coordBox.width(), coordBox.height())
        self.rbScaleBox.setTransform(tr)
        self.rbScaleBox.show()    
    
    def selectItemsWithin(self, xrange: tuple, yrange: tuple):
        print("`selectItemsWithin` should be overrided", xrange, yrange)
    
    def highlightitemsWithin(self, xrange: tuple, yrange: tuple):
        print("`highlightitemsWithin` should be overrided", xrange, yrange)


class TrendViewBox(StdfViewrViewBox):
    def selectItemsWithin(self, xrange: tuple, yrange: tuple):
        print("Trend chart pick logic")
    
    def highlightitemsWithin(self, xrange: tuple, yrange: tuple):
        print("Trend chart highlight logic")


class HistoViewBox(StdfViewrViewBox):
    def selectItemsWithin(self, xrange: tuple, yrange: tuple):
        print("Histo chart pick logic")
    
    def highlightitemsWithin(self, xrange: tuple, yrange: tuple):
        print("Hisot chart highlight logic")


class BinViewBox(StdfViewrViewBox):
    def selectItemsWithin(self, xrange: tuple, yrange: tuple):
        print("Bin chart pick logic")
    
    def highlightitemsWithin(self, xrange: tuple, yrange: tuple):
        print("Bin chart highlight logic")


class WaferViewBox(StdfViewrViewBox):
    def selectItemsWithin(self, xrange: tuple, yrange: tuple):
        print("Wafer pick logic")
    
    def highlightitemsWithin(self, xrange: tuple, yrange: tuple):
        print("Wafer highlight logic")


class TrendChart(GraphicViewWithMenu):
    def __init__(self):
        super().__init__(800, 400)
        self.meanPen = pg.mkPen({"color": "orange", "width": 1})
        self.medianPen = pg.mkPen({"color": "k", "width": 1})
        self.lolimitPen = pg.mkPen({"color": "#0000ff", "width": 3.5})
        self.hilimitPen = pg.mkPen({"color": "#ff0000", "width": 3.5})
        self.lospecPen = pg.mkPen({"color": "#000080", "width": 3.5})
        self.hispecPen = pg.mkPen({"color": "#8b0000", "width": 3.5})
        self.trendData = {}
        self.validData = False
        
    def setTrendData(self, trendData: dict):
        settings = ss.getSetting()
        self.trendData = trendData
        testInfo: dict = trendData["TestInfo"]
        # testData  key: fid, 
        #           value: a dict with site number as key and value: testDataDict of this site
        testData: dict = trendData["Data"]
        # get display limit of y axis, should be 
        # the max|min of (lim, spec, data)
        y_min_list = []
        y_max_list = []
        test_num = -9999
        test_name = ""
        for fid in testData.keys():
            i_file = testInfo[fid]
            d_file = testData[fid]
            if len(i_file) == 0:
                # this file doesn't contain
                # current test, 
                continue
            test_num = i_file["TEST_NUM"]
            test_name = i_file["TEST_NAME"]
            y_min_list.extend([i_file["LLimit"], i_file["LSpec"]])
            y_max_list.extend([i_file["HLimit"], i_file["HSpec"]])
            for d_site in d_file.values():
                # TODO dynamic limits
                y_min_list.append(d_site["Min"])
                y_max_list.append(d_site["Max"])
                # at least one site data should be valid
                self.validData |= (~np.isnan(d_site["Min"]) and 
                                   ~np.isnan(d_site["Max"]))
        # validData means the valid data exists, 
        # set the flag to True and put it in top GUI
        if not self.validData:
            return
        # # if these two list is empty, means no test value
        # # is found in all files. this is is rare but I've encountered
        # if len(y_min_list) == 0 or len(y_max_list) == 0:
        #     return
        y_min = np.nanmin(y_min_list)
        y_max = np.nanmax(y_max_list)
        # add 15% as overhead
        oh = 0.15 * (y_max - y_min)
        y_min -= oh
        y_max += oh
        # it's common that y_min == y_max for FTR
        # in this case we need to manually assign y limits
        if y_min == y_max:
            y_min -= 1
            y_max += 1
        # # there is a possibility that y_min or y_max
        # # is nan, in this case we cannot draw anything
        # if np.isnan(y_min) or np.isnan(y_max):
        #     return
        # add title
        self.plotlayout.addLabel(f"{test_num} {test_name}", row=0, col=0, 
                                 rowspan=1, colspan=len(testInfo),
                                 size="20pt")
        # create same number of viewboxes as file counts
        for fid in sorted(testInfo.keys()):
            isFirstPlot = len(self.view_list) == 0
            view = TrendViewBox()
            view.setMouseMode(view.RectMode)
            # plotitem setup
            pitem = pg.PlotItem(viewBox=view)
            pitem.addLegend((0, 1), labelTextSize="12pt")
            # iterate site data and draw in a same plot item
            # if mean and median is enabled, draw them as well
            sitesData = testData[fid]
            infoDict = testInfo[fid]
            if len(sitesData) == 0 or len(infoDict) == 0:
                # skip this file if: 
                #  - test is not in this file (empty sitesData)
                #  - no data found in selected sites (test value is empty array)
                # to ensure the following operation is on valid data
                continue
            x_min_list = []
            x_max_list = []
            for site, data_per_site in sitesData.items():
                x = data_per_site["dutList"]
                y = data_per_site["dataList"]
                if len(x) == 0 or len(y) == 0:
                    # skip this site that contains 
                    # no data
                    continue
                x_min_list.append(np.nanmin(x))
                x_max_list.append(np.nanmax(x))
                fsymbol = settings.fileSymbol[fid]
                siteColor = settings.siteColor[site]
                # test value
                pdi = pg.PlotDataItem(x=x, y=y, pen=None, 
                                      symbol=fsymbol, symbolPen="k", 
                                      symbolSize=8, symbolBrush=siteColor, 
                                      name=f"Site {site}")
                pdi.scatter.opts.update(hoverable=True, 
                                        tip=f"Site {site}\nDUTIndex: {{x:.0f}}\nValue: {{y:.3g}}".format,
                                        hoverSymbol="+",
                                        hoverSize=12,
                                        hoverPen=pg.mkPen("#ff0000", width=1))
                pitem.addItem(pdi)
                # mean
                mean = data_per_site["Mean"]
                if settings.showMean_trend and ~np.isnan(mean):
                    pitem.addLine(y=mean, pen=self.meanPen, name=f"Mean_site{site}", label="x̅ = {value:0.3f}",
                                  labelOpts={"position":0.9, "color": self.meanPen.color(), "movable": True})
                # median
                median = data_per_site["Median"]
                if settings.showMed_trend and ~np.isnan(median):
                    pitem.addLine(y=median, pen=self.medianPen, name=f"Median_site{site}", label="x̃ = {value:0.3f}",
                                  labelOpts={"position":0.7, "color": self.medianPen.color(), "movable": True})
            # add test limits and specs
            for (key, name, pen, enabled) in [("LLimit", "Low Limit", self.lolimitPen, settings.showLL_trend), 
                                              ("HLimit", "High Limit", self.hilimitPen, settings.showHL_trend), 
                                              ("LSpec", "Low Spec", self.lospecPen, settings.showLSpec_trend), 
                                              ("HSpec", "High Spec", self.hispecPen, settings.showHSpec_trend)]:
                lim = infoDict[key]
                pos = 0.8 if key.endswith("Spec") else 0.2
                anchors = [(0.5, 0), (0.5, 0)] if key.startswith("L") else [(0.5, 1), (0.5, 1)]
                if enabled and ~np.isnan(lim):
                    pitem.addLine(y=lim, pen=pen, name=name, 
                                label=f"{name} = {{value:0.2f}}", 
                                labelOpts={"position":pos, "color": pen.color(), 
                                            "movable": True, "anchors": anchors})
            # labels and file id
            unit = infoDict["Unit"]
            pitem.getAxis("left").setLabel(f"Test Value" + f" ({unit})" if unit else "")
            pitem.getAxis("bottom").setLabel(f"DUTIndex")
            if len(testInfo) > 1:
                # only add if there are multiple files
                addFileLabel(pitem, fid)
            pitem.setClipToView(True)
            # set range and limits
            x_min = min(x_min_list)
            x_max = max(x_max_list)
            oh = 0.02 * (x_max - x_min)
            x_min -= oh
            x_max += oh
            # view.setAutoPan()
            view.setRange(xRange=(x_min, x_max), 
                          yRange=(y_min, y_max))
            view.setLimits(xMin=x_min, xMax=x_max,      # avoid blank area
                           yMin=y_min, yMax=y_max,
                           minXRange=2)                 # avoid zoom too deep
            # add to layout
            self.plotlayout.addItem(pitem, row=1, col=fid, rowspan=1, colspan=1)
            # link current viewbox to previous, hide axis
            # for 2nd+ plots
            if not isFirstPlot:
                pitem.getAxis("left").hide()
                view.setYLink(self.view_list[0])
            # append view for counting plots
            self.view_list.append(view)
        # set auto range for all view
        # to fix the issue that y axis not synced
        for v in self.view_list:
            v.enableAutoRange(enable=True)
        self.connectActions()


class HistoChart(TrendChart):
    def setTrendData(self, trendData: dict):
        settings = ss.getSetting()
        self.trendData = trendData
        testInfo: dict = trendData["TestInfo"]
        # testData  key: fid, 
        #           value: a dict with site number as key and value: testDataDict of this site
        testData: dict = trendData["Data"]
        # get display limit of y axis, should be 
        # the max|min of (lim, spec, data)
        y_min_list = []
        y_max_list = []
        test_num = -9999
        test_name = ""
        for fid in testData.keys():
            i_file = testInfo[fid]
            d_file = testData[fid]
            if len(i_file) == 0:
                # this file doesn't contain
                # current test, 
                continue
            test_num = i_file["TEST_NUM"]
            test_name = i_file["TEST_NAME"]
            y_min_list.extend([i_file["LLimit"], i_file["LSpec"]])
            y_max_list.extend([i_file["HLimit"], i_file["HSpec"]])
            for d_site in d_file.values():
                y_min_list.append(d_site["Min"])
                y_max_list.append(d_site["Max"])
                # at least one site data should be valid
                self.validData |= (~np.isnan(d_site["Min"]) and 
                                   ~np.isnan(d_site["Max"]))
        # validData means the valid data exists, 
        # set the flag to True and put it in top GUI
        if not self.validData:
            return
        y_min = np.nanmin(y_min_list)
        y_max = np.nanmax(y_max_list)
        # add 15% as overhead
        oh = 0.15 * (y_max - y_min)
        y_min -= oh
        y_max += oh
        # it's common that y_min == y_max for FTR
        # in this case we need to manually assign y limits
        if y_min == y_max:
            y_min -= 1
            y_max += 1
        # add title
        self.plotlayout.addLabel(f"{test_num} {test_name}", row=0, col=0, 
                                 rowspan=1, colspan=len(testInfo),
                                 size="20pt")
        # create same number of viewboxes as file counts
        for fid in sorted(testInfo.keys()):
            isFirstPlot = len(self.view_list) == 0
            view = HistoViewBox()
            view.setMouseMode(view.RectMode)
            # plotitem setup
            pitem = pg.PlotItem(viewBox=view)
            pitem.addLegend((0, 1), labelTextSize="12pt")
            # iterate site data and draw in a same plot item
            # if mean and median is enabled, draw them as well
            sitesData = testData[fid]
            infoDict = testInfo[fid]
            if len(sitesData) == 0 or len(infoDict) == 0:
                # skip this file if: 
                #  - test is not in this file (empty sitesData)
                #  - no data found in selected sites (test value is empty array)
                # to ensure the following operation is on valid data
                continue
            bar_base = 0
            # xaxis tick labels
            ticks = []
            for site, data_per_site in sitesData.items():
                x = data_per_site["dutList"]
                y = data_per_site["dataList"]
                if len(x) == 0 or len(y) == 0:
                    # skip this site that contains 
                    # no data
                    continue
                siteColor = settings.siteColor[site]
                # calculate bin edges and histo counts
                hist, bin_edges = np.histogram(y, bins=settings.binCount)
                bin_width = bin_edges[1]-bin_edges[0]
                #TODO get histo bin index (start from 1) of each dut
                # np.histogram is left-close-right-open, except the last bin
                # np.digitize should be right=False, but must remove the last bin edge to force close the rightmost bin
                bin_ind = np.digitize(y, bin_edges[:-1], right=False)
                bin_dut_dict = {}
                for ind, dut in zip(bin_ind, x):
                    bin_dut_dict.setdefault(ind, []).append(dut)
                site_name = f"Site {site}"
                # use normalized hist for better display
                hist_normalize = hist / hist.max()
                bar = pg.BarGraphItem(x0=bar_base, y0=bin_edges[:len(hist)], 
                                      width=hist_normalize, height=bin_width, 
                                      brush=siteColor, name=site_name)
                pitem.addItem(bar)
                # set the bar base of histogram of next site
                inc = 1.2
                ticks.append((bar_base + 0.5 * inc, site_name))
                bar_base += inc
                # #TODO mean
                # mean = data_per_site["Mean"]
                # if settings.showMean_trend and ~np.isnan(mean):
                #     pitem.addLine(y=mean, pen=self.meanPen, name=f"Mean_site{site}", label="x̅ = {value:0.3f}",
                #                   labelOpts={"position":0.9, "color": self.meanPen.color(), "movable": True})
                # # median
                # median = data_per_site["Median"]
                # if settings.showMed_trend and ~np.isnan(median):
                #     pitem.addLine(y=median, pen=self.medianPen, name=f"Median_site{site}", label="x̃ = {value:0.3f}",
                #                   labelOpts={"position":0.7, "color": self.medianPen.color(), "movable": True})
            # add test limits and specs
            for (key, name, pen, enabled) in [("LLimit", "Low Limit", self.lolimitPen, settings.showLL_trend), 
                                              ("HLimit", "High Limit", self.hilimitPen, settings.showHL_trend), 
                                              ("LSpec", "Low Spec", self.lospecPen, settings.showLSpec_trend), 
                                              ("HSpec", "High Spec", self.hispecPen, settings.showHSpec_trend)]:
                lim = infoDict[key]
                pos = 0.8 if key.endswith("Spec") else 0.2
                anchors = [(0.5, 0), (0.5, 0)] if key.startswith("L") else [(0.5, 1), (0.5, 1)]
                if enabled and ~np.isnan(lim):
                    pitem.addLine(y=lim, pen=pen, name=name, 
                                label=f"{name} = {{value:0.2f}}", 
                                labelOpts={"position":pos, "color": pen.color(), 
                                            "movable": True, "anchors": anchors})
            
            if len(testInfo) > 1:
                # only add if there are multiple files
                addFileLabel(pitem, fid)
            view.setRange(xRange=(0, bar_base), 
                          yRange=(y_min, y_max))
            view.setLimits(xMin=0, xMax=bar_base+0.5,
                           yMin=y_min, yMax=y_max,
                           minXRange=2)
            # add to layout
            self.plotlayout.addItem(pitem, row=1, col=fid, rowspan=1, colspan=1)
            # link current viewbox to previous, 
            # show axis but hide value 2nd+ plots
            # labels and file id
            unit = infoDict["Unit"]
            pitem.getAxis("bottom").setTicks([ticks])
            if isFirstPlot:
                pitem.getAxis("left").setLabel(test_name + f" ({unit})" if unit else "")
            else:
                pitem.getAxis("left").setStyle(showValues=False)
                view.setYLink(self.view_list[0])
            # append view for counting plots
            self.view_list.append(view)
        # set auto range for all view
        # to fix the issue that y axis not synced
        for v in self.view_list:
            v.enableAutoRange(enable=True)
        self.connectActions()


class BinChart(GraphicViewWithMenu):
    def __init__(self):
        super().__init__(800, 800)
        self.validData = False
        
    def setBinData(self, binData: dict):
        if not all([k in binData for k in ["HS", 
                                           "HBIN", "SBIN", 
                                           "HBIN_Ticks", "SBIN_Ticks"]]):
            return
        
        settings = ss.getSetting()
        self.validData = True
        row = 0
        (head, site) = binData["HS"]
        hs_info = f" - Head {head} - " + f"All Site" if site == -1 else f"Site {site}"
        # create two plot items for HBIN & SBIN
        for binType in ["HBIN", "SBIN"]:
            hsbin = binData[binType]
            binTicks = binData[binType+"_Ticks"]
            num_files = len(hsbin)
            # use a list to track viewbox count in
            # a single plot, used for Y-link and 
            # hide axis
            tmpVbList = []
            binColorDict = settings.hbinColor if binType == "HBIN" else settings.sbinColor
            # add title
            binTypeName = "Hardware Bin" if binType == "HBIN" else "Software Bin"
            self.plotlayout.addLabel(f"{binTypeName}{hs_info}", 
                                     row=row, col=0, 
                                     rowspan=1, colspan=num_files, 
                                     size="20pt")
            row += 1
            # iterate thru all files
            for fid in sorted(hsbin.keys()):
                isFirstPlot = len(tmpVbList) == 0
                view_bin = BinViewBox()
                view_bin.invertY(True)
                pitem = pg.PlotItem(viewBox=view_bin)
                binStats = hsbin[fid]
                # get data for barGraph
                numList = sorted(binTicks.keys())
                cntList = [binStats.get(n, 0) for n in numList]
                colorList = [binColorDict[n] for n in numList]
                # draw horizontal bars, use `ind` instead of `bin_num` as y
                bar = pg.BarGraphItem(x0=0, y=np.arange(len(numList)), width=cntList, height=0.8, brushes=colorList)
                pitem.addItem(bar)
                # set ticks to y
                ticks = [[binTicks[n] for n in numList]]
                pitem.getAxis("left").setTicks(ticks)
                pitem.getAxis("bottom").setLabel(f"{binType} Count" 
                                                 if num_files == 1 
                                                 else f"{binType} Count in File {fid}")
                # set visible range
                x_max = max(cntList) * 1.15
                y_max = len(numList)
                view_bin.setLimits(xMin=0, xMax=x_max, 
                                   yMin=-1, yMax=y_max, 
                                   minXRange=2, minYRange=y_max+1)
                view_bin.setRange(xRange=(0, x_max), 
                                  yRange=(-1, y_max),
                                  disableAutoRange=False)
                # add them to the same row
                self.plotlayout.addItem(pitem, row=row, col=fid, rowspan=1, colspan=1)
                # for 2nd+ plots
                if not isFirstPlot:
                    pitem.getAxis("left").hide()
                    view_bin.setYLink(tmpVbList[0])
                tmpVbList.append(view_bin)
                # this list is for storing all
                # view boxes from HBIN/SBIN plot
                self.view_list.append(view_bin)
            row += 1
        self.connectActions()


class WaferBlock(pg.ItemSample):
    '''
    Used for changing square sizes in legends
    '''
    def paint(self, p, *args):
        opts = self.item.opts

        visible = self.item.isVisible()
        if not visible:
            icon = getGraphIcon("invisibleEye")
            p.drawPixmap(QPoint(1, 1), icon.pixmap(18, 18))
            return

        symbol = opts.get('symbol', None)
        if symbol is not None:
            p.translate(10, 15)
            drawSymbol(p, symbol, 20, fn.mkPen(opts['pen']),
                       fn.mkBrush(opts['brush']))
    

class WaferMap(GraphicViewWithMenu):
    def __init__(self):
        super().__init__(600, 500)
        self.validData = False
        
    def setWaferData(self, waferData: dict):
        if len(waferData) == 0 or len(waferData["Statistic"]) == 0:
            return
        
        settings = ss.getSetting()
        self.validData = True
        waferView = WaferViewBox()
        pitem = pg.PlotItem(viewBox=waferView)
        # put legend in another view
        view_legend = pg.ViewBox()
        pitem_legend = pg.PlotItem(viewBox=view_legend, enableMenu=False)
        pitem_legend.getAxis("left").hide()
        pitem_legend.getAxis("bottom").hide()
        legend = pitem_legend.addLegend(offset=(10, 10), 
                                        verSpacing=5, 
                                        labelTextSize="15pt")
        xyData = waferData["Data"]
        isStackMap = waferData["Stack"]
        stackColorMap = pg.ColorMap(pos=None, color=["#00EE00", "#EEEE00", "#EE0000"])
        sortedKeys = sorted(xyData.keys())
        
        for num in sortedKeys:
            xyDict = xyData[num]
            # for stack map, num = fail counts
            # for wafer map, num = sbin number
            if isStackMap:
                color = stackColorMap.mapToQColor(num/sortedKeys[-1])
                tipFunc = f"XY: ({{x:.0f}}, {{y:.0f}})\nFail Count: {num}".format
                legendString = f"Fail Count: {num}"
            else:
                color = settings.sbinColor[num]
                (sbinName, sbinCnt, percent) = waferData["Statistic"][num]
                tipFunc = f"XY: ({{x:.0f}}, {{y:.0f}})\nSBIN {num}\nBin Name: {sbinName}".format
                legendString = f"SBIN {num} - {sbinName}\n[{sbinCnt} - {percent:.1f}%]"
            
            spi = pg.ScatterPlotItem(
                symbol="s",
                pen=None,
                size=0.95,
                pxMode=False,
                hoverable=True,
                hoverPen=pg.mkPen('r', width=4),
                hoverSize=1,
                tip=tipFunc,
                name=legendString)
            spi.addPoints(x=xyDict["x"], y=xyDict["y"], brush=color)
            pitem.addItem(spi)
            legend.addItem(WaferBlock(spi), spi.name())
        
        (ratio, die_size, invertX, invertY, waferID, sites) = waferData["Info"]
        x_max, x_min, y_max, y_min = waferData["Bounds"]
        waferView.setLimits(xMin=x_min-50, xMax=x_max+50, 
                            yMin=y_min-50, yMax=y_max+50, 
                            maxXRange=(x_max-x_min+100), 
                            maxYRange=(y_max-y_min+100),
                            minXRange=2, minYRange=2)
        waferView.setRange(xRange=(x_min-5, x_max+5), 
                            yRange=(y_min-5, y_max+5),
                            disableAutoRange=False)
        waferView.setAspectLocked(lock=True, ratio=ratio)
        
        if invertX:
            waferView.invertX(True)
        if invertY:
            waferView.invertY(True)
        view_legend.autoRange()
        # title
        site_info = "All Site" if -1 in sites else f"Site {','.join(map(str, sites))}"
        self.plotlayout.addLabel(f"{waferID} - {site_info}", row=0, col=0, 
                                 rowspan=1, colspan=2, size="20pt")
        # die size
        if die_size:
            dieSizeText = pg.LabelItem(die_size, size="12pt", color="#000000", anchor=(0, 0))
            dieSizeText.setParentItem(pitem)
            dieSizeText.anchor(itemPos=(0, 0), parentPos=(0, 0), offset=(30, 30))
            
        # add map and axis
        self.plotlayout.addItem(pitem, row=1, col=0, rowspan=1, colspan=2)
        # add legend
        self.plotlayout.addItem(pitem_legend, row=1, col=2, rowspan=1, colspan=1)
        self.view_list.append(waferView)
        self.connectActions()


__all__ = ["TrendChart", 
           "HistoChart", 
           "BinChart",
           "WaferMap"
           ]