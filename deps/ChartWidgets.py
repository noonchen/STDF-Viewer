#
# ChartWidgets.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 25th 2022
# -----
# Last Modified: Wed Oct 08 2025
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


def prepareHistoData(dutList: np.ndarray, 
                     dataList: np.ndarray, 
                     binCount: int, 
                     rectBaseLevel: int, 
                     horizontalBar: bool = True):
    '''
    returns hist, bin left edges, bin width, [(rect, duts)], tipData
    '''
    ffmt = ss.getSetting().getFloatFormat()
    hist, edges = np.histogram(dataList, bins=binCount)
    bin_width = edges[1]-edges[0]
    # get left edges
    edges = edges[:hist.size]
    # np.histogram is left-close-right-open, except the last bin
    # np.digitize should be right=False, use left edges to force close the rightmost bin
    bin_ind = np.digitize(dataList, edges, right=False)
    # bin index -> dut index list
    bin_dut_dict = {}
    for ind, dut in zip(bin_ind, dutList):
        # bin_ind start from 1
        bin_dut_dict.setdefault(ind-1, []).append(dut)
    # list of (rect, duts) for data picking
    rectDutList = []
    # list of tip data for hovering display
    tipData = []
    for ind, (h, e) in enumerate(zip(hist, edges)):
        # tipData must be the same length of hist/edges,
        # add data even if h == 0
        tipData.append( ("[{}, {})".format(ffmt % e, 
                                           ffmt % (e + bin_width)), 
                         h) )
        if h == 0:
            continue
        duts = bin_dut_dict[ind]
        
        if horizontalBar:
            left    = rectBaseLevel
            top     = e
            width   = h
            height  = bin_width
        else:
            left    = e
            top     = rectBaseLevel + h
            width   = bin_width
            height  = h
        
        rectDutList.append( (QRectF(left, top, width, height), 
                             duts) )
    return hist, edges, bin_width, rectDutList, tipData


def prepareBinRectList(binCenter: np.ndarray, 
                       binCnt: np.ndarray, 
                       binWidth: float, 
                       isHBIN: bool, 
                       binNumList: np.ndarray,
                       horizontalBar: bool = True):
    '''
    return [(rect, (isHBIN, bin_num))]
    '''
    rectList = []
    
    for center, cnt, bin_num in zip(binCenter, binCnt, binNumList):
        if cnt == 0:
            continue
        edge = center - binWidth/2
        
        if horizontalBar:
            left    = 0
            top     = edge
            width   = cnt
            height  = binWidth
        else:
            left    = edge
            top     = cnt
            width   = binWidth
            height  = cnt

        rectList.append( (QRectF(left, top, width, height), 
                          (isHBIN, bin_num)) )
    return rectList


def getAxisRange(minList, maxList, padding = 0.15):
    a_min = np.nanmin(minList)
    a_max = np.nanmax(maxList)
    if a_min == a_max:
        a_min -= 1
        a_max += 1
    else:
        pad = padding * (a_max - a_min)
        a_min -= pad
        a_max += pad
    return (a_min, a_max)


class PlotMenu(QMenu):
    def __init__(self):
        QMenu.__init__(self)
        # actions
        self.restoreMode = QAction("Restore View", self)
        self.scaleMode = QAction("Scale Mode", self)
        self.panMode = QAction("Pan Mode", self)
        self.pickMode = QAction("Data Pick Mode", self)
        self.clearSelection = QAction("Clear Selections", self)
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
                         self.clearSelection,
                         self.showDutData])
        
    def connectRestore(self, restoreMethod):
        self.restoreMode.triggered.connect(restoreMethod)
        
    def connectScale(self, scaleMethod):
        self.scaleMode.triggered.connect(scaleMethod)
        
    def connectPan(self, panMethod):
        self.panMode.triggered.connect(panMethod)
        
    def connectPick(self, pickMethod):
        self.pickMode.triggered.connect(pickMethod)
        
    def connectClearSelection(self, clearSelectionMethod):
        self.clearSelection.triggered.connect(clearSelectionMethod)
    
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
        self.connectActions()
        self.showDutSignal = None
        
    def setShowDutSignal(self, signal):
        self.showDutSignal = signal
    
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
        self.menu.connectRestore(self.onRestoreMode)
        self.menu.connectPan(self.onPanMode)
        self.menu.connectScale(self.onScaleMode)
        self.menu.connectPick(self.onPickMode)
        self.menu.connectClearSelection(self.onClearSel)
        self.menu.connectShowDut(self.onShowDut)
    
    def onRestoreMode(self):
        for view in self.view_list:
            view.enableAutoRange()
    
    def onScaleMode(self):
        self.menu.uncheckOthers("scale")
        # if action is checked twice, 
        # it will appear as unchecked...
        self.menu.scaleMode.setChecked(True)
        for view in self.view_list:
            view.setLeftButtonAction('rect')
            view.enableWheelScale = True
            view.enablePickMode = False

    def onPanMode(self):
        self.menu.uncheckOthers("pan")
        self.menu.panMode.setChecked(True)
        for view in self.view_list:
            view.setLeftButtonAction('pan')
            view.enableWheelScale = False

    def onPickMode(self):
        self.menu.uncheckOthers("pick")
        self.menu.pickMode.setChecked(True)
        for view in self.view_list:
            view.setLeftButtonAction('rect')
            view.enablePickMode = True

    def onClearSel(self):
        for view in self.view_list:
            view.clearSelections()
    
    def onShowDut(self):
        selectedData = []
        for view in self.view_list:
            selectedData.extend(view.getSelectedDataForDutTable())
        # send data to main UI
        if self.showDutSignal:
            self.showDutSignal.emit(selectedData)


class StdfViewrViewBox(pg.ViewBox):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.setMenuEnabled(False)
        # scale mode is enabled by default
        # wheel scale should be enabled as well
        self.enableWheelScale = True
        self.state['mouseMode'] = pg.ViewBox.RectMode
        self.enablePickMode = False
        # file id is for showing dut data only
        self.fileID = 0
    
    def setFileID(self, fid: int):
        self.fileID = fid
    
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
            # Zoom mode or Pick mode
            if ev.isFinish():
                self.rbScaleBox.hide()
                if self.enablePickMode:
                    # select objects in the scale box
                    self.selectItemsWithin(coordBox)
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
                    self.highlightitemsWithin(coordBox)
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
    
    def selectItemsWithin(self, coordBox: QRectF):
        print("`selectItemsWithin` should be overrided", coordBox)
    
    def highlightitemsWithin(self, coordBox: QRectF):
        print("`highlightitemsWithin` should be overrided", coordBox)
        
    def clearSelections(self):
        print("`clearSelections` should be overrided")
    
    def getSelectedDataForDutTable(self) -> list:
        print("`getSelectedDataForDutTable` should be overrided")
        return []


class TrendViewBox(StdfViewrViewBox):
    '''
    All items that added to viewbox will have a same parent: `self.childGroup`
    Items that will affect auto range will be added into `self.addedItems`
    '''
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        # add scatter item for displaying 
        # highlighted and selected point in pick mode
        self.hlpoints = pg.ScatterPlotItem(brush="#111111", size=10, name="_highlight")
        self.slpoints = pg.ScatterPlotItem(brush="#CC0000", size=10, name="_selection")
        # set z value for them stay at the top
        self.hlpoints.setZValue(1000)
        self.slpoints.setZValue(999)
        self.addItem(self.hlpoints)
        self.addItem(self.slpoints)
    
    def _getSelectedPoints(self, coordBox: QRectF) -> set:
        pointSet = set()
        for item in self.addedItems:
            if isinstance(item, pg.PlotDataItem):
                # trend plot is a PlotDataItem
                scatter = item.scatter
            elif isinstance(item, pg.ScatterPlotItem):
                # wafer map is a ScatterPlotItem
                scatter = item
            else:
                continue
            
            if (scatter.isVisible() and scatter.name() not in ["_selection", 
                                                               "_highlight"]):
                xData, yData = scatter.getData()
                # get mask from xy selection range
                xl, xr = (coordBox.x(), coordBox.x() + coordBox.width())
                yd, yu = (coordBox.y(), coordBox.y() + coordBox.height())
                mask = np.full(xData.size, True)
                mask &= xData > xl
                mask &= xData < xr
                mask &= yData > yd
                mask &= yData < yu
                # add points to set
                for x, y in zip(xData[mask], yData[mask]):
                    pointSet.add( (x, y) )
        return pointSet
    
    def selectItemsWithin(self, coordBox: QRectF):
        # clear highlight points when drag event is finished
        self.hlpoints.clear()
        pointSet = self._getSelectedPoints(coordBox)
        self.slpoints.addPoints(pos=pointSet)
    
    def highlightitemsWithin(self, coordBox: QRectF):
        pointSet = self._getSelectedPoints(coordBox)
        # remove previous and add new points
        self.hlpoints.clear()
        self.hlpoints.addPoints(pos=pointSet)
        
    def clearSelections(self):
        self.slpoints.clear()
    
    def getSelectedDataForDutTable(self):
        dataSet = set()
        dutIndexArray, _ = self.slpoints.getData()
        # remove duplicates
        # array is float type, must convert to int
        # otherwise will cause crash in `TestDataTable`
        _ = [dataSet.add((self.fileID, int(i))) for i in dutIndexArray]
        return list(dataSet)


class RectItem(pg.GraphicsObject):
    '''
    For showing highlight bars in histo/bin chart
    '''
    def __init__(self, **opts):
        super().__init__(None)
        self.opts = dict(
            name=None,
            pen=None,
            brush=None,
        )
        self._rects = []
        self.picture = QtGui.QPicture()
        self._generate_picture()
        self.setOpts(**opts)

    def setOpts(self, **opts):
        self.opts.update(opts)

    def name(self):
        return self.opts["name"]
    
    def addRects(self, rects: list):
        for r in rects:
            if r not in self._rects:
                self._rects.append(r)
        self._generate_picture()
        self.informViewBoundsChanged()
    
    def getRects(self):
        return self._rects
    
    def clear(self):
        self.picture = QtGui.QPicture()
        self._rects = []
        self._generate_picture()
        self.informViewBoundsChanged()
    
    def _generate_picture(self):
        if self.opts["pen"] is None:
            pen = pg.mkPen(None)
        else:
            pen = pg.mkPen(self.opts["pen"])
        
        if self.opts["brush"] is None:
            brush = pg.mkBrush(None)
        else:
            brush = pg.mkBrush(self.opts["brush"])
            
        painter = QtGui.QPainter(self.picture)
        painter.setPen(pen)
        painter.setBrush(brush)
        for rectTup in self._rects:
            painter.drawRect(rectTup[0])
        painter.end()

    def paint(self, painter, option, widget=None):
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class SVBarViewBox(StdfViewrViewBox):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.hlbars = RectItem(pen="#111111",
                               brush="#111111",
                               name="_highlight")
        self.slbars = RectItem(pen={"color": "#CC0000", 
                                    "width": 5},
                               brush=None,
                               name="_selection")
        self.hlbars.setZValue(1000)
        self.slbars.setZValue(999)
        self.addItem(self.hlbars)
        self.addItem(self.slbars)
        
    def _getSelectedRects(self, coordBox: QRectF) -> list:
        '''
        returns [(QRectF, duts)]
        '''
        rects = []
        for item in self.addedItems:
            if item.isVisible() and item.name() not in ["_selection", 
                                                        "_highlight"]:
                if isinstance(item, SVBarGraphItem):
                    rectList = item.getRectDutList()
                else:
                    continue
                
                for rectTup in rectList:
                    if coordBox.intersects(rectTup[0]):
                        rects.append(rectTup)
        return rects
    
    def selectItemsWithin(self, coordBox: QRectF):
        self.hlbars.clear()
        newRects = self._getSelectedRects(coordBox)
        self.slbars.addRects(newRects)
    
    def highlightitemsWithin(self, coordBox: QRectF):
        newRects = self._getSelectedRects(coordBox)
        self.hlbars.clear()
        self.hlbars.addRects(newRects)
    
    def clearSelections(self):
        self.slbars.clear()
    
    def getSelectedDataForDutTable(self) -> list:
        dataSet = set()
        for _, duts in self.slbars.getRects():
            _ = [dataSet.add( (self.fileID, dut) ) for dut in duts]
        return list(dataSet)


class BinViewBox(SVBarViewBox):
    def getSelectedDataForDutTable(self) -> list:
        '''
        For BinChart, return [(fid, isHBIN, bins)]
        '''
        tmp = {}
        for _, binTup in self.slbars.getRects():
            isHBIN, bin_num = binTup
            tmp.setdefault( (self.fileID, isHBIN), []).append(bin_num)
        return [(fid, isHBIN, bins) 
                for (fid, isHBIN), bins 
                in tmp.items()]


class WaferViewBox(TrendViewBox):
    '''
    WaferViewBox and TrendViewBox are both draw in scatter plot
    only difference is the data type of selections
    '''
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        # remove scatter items in super() init
        self.removeItem(self.hlpoints)
        self.removeItem(self.slpoints)
        # add scatter item for displaying 
        # highlighted and selected point in pick mode
        self.hlpoints = pg.ScatterPlotItem(symbol="h", 
                                           pen=None, 
                                           size=0.95, 
                                           pxMode=False, 
                                           brush="#111111", 
                                           name="_highlight")
        self.slpoints = pg.ScatterPlotItem(symbol="h", 
                                           pen=None, 
                                           size=0.95, 
                                           pxMode=False, 
                                           brush="#CC0000",
                                           name="_selection")
        # set z value for them stay at the top
        self.hlpoints.setZValue(1000)
        self.slpoints.setZValue(999)
        self.addItem(self.hlpoints)
        self.addItem(self.slpoints)
        # file id and waferIndex is 
        # for showing dut data
        self.waferInd = -1
        
    def setWaferIndex(self, ind: int):
        self.waferInd = ind
        
    def getSelectedDataForDutTable(self):
        # (waferInd, fid, (x, y))
        dataSet = set()
        xData, yData = self.slpoints.getData()
        # remove duplicates
        _ = [dataSet.add((self.waferInd, 
                          self.fileID, 
                          (int(x), int(y)))) 
             for x, y 
             in zip(xData, yData)]
        return list(dataSet)


class SigmaRegion(QtWidgets.QGraphicsRectItem):
    def __init__(self, region: tuple[int, float, float, float, float], isVertical = True):
        '''
        region:         Tuple of (n, avg, stddev, base, height), in data coords.
        isVertical:     If True, using y = base, y = base + height, x = -n*stddev, x = n*stddev to draw a rect.
        color:          Tuple of (R, G, B, A).
        '''
        self._isVertical = isVertical
        n, avg, stddev, base, height = region
        # QRectF coords is different than data coords, x+ towards right, y+ towards down,
        # which means:
        # right = left + width
        # bottom = top + height
        # 
        # we need to switch top and bottom to draw correct rect on data coords,
        # and noted that "top" of rect is actually the bottom line
        if isVertical:
            # top should be "base + height", but use "base"
            l, t, w, h = avg - n * stddev, base, 2 * n * stddev, height
        else:
            # top should be "avg + n * stddev", but use "avg - n * stddev"
            l, t, w, h = base, avg - n * stddev, height, 2 * n * stddev
        rect = QRectF(l, t, w, h)
        super().__init__(rect)
        self.setBrush(QtGui.QBrush(Qt.BrushStyle.NoBrush))
        self.setPen(QtGui.QPen(Qt.PenStyle.NoPen))
        # larger the n, lower it goes
        self.setZValue(-1 * n)
        
        # gray dash border
        self._borderPen = QtGui.QPen(QtGui.QColor(128, 128, 128))
        self._borderPen.setCosmetic(True)
        self._borderPen.setWidth(2)
        self._borderPen.setStyle(Qt.PenStyle.DashDotLine)
        
        # add label texts
        self.labelNeg = pg.TextItem(f"-{'' if n == 1 else n}σ", anchor=(1, 0))
        self.labelPos = pg.TextItem(f"{''  if n == 1 else n}σ", anchor=(0, 0) if isVertical else (1, 1))
        self.labelNeg.setPos(self.rect().bottomLeft() if isVertical else self.rect().topRight())
        self.labelPos.setPos(self.rect().bottomRight() if isVertical else self.rect().bottomRight())
        self.labelNeg.setParentItem(self)
        self.labelPos.setParentItem(self)
        
    def paint(self, painter, option, widget = None):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRect(self.rect())

        # draw only vertical dashed borders
        painter.setPen(self._borderPen)
        r = self.rect()
        if self._isVertical:
            painter.drawLine(r.topLeft(), r.bottomLeft())
            painter.drawLine(r.topRight(), r.bottomRight())
        else:
            painter.drawLine(r.topLeft(), r.topRight())
            painter.drawLine(r.bottomLeft(), r.bottomRight())


class TrendChart(GraphicViewWithMenu):
    def __init__(self):
        super().__init__(800, 400)
        self.meanPen = pg.mkPen({"color": "orange", "width": 1})
        self.medianPen = pg.mkPen({"color": "k", "width": 1})
        self.lolimitPen = pg.mkPen({"color": "#0000ff", "width": 3.5})
        self.hilimitPen = pg.mkPen({"color": "#ff0000", "width": 3.5})
        self.lospecPen = pg.mkPen({"color": "#000080", "width": 3.5})
        self.hispecPen = pg.mkPen({"color": "#8b0000", "width": 3.5})
        self.testInfo = {}
        self.testData = {}
        self.test_num = -9999
        self.test_name = ""
        self.y_min = np.nan
        self.y_max = np.nan
        self.validData = False
        
    def setData(self, dataDict: dict):
        '''
        Store info and data, calculate y axis limits for plotting
        '''
        self.testInfo: dict = dataDict["TestInfo"]
        # testData  key: fid, 
        #           value: a dict with site number as key and value: testDataDict of this site
        self.testData: dict = dataDict["Data"]
        # get display limit of y axis, should be 
        # the max|min of (lim, spec, data)
        y_min_list = []
        y_max_list = []
        for fid in self.testData.keys():
            i_file = self.testInfo[fid]
            d_file = self.testData[fid]
            if len(i_file) == 0:
                # this file doesn't contain
                # current test, 
                continue
            self.test_num = i_file["TEST_NUM"]
            self.test_name = i_file["TEST_NAME"]
            y_min_list.extend([i_file["LLimit"], i_file["LSpec"]])
            y_max_list.extend([i_file["HLimit"], i_file["HSpec"]])
            for d_site in d_file.values():
                # dynamic limits
                if d_site.get("dyLLimit", {}):
                    y_min_list.append(min(d_site["dyLLimit"].values()))
                if d_site.get("dyHLimit", {}):
                    y_max_list.append(max(d_site["dyHLimit"].values()))
                y_min_list.append(d_site["Min"])
                y_max_list.append(d_site["Max"])
                # at least one site data should be valid
                self.validData |= (~np.isnan(d_site["Min"]) and 
                                   ~np.isnan(d_site["Max"]))
        # validData means the valid data exists, 
        # set the flag to True and put it in top GUI
        if not self.validData:
            return
        # add 15% padding to y lim range
        self.y_min, self.y_max = getAxisRange(y_min_list, y_max_list)
        # call draw() if valid
        self.draw()
        
    def draw(self):
        settings = ss.getSetting()
        # add title
        self.plotlayout.addLabel(f"{self.test_num} {self.test_name}", row=0, col=0, 
                                 rowspan=1, colspan=len(self.testInfo),
                                 size="20pt")
        # create same number of viewboxes as file counts
        for fid in sorted(self.testInfo.keys()):
            isFirstPlot = len(self.view_list) == 0
            view = TrendViewBox()
            view.setFileID(fid)
            # plotitem setup
            pitem = pg.PlotItem(viewBox=view)
            pitem.addLegend((0, 1), labelTextSize="12pt")
            # iterate site data and draw in a same plot item
            # if mean and median is enabled, draw them as well
            sitesData = self.testData[fid]
            infoDict = self.testInfo[fid]
            if len(sitesData) == 0 or len(infoDict) == 0:
                # skip this file if: 
                #  - test is not in this file (empty sitesData)
                #  - no data found in selected sites (test value is empty array)
                # to ensure the following operation is on valid data
                continue
            x_min_list = []
            x_max_list = []
            dyL = {}
            dyH = {}
            for site, data_per_site in sitesData.items():
                x = data_per_site["dutList"]
                y = data_per_site["dataList"]
                if len(x) == 0 or len(y) == 0:
                    # skip this site that contains 
                    # no data
                    continue
                x_min_list.append(np.nanmin(x))
                x_max_list.append(np.nanmax(x))
                dyL.update(data_per_site.get("dyLLimit", {}))
                dyH.update(data_per_site.get("dyHLimit", {}))
                fsymbol = settings.gen.file_symbols[fid]
                siteColor = settings.color.site_colors[site]
                # test value
                site_info = "All Site" if site == -1 else f"Site {site}"
                pdi = pg.PlotDataItem(x=x, y=y, pen=None, 
                                      symbol=fsymbol, symbolPen="k", 
                                      symbolSize=8, symbolBrush=siteColor, 
                                      name=f"{site_info}")
                pdi.scatter.opts.update(hoverable=True, 
                                        tip=f"{site_info}\nDUTIndex: {{x:.0f}}\nValue: {{y:.3g}}".format,
                                        hoverSymbol="+",
                                        hoverSize=12,
                                        hoverPen=pg.mkPen("#ff0000", width=1))
                pitem.addItem(pdi)
                # mean
                mean = data_per_site["Mean"]
                if settings.trend.show_mean and ~np.isnan(mean) and ~np.isinf(mean):
                    pitem.addLine(y=mean, pen=self.meanPen, name=f"Mean_site{site}", label="x̅ = {value:0.3f}",
                                  labelOpts={"position":0.9, "color": self.meanPen.color(), "movable": True})
                # median
                median = data_per_site["Median"]
                if settings.trend.show_median and ~np.isnan(median) and ~np.isinf(median):
                    pitem.addLine(y=median, pen=self.medianPen, name=f"Median_site{site}", label="x̃ = {value:0.3f}",
                                  labelOpts={"position":0.7, "color": self.medianPen.color(), "movable": True})
            # add test limits and specs
            for (key, name, pen, enabled) in [("LLimit", "Low Limit", self.lolimitPen, settings.trend.show_lolim), 
                                              ("HLimit", "High Limit", self.hilimitPen, settings.trend.show_hilim), 
                                              ("LSpec", "Low Spec", self.lospecPen, settings.trend.show_lospec), 
                                              ("HSpec", "High Spec", self.hispecPen, settings.trend.show_hispec)]:
                lim = infoDict[key]
                pos = 0.8 if key.endswith("Spec") else 0.2
                anchors = [(0.5, 0), (0.5, 0)] if key.startswith("L") else [(0.5, 1), (0.5, 1)]
                if enabled and ~np.isnan(lim) and ~np.isinf(lim):
                    pitem.addLine(y=lim, pen=pen, name=name, 
                                label=f"{name} = {{value:0.2f}}", 
                                labelOpts={"position":pos, "color": pen.color(), 
                                            "movable": True, "anchors": anchors})
            # dynamic limits
            for (dyDict, name, pen, enabled) in [(dyL, "Dynamic Low Limit", self.lolimitPen, settings.trend.show_lolim), 
                                                 (dyH, "Dynamic High Limit", self.hilimitPen, settings.trend.show_hilim)]:
                if enabled and len(dyDict) > 0:
                    x = np.array(sorted(dyDict.keys()))
                    dylims = np.array([dyDict[i] for i in x])
                    pitem.addItem(pg.PlotDataItem(x=x, y=dylims, pen=pen, name=name, color=pen.color()))
            # labels and file id
            unit = infoDict["Unit"]
            pitem.getAxis("left").setLabel(f"Test Value" + f" ({unit})" if unit else "")
            pitem.getAxis("bottom").setLabel(f"DUTIndex")
            if len(self.testInfo) > 1:
                # only add if there are multiple files
                addFileLabel(pitem, fid)
            pitem.setClipToView(True)
            # set range and limits
            x_min, x_max = getAxisRange(x_min_list, x_max_list, 0.02)
            # view.setAutoPan()
            view.setRange(xRange=(x_min, x_max), 
                          yRange=(self.y_min, self.y_max),
                          padding=0.0)
            view.setLimits(xMin=x_min, xMax=x_max,      # avoid blank area
                           yMin=self.y_min, yMax=self.y_max,
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


class SVBarGraphItem(pg.BarGraphItem):
    '''
    STDF Viewer customize BarGraphItem
    '''
    def __init__(self, **opts):
        super().__init__(**opts)
        self.rectDutList = []
        self.opts['tip'] = None
        self._toolTipCleared = True
        
    def setRectDutList(self, rdl: list):
        self.rectDutList = rdl
        
    def getRectDutList(self):
        return self.rectDutList
    
    def setHoverTipFunction(self, tipFunc):
        # tipFunc(arg1, arg2):
        # arg1: str, bar description
        # arg2: int, bar height/count
        #
        # the value of args are get from `tipData`
        self.opts['tip'] = tipFunc
    
    def setTipData(self, tipData: list):
        # a list of (description, height/count) 
        # using same order of bar data (x0, y0, etc.)
        self.tipData = tipData
    
    def hoverEvent(self, ev):
        hoveredRectIdx = []
        if not ev.exit:
            # found which rects contain the hover position,
            # and store their indexes
            for idx, rect in enumerate(self._rectarray.instances()):
                if rect.contains(ev.pos()):
                    hoveredRectIdx.append(idx)
        
        # Show information about hovered points in a tool tip
        vb = self.getViewBox()
        if vb is not None and self.opts['tip'] is not None and len(self.tipData) > 0:
            numHovered = len(hoveredRectIdx)
            if numHovered > 0:
                cutoff = 3
                tip = [self.opts['tip'](*self.tipData[idx])
                        for idx in hoveredRectIdx[:cutoff]]
                if numHovered > cutoff:
                    tip.append('({} others...)'.format(numHovered - cutoff))
                vb.setToolTip('\n\n'.join(tip))
                self._toolTipCleared = False
            elif not self._toolTipCleared:
                vb.setToolTip("")
                self._toolTipCleared = True


class HistoChart(TrendChart):
    def draw(self):
        settings = ss.getSetting()
        # add title
        self.plotlayout.addLabel(f"{self.test_num} {self.test_name}", row=0, col=0, 
                                 rowspan=1, colspan=len(self.testInfo),
                                 size="20pt")
        # create same number of viewboxes as file counts
        for fid in sorted(self.testInfo.keys()):
            isFirstPlot = len(self.view_list) == 0
            view = SVBarViewBox()
            view.setFileID(fid)
            # plotitem setup
            pitem = pg.PlotItem(viewBox=view)
            pitem.addLegend((0, 1), labelTextSize="12pt")
            # iterate site data and draw in a same plot item
            # if mean and median is enabled, draw them as well
            sitesData = self.testData[fid]
            infoDict = self.testInfo[fid]
            if len(sitesData) == 0 or len(infoDict) == 0:
                # skip this file if: 
                #  - test is not in this file (empty sitesData)
                #  - no data found in selected sites (test value is empty array)
                # to ensure the following operation is on valid data
                continue
            bar_base = 0
            # track bin_width of all sites
            bin_width_list = []
            # xaxis tick labels
            ticks = []
            for site, data_per_site in sitesData.items():
                x = data_per_site["dutList"]
                y = data_per_site["dataList"]
                if len(x) == 0 or len(y) == 0:
                    # skip this site that contains 
                    # no data
                    continue
                siteColor = settings.color.site_colors[site]
                # calculate bin edges and histo counts                
                (hist, 
                 edges, 
                 bin_width, 
                 rectDutList, 
                 tipData) = prepareHistoData(x, y, 
                                            settings.histo.bin_count, 
                                            bar_base)
                bin_width_list.append(bin_width)
                site_info = "All Site" if site == -1 else f"Site {site}"
                # use normalized hist if enabled
                if settings.histo.norm_histobars and hist.max() != 0:
                    hist = hist / hist.max()
                # show bars if enabled
                if settings.histo.show_histobars:
                    item = SVBarGraphItem(x0=bar_base, y0=edges, 
                                        width=hist, height=bin_width, 
                                        brush=siteColor, name=site_info)
                    item.setRectDutList(rectDutList)
                    item.setTipData(tipData)
                    item.setHoverTipFunction("Range: {}\nDUT Count: {}".format)
                    pitem.addItem(item)
                # set the bar base of histogram of next site
                inc = 1.2 * hist.max()
                ticks.append((bar_base + 0.5 * inc, site_info))
                # mean
                mean = data_per_site["Mean"]
                if settings.histo.show_mean and ~np.isnan(mean) and ~np.isinf(mean):
                    pitem.addLine(y=mean, pen=self.meanPen, name=f"Mean_site{site}", label="x̅ = {value:0.3f}",
                                  labelOpts={"position":0.9, "color": self.meanPen.color(), "movable": True})
                # median
                median = data_per_site["Median"]
                if settings.histo.show_median and ~np.isnan(median) and ~np.isinf(median):
                    pitem.addLine(y=median, pen=self.medianPen, name=f"Median_site{site}", label="x̃ = {value:0.3f}",
                                  labelOpts={"position":0.7, "color": self.medianPen.color(), "movable": True})
                # sigma lines
                stddev = data_per_site["SDev"]
                sigmaList = settings.histo.get_sigma_list()
                if len(sigmaList) > 0 and stddev != 0 and ~np.isnan(stddev) and ~np.isinf(stddev):
                    for n in sigmaList:
                        if n == 0: continue
                        sigreg = SigmaRegion((n, mean, stddev, bar_base, inc), False)
                        view.addItem(sigreg)
                # update bar base for other sites
                bar_base += inc
            # add test limits and specs
            for (key, name, pen, enabled) in [("LLimit", "Low Limit", self.lolimitPen, settings.histo.show_lolim), 
                                              ("HLimit", "High Limit", self.hilimitPen, settings.histo.show_hilim), 
                                              ("LSpec", "Low Spec", self.lospecPen, settings.histo.show_lospec), 
                                              ("HSpec", "High Spec", self.hispecPen, settings.histo.show_hispec)]:
                lim = infoDict[key]
                pos = 0.8 if key.endswith("Spec") else 0.2
                anchors = [(0.5, 0), (0.5, 0)] if key.startswith("L") else [(0.5, 1), (0.5, 1)]
                if enabled and ~np.isnan(lim) and ~np.isinf(lim):
                    pitem.addLine(y=lim, pen=pen, name=name, 
                                label=f"{name} = {{value:0.2f}}", 
                                labelOpts={"position":pos, "color": pen.color(), 
                                            "movable": True, "anchors": anchors})
            
            if len(self.testInfo) > 1:
                # only add if there are multiple files
                addFileLabel(pitem, fid)
            # set min range to avoid zoom too much
            minZoomRange = 4 * min(bin_width_list)
            view.setRange(xRange=(0, bar_base), 
                          yRange=(self.y_min, self.y_max),
                          padding=0.0)
            view.setLimits(xMin=0, xMax=bar_base+0.5,
                           yMin=self.y_min, yMax=self.y_max,
                           minYRange=minZoomRange)
            # add to layout
            self.plotlayout.addItem(pitem, row=1, col=fid, rowspan=1, colspan=1)
            # link current viewbox to previous, 
            # show axis but hide value 2nd+ plots
            # labels and file id
            unit = infoDict["Unit"]
            pitem.getAxis("bottom").setTicks([ticks])
            if isFirstPlot:
                pitem.getAxis("left").setLabel(self.test_name + f" ({unit})" if unit else "")
            else:
                pitem.getAxis("left").setStyle(showValues=False)
                view.setYLink(self.view_list[0])
            # append view for counting plots
            self.view_list.append(view)


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
            isHBIN = True if binType == "HBIN" else False
            num_files = len(hsbin)
            # use a list to track viewbox count in
            # a single plot, used for Y-link and 
            # hide axis
            tmpVbList = []
            binColorDict = settings.color.hbin_colors if isHBIN else settings.color.sbin_colors
            # add title
            binTypeName = "Hardware Bin" if isHBIN else "Software Bin"
            self.plotlayout.addLabel(f"{binTypeName}{hs_info}", 
                                     row=row, col=0, 
                                     rowspan=1, colspan=num_files, 
                                     size="20pt")
            row += 1
            # iterate thru all files
            for fid in sorted(hsbin.keys()):
                isFirstPlot = len(tmpVbList) == 0
                view_bin = BinViewBox()
                view_bin.setFileID(fid)
                view_bin.invertY(True)
                pitem = pg.PlotItem(viewBox=view_bin)
                binStats = hsbin[fid]
                # get data for barGraph
                numList = sorted(binTicks.keys())
                cntList = np.array([binStats.get(n, 0) for n in numList])
                colorList = [binColorDict[n] for n in numList]
                # draw horizontal bars, use `ind` instead of `bin_num` as y
                y = np.arange(len(numList))
                height = 0.8
                rectList = prepareBinRectList(y, cntList, height, isHBIN, numList)
                # show name (tick), bin number and count in hover tip
                ticks = [[binTicks[n] for n in numList]]
                tipData = [(f"{name[1]}\nBin: {n}", cnt) 
                           for (name, n, cnt) 
                           in zip(ticks[0], numList, cntList)]
                bar = SVBarGraphItem(x0=0, y=y, width=cntList, height=height, brushes=colorList)
                bar.setRectDutList(rectList)
                bar.setTipData(tipData)
                bar.setHoverTipFunction("Name: {}\nDUT Count: {}".format)
                pitem.addItem(bar)
                # set ticks to y
                pitem.getAxis("left").setTicks(ticks)
                pitem.getAxis("bottom").setLabel(f"{binType} Count" 
                                                 if num_files == 1 
                                                 else f"{binType} Count in File {fid}")
                # set visible range
                x_max = max(cntList) * 1.15
                y_max = len(numList)
                view_bin.setLimits(xMin=0, xMax=x_max, 
                                   yMin=-1, yMax=y_max, 
                                   minYRange=4)
                view_bin.setRange(xRange=(0, x_max), 
                                  yRange=(-1, y_max),
                                  padding=0.0)
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
        waferInd, fid = waferData["ID"]
        waferView = WaferViewBox()
        waferView.setWaferIndex(waferInd)
        waferView.setFileID(fid)
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
        stackColorMap = pg.ColorMap(pos=None, color=["#00EE00", "#EEEE00", "#EE0000"])
        sortedKeys = sorted(xyData.keys())
        
        for num in sortedKeys:
            xyDict = xyData[num]
            # for stack map, num = fail counts
            # for wafer map, num = sbin number
            if waferInd == -1:
                color = stackColorMap.mapToQColor(num/sortedKeys[-1])
                tipFunc = f"XY: ({{x:.0f}}, {{y:.0f}})\nFail Count: {num}".format
                legendString = f"Fail Count: {num}"
            else:
                color = settings.color.sbin_colors[num]
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


__all__ = ["TrendChart", 
           "HistoChart", 
           "BinChart",
           "WaferMap"
           ]