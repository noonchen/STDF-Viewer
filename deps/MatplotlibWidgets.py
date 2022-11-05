#
# MatplotlibWidgets.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 3rd 2022
# -----
# Last Modified: Thu Nov 03 2022
# Modified By: noonchen
# -----
# Copyright (c) 2022 noonchen
# <<licensetext>>
#

import os
import numpy as np

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, Qt

import matplotlib
matplotlib.use('QT5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT


# convert from pixel coords to data coords
toDCoord = lambda ax, point: ax.transData.inverted().transform(point)


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
        self.pmr = 0
        self.test_name = ""
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
            self.dcp_bin = self.ax.annotate(text="", xy=(1, 1), xycoords="axes fraction", xytext=(-8, -8), textcoords="offset points", fontname=mainGUI.imageFont, weight="bold", 
                                            fontsize=8, va="top", ha="right", bbox=dict(boxstyle="round,pad=0.5", fc="#FFFFCC"), zorder=1000)
            self.dcp_bin.set_visible(False)
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
            self.dcp_bin.set_visible(False)
        elif self.waferMode:
            self.dcp_wafer.set_visible(False)
            
        self.ax.figure.canvas.draw()
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.figure.bbox)

    def mouse_move(self, event):
        if not event.inaxes:
            return
        
        ishover = False
        ind = 0     # used in bin chart
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
            
            for ind, rec in enumerate(self.binchart):
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
                count = data.get_height()
                binNum = self.binchart.binList[ind]
                binName = self.binchart.binNames[ind]
                text = self.tr('Bin: %d\nCount: %d\nBinName: %s') % \
                               (binNum, count, binName)
                self.dcp_bin.set_text(text)
                # self.dcp_bin.set_position(self.ax.transData.inverted().transform((event.x+10, event.y+10)))
                self.dcp_bin.set_visible(True)
                self.ax.draw_artist(self.dcp_bin)
            
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
                self.dcp_bin.set_visible(False)
                self.ax.draw_artist(self.dcp_bin)
            
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

