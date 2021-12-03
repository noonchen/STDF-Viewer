#
# clean.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: November 29th 2021
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



import os, shutil, pickle, platform

fileTupleList = []
curOS = platform.system()

if curOS == "Darwin":
    # macos
    buildOutput = "dist/"
    with open("build_tools/macos.pickle", "rb") as f:
        fileTupleList = pickle.load(f)
        
elif curOS == "Windows":
    buildOutput = "dist\\"
    with open("build_tools/windows.pickle", "rb") as f:
        fileTupleList = pickle.load(f)

elif curOS == "Linux":
    buildOutput = "dist/"
    with open("build_tools/linux.pickle", "rb") as f:
        fileTupleList = pickle.load(f)

else:
    raise Exception("Unknown OS")


## build dictionary from fileTupleList
# root -> filenames
fileDict = {}
for _root, _, _filename in fileTupleList:
    # folders are ignored, since I confirmed there are not empty folders
    if not _root in fileDict:
        fileDict[_root] = _filename
    else:
        fileDict[_root].extend(_filename)

# walk thru build folder
for root, _, filenames in os.walk(buildOutput):
    # we have to loop thru keys because the root is not exact equal to the key
    # strip is not helpful because the direction separator is different in OSs.
    stripRoot = root[len(buildOutput):]
    if stripRoot == "": continue
    
    if stripRoot in fileDict:
        if filenames == []: continue
        # loop thru files
        for fn in filenames:
            if fn == "": continue
            # delete files not in list
            if not fn in fileDict[stripRoot]:
                fullpath = os.path.join(root, fn)
                os.remove(fullpath)
                print("File deleted: {0}".format(fullpath))
    else:
        shutil.rmtree(root)
        print("Folder deleted: {0}".format(root))