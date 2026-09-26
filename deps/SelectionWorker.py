#
# SelectionWorker.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: September 26th 2026
# -----
# Last Modified: Sat Sep 26 2026
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
# Selection queries on a worker thread.  `DataFetcher` is unsendable, so the
# worker builds its own `DataInterface` inside its thread and answers through a
# queued signal; only the newest pending request is kept, and every answer
# carries its request id so stale results can be dropped.
#

import logging
import threading
import time

from PyQt5 import QtCore

from deps.DataInterface import DataInterface
from deps.SharedSrc import LOG_NAME, tab

logger = logging.getLogger(LOG_NAME)


class SelectionRequest:
    """A plain description of the work the GUI needs for one selection."""

    __slots__ = ("requestId", "tabType", "selTests", "waferSelection", "heads",
                 "sites", "needStat", "needTab", "needRawData")

    def __init__(self, requestId: int, tabType: int, selTests: list, heads: list,
                 sites: list, needStat: bool, needTab: bool, needRawData: bool,
                 waferSelection: list = None):
        self.requestId = requestId
        self.tabType = tabType
        self.selTests = selTests
        # selected wafers, used by the wafer tab (its test list is disabled)
        self.waferSelection = waferSelection or []
        self.heads = heads
        self.sites = sites
        self.needStat = needStat
        self.needTab = needTab
        self.needRawData = needRawData


class SelectionWorker(QtCore.QObject):
    """Runs selection queries on a private thread with a private DataInterface."""

    resultReady = QtCore.pyqtSignal(int, object)   # requestId, payload or None

    def __init__(self, dbPath: str, parent=None):
        super().__init__(parent)
        self._dbPath = dbPath
        self._pending = None
        self._wake = threading.Condition(threading.Lock())
        self._stop = False
        self._thread = None
        self._ready = threading.Event()

    # ---------- GUI thread ----------

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="STDF-SelectionWorker", daemon=True)
        self._thread.start()

    def submit(self, request: SelectionRequest):
        """Queue `request`, replacing any request that has not started yet."""
        with self._wake:
            dropped = self._pending is not None
            self._pending = request
            self._wake.notify()

    def shutdown(self):
        with self._wake:
            self._stop = True
            self._pending = None
            self._wake.notify()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5.0)

    # ---------- worker thread ----------

    def _run(self):
        di = None
        try:
            di = DataInterface()
            di.dbPath = self._dbPath
            di.loadDatabase()
        except Exception:
            logger.exception("selection worker cannot open %s", self._dbPath)
            di = None
        self._ready.set()

        while True:
            with self._wake:
                while self._pending is None and not self._stop:
                    self._wake.wait(0.2)
                if self._stop:
                    break
                request, self._pending = self._pending, None
            if di is None:
                self.resultReady.emit(request.requestId, None)
                continue
            payload = None
            try:
                payload = self._compute(di, request)
            except Exception:
                logger.exception("selection work failed (id=%d)", request.requestId)
            self.resultReady.emit(request.requestId, payload)

        if di is not None:
            try:
                di.close()
            except Exception:
                logger.exception("selection worker close failed")

    def _compute(self, di: DataInterface, request: SelectionRequest) -> dict:
        payload = {}
        t0 = time.perf_counter()
        if request.needStat:
            stat = self._statistics(di, request)
            if stat is not None:
                payload["stat"] = stat
        tStat = time.perf_counter() - t0
        t0 = time.perf_counter()
        if request.needTab:
            payload.update(self._tabData(di, request))
        tTab = time.perf_counter() - t0
        return payload

    @staticmethod
    def _statistics(di: DataInterface, request: SelectionRequest):
        if request.tabType == tab.Bin:
            # the bin table is a bin distribution, the selected tests are
            # irrelevant for it
            return di.getBinStatistics(request.heads, request.sites)
        if request.tabType == tab.Wafer:
            # wafer rows come from the selected wafers (test selection is
            # disabled on that tab), while the charts use getWaferMapData
            return di.getWaferStatistics(request.selTests, request.sites)
        if request.tabType in (tab.Info, tab.Trend, tab.Histo, tab.PPQQ):
            return di.getTestStatistics(request.selTests, request.heads, request.sites)
        return None

    @staticmethod
    def _tabData(di: DataInterface, request: SelectionRequest) -> dict:
        out = {}
        if request.tabType == tab.Info:
            if request.needRawData:
                out["rawData"] = di.getTestDataTableContent(
                    request.selTests, request.heads, request.sites)
        elif request.tabType in (tab.Trend, tab.Histo):
            # one query per (test, head), feeds the chart of that combination
            out["plots"] = [(testTuple, head,
                             di.getTrendChartData(testTuple, head, request.sites))
                            for testTuple in request.selTests
                            for head in request.heads]
        elif request.tabType == tab.Wafer:
            # the wafer list provides the tuples the wafer charts index by
            # (test selection is disabled on this tab)
            out["plots"] = [(waferTuple, None,
                             di.getWaferMapData(waferTuple, request.sites))
                            for waferTuple in request.waferSelection]
        elif request.tabType == tab.Bin:
            out["binData"] = [(head, site, di.getBinChartData(head, site))
                              for head in request.heads
                              for site in request.sites]
        return out
