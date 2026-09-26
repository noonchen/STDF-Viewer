#
# busyIndicator.py - STDF Viewer
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
# Spinner plus an attachable busy overlay, so individual panes can show their
# own spinner while the rest of the window stays usable.
#

import logging
import os

from PyQt5 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class BusyIndicator(QtWidgets.QWidget):
    def __init__(self, parent=None, size=22, line_width=3, color="#2F80ED",
                 fps=30, step=6):
        super().__init__(parent)
        self._line_width = line_width
        self._color = QtGui.QColor(color)
        self._angle = 0
        self._step = step
        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self._timer.setInterval(max(1, int(1000 / fps)))
        self._timer.timeout.connect(self._advance)
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def start(self):
        self._angle = 0
        self.show()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()
        self.update()

    def _advance(self):
        self._angle = (self._angle + self._step) % 360.0
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w = self._line_width
        rect = self.rect().adjusted(w, w, -w, -w)
        pen = QtGui.QPen(self._color, w, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, int((90.0 - self._angle) * 16), int(280 * 16))


class BusyOverlay(QtWidgets.QWidget):
    """Semi-transparent overlay with a centered spinner.

    One instance follows one parent for its whole lifetime, so several panes
    can spin at once; never reparent an instance.
    """

    def __init__(self, parent=None, text="Loading..."):
        super().__init__(parent)
        self.setObjectName("busyOverlay")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        # purely decorative: clicks go to the covered widgets, so the windows
        # behind the overlay stay usable
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("QWidget#busyOverlay { background-color: rgba(255, 255, 255, 150); }")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        self._spinner = BusyIndicator(self, size=40, line_width=5)
        layout.addWidget(self._spinner, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._label = QtWidgets.QLabel(text, self)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = self._label.font()
        font.setPointSize(11)
        self._label.setFont(font)
        layout.addWidget(self._label)
        layout.addStretch(1)
        if parent is not None:
            parent.installEventFilter(self)
            self._syncGeometry()
        self.hide()

    def _syncGeometry(self):
        """Always cover the whole parent, never a stale (0, 0, 0, 0) rect."""
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() in (
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.Move,
            QtCore.QEvent.Type.LayoutRequest,
        ):
            self._syncGeometry()
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._syncGeometry()

    def start(self, text=None):
        if text:
            self._label.setText(text)
        self._syncGeometry()
        self.show()
        self.raise_()
        self._syncGeometry()
        self._spinner.start()

    def isPainted(self) -> bool:
        """True when this overlay is really on screen right now."""
        return self.isVisibleTo(self.window())

    def stop(self):
        self._spinner.stop()
        self.hide()


class BusyManager:
    """Owns one overlay per pane and decides nothing about *when* work happens.

    The caller passes the panes that are doing the work, so this class stays
    free of any knowledge of the main window's state.
    """

    def __init__(self, window, is_allowed=None):
        self._window = window
        self._is_allowed = is_allowed or (lambda pane: pane is not None)
        self._overlays = {}
        self._text = None
        self._panes = []
        self._shown = []

    def _allowed(self, panes):
        """Drop panes that must never be covered (the Detailed Info tab)."""
        panes = [p for p in panes or [] if p is not None]
        blocked = [p for p in panes if not self._is_allowed(p)]
        if blocked:
            logger.error("busy guard: refusing to cover %s",
                         [p.objectName() or type(p).__name__ for p in blocked])
            if os.environ.get("STDF_BUSY_GUARD", "1") == "strict":
                raise AssertionError(
                    "busy spinner must not cover %s"
                    % [p.objectName() or type(p).__name__ for p in blocked])
        return [p for p in panes if self._is_allowed(p)]

    def _overlayFor(self, pane) -> BusyOverlay:
        """The overlay instance owned by `pane` (created on first use)."""
        overlay = self._overlays.get(pane)
        if overlay is None:
            overlay = BusyOverlay(pane)
            self._overlays[pane] = overlay
        return overlay

    def show(self, text="Loading...", panes=None):
        """Start a spinner on `panes`; hidden panes only remember the text."""
        panes = self._allowed(panes)
        # drop spinners of a previous call, otherwise a narrower follow-up
        # update leaves the earlier ones turning next to the new one
        for pane in self._shown:
            if pane not in panes:
                self._overlayFor(pane).stop()
        self._text = text
        self._panes = list(panes)
        self._shown = list(panes)
        for pane in panes:
            overlay = self._overlayFor(pane)
            if pane.isVisibleTo(self._window):
                overlay.start(text)
            else:
                overlay.stop()

    def hide(self):
        self._text = None
        self._shown = []
        for overlay in self._overlays.values():
            overlay.stop()

    def reattach(self):
        """Re-show the spinners after the user switched to another page."""
        if self._text:
            self.show(self._text, panes=list(self._panes))

