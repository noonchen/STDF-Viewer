#
# pickleFinalFileTree.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: December 1st 2021
# -----
# Last Modified: Wed Dec 01 2021
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



import os, pickle, platform

if platform.system() == "Darwin":
    folderName = "STDF Viewer.app"
    dumpfile = "macos.pickle"
else:
    folderName = "STDF Viewer"
    if platform.system() == "Windows":
        dumpfile = "windows.pickle"
    else:
        dumpfile = "linux.pickle"

fileTree = []
for i in os.walk(folderName):
    print(i)
    fileTree.append(i)
    
with open(dumpfile, "wb") as df:
    pickle.dump(fileTree, df, protocol=pickle.HIGHEST_PROTOCOL)
    
# test
with open(dumpfile, "rb") as df:
    readTree = pickle.load(df)
assert fileTree == readTree, "Dump failed"
print("dump success")