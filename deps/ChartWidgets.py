#
# ChartWidgets.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 25th 2022
# -----
# Last Modified: Sun Nov 27 2022
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



from PyQt5 import QtWidgets
import numpy as np
import pyqtgraph as pg
import deps.SharedSrc as ss

pg.setConfigOptions(foreground='k', background='w', antialias=False)


class TrendChart(pg.GraphicsView):
    def __init__(self, *arg, **kargs):
        super().__init__(*arg, **kargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, 
                           QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
        self.setStyleSheet("QToolTip {background: red;}")
        self.plotlayout = pg.GraphicsLayout()
        self.setCentralWidget(self.plotlayout)
        self.meanPen = pg.mkPen({"color": "orange", "width": 1})
        self.medianPen = pg.mkPen({"color": "k", "width": 1})
        self.lolimitPen = pg.mkPen({"color": "#0000ff", "width": 3.5})
        self.hilimitPen = pg.mkPen({"color": "#ff0000", "width": 3.5})
        self.lospecPen = pg.mkPen({"color": "#000080", "width": 3.5})
        self.hispecPen = pg.mkPen({"color": "#8b0000", "width": 3.5})
        self.view_list = []
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
            view = pg.ViewBox()
            view.setMouseMode(view.RectMode)
            # plotitem setup
            pitem = pg.PlotItem(viewBox=view)
            pitem.addLegend((0, 1), labelTextSize="12pt")
            # iterate site data and draw in a same plot item
            # if mean and median is enabled, draw them as well
            sitesData = testData[fid]
            infoDict = testInfo[fid]
            # if len(sitesData) == 0 or len(infoDict) == 0:
            #     # skip this file if: 
            #     #  - test is not in this file (empty sitesData)
            #     #  - no data found in selected sites (test value is empty array)
            #     # to ensure the following operation is on valid data
            #     continue
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
                #TODO get file symbol
                fsymbol = "o"
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
            lolimit = infoDict["LLimit"]
            if settings.showLL_trend and ~np.isnan(lolimit):
                pitem.addLine(y=lolimit, pen=self.lolimitPen, name="Low Limit", 
                              label="Low Limit = {value:0.2f}", 
                              labelOpts={"position":0.2, "color": self.lolimitPen.color(), 
                                         "movable": True, "anchors": [(0.5, 0), (0.5, 0)]})
            hilimit = infoDict["HLimit"]
            if settings.showHL_trend and ~np.isnan(hilimit):
                pitem.addLine(y=hilimit, pen=self.hilimitPen, name="High Limit", 
                              label="High Limit = {value:0.2f}", 
                              labelOpts={"position":0.2, "color": self.hilimitPen.color(), 
                                         "movable": True, "anchors": [(0.5, 1), (0.5, 1)]})
            lspec = infoDict["LSpec"]
            if settings.showLSpec_trend and ~np.isnan(lspec):
                pitem.addLine(y=lspec, pen=self.lospecPen, name="Low Spec", 
                              label="Low Spec = {value:0.2f}", 
                              labelOpts={"position":0.2, "color": self.lospecPen.color(), 
                                         "movable": True, "anchors": [(0.5, 0), (0.5, 0)]})
            hspec = infoDict["HSpec"]
            if settings.showHSpec_trend and ~np.isnan(hspec):
                pitem.addLine(y=hspec, pen=self.hispecPen, name="High Spec", 
                              label="High Spec = {value:0.2f}", 
                              labelOpts={"position":0.2, "color": self.hispecPen.color(), 
                                         "movable": True, "anchors": [(0.5, 1), (0.5, 1)]})
            # labels and file id
            unit = infoDict["Unit"]
            pitem.getAxis("left").setLabel(f"Test Value" + f" ({unit})" if unit else "")
            pitem.getAxis("bottom").setLabel(f"DUTIndex")
            if len(testInfo) > 1:
                # only add if there are multiple files
                file_text = pg.TextItem(f"File {fid}", color="#000000", anchor=(1, 0))
                pitem.addItem(file_text)
            pitem.setClipToView(True)
            # set range and limits
            x_min = min(x_min_list)
            x_max = max(x_max_list)
            oh = 0.02 * (x_max - x_min)
            x_min -= oh
            x_max += oh
            view.setAutoPan()
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
                


__all__ = ["TrendChart", 
           ]