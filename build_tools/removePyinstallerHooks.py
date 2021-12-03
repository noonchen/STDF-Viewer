#
# clean.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 29th 2021
# -----
# Last Modified: Mon Nov 29 2021
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



import os, PyInstaller

hooksFolder=os.path.join(os.path.dirname(PyInstaller.__file__), 'hooks'); 
needPyQt5hooks = ["hook-PyQt5.py",
                  "hook-PyQt5.Qt.py",
                  "hook-PyQt5.QtCore.py",
                  "hook-PyQt5.QtGui.py",
                  "hook-PyQt5.QtSvg.py",
                  "hook-PyQt5.QtSvg.py"]
rthooksFolder=os.path.join(os.path.dirname(PyInstaller.__file__), 'hooks', 'rthooks'); 
needRThooks = ["pyi_rth_mplconfig.py",
               "pyi_rth_pyqt5.py"]
# walk thru build folder
for root, _, filenames in os.walk(hooksFolder):
    for fn in filenames:
        if fn.startswith("hook-PyQt") or fn.startswith("hook-PySide"):
            # is qt hooks
            if not fn in needPyQt5hooks:
                fullpath = os.path.join(root, fn)
                os.remove(fullpath)
                print("Hook deleted: {0}".format(fullpath))
        elif fn == "hook-_tkinter.py":
            fullpath = os.path.join(root, fn)
            os.remove(fullpath)
            print("Hook deleted: {0}".format(fullpath))
