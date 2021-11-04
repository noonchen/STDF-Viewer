#
# cystdf_amalgamation_setup.py - STDF Viewer
# 
# Author: noonchen - chennoon233@foxmail.com
# Created Date: April 20th 2021
# -----
# Last Modified: Tue Nov 02 2021
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



from setuptools import Extension, setup
from Cython.Build import cythonize
import numpy, os, sys


# C sources that are not included automatically by cython (aka, no pxd files)
source_c = []
for dirp, dirn, fn in os.walk(os.path.join(os.getcwd(), "stdf4_src")):
      if len(dirn) == 0:
            for f in fn:
                  if f.endswith(".c"):
                        rpath = os.path.join(dirp, f)
                        source_c.append(os.path.relpath(rpath, os.getcwd()))
                        

isWindows = sys.platform.startswith("win")
isMac = sys.platform.startswith("darwin")

library_dirs      = []
libraries         = []
compile_args      = []
link_args         = []
include_dirs      = [numpy.get_include()]                                    # numpy headers
macros            = [("_LARGEFILE64_SOURCE", 1),                             # enable 64bit for zlib
                     ("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]       # suppress numpy deprecate warning

# openmp
if isMac:
      include_dirs.append(os.path.join(os.getcwd(), "libomp", "include"))
      library_dirs.append(os.path.join(os.getcwd(), "libomp", "lib"))
      libraries.append('omp')
      # clang need to preprocess openmp pragma
      compile_args.extend(['-Xpreprocessor', '-fopenmp'])
      # no need for link args because we used static link by specifying omp location
      # link_args.extend(['-Xpreprocessor', '-fopenmp', '-lomp'])
else:
      compile_args.extend(['-fopenmp'])
      link_args.extend(['-fopenmp'])

# static link in windows
if isWindows:
      library_dirs.append(os.path.join(os.getcwd(), "vcruntime"))
      compile_args.append('-DMS_WIN64')
      link_args.extend(['-static-libgcc',
                        '-static-libstdc++',
                        '-Wl,-Bstatic,--whole-archive',
                        '-lwinpthread',
                        '-Wl,--no-whole-archive'])

setup(ext_modules = cythonize(Extension(
            "_cystdf",                                             # the extension name
            sources           = ["cystdf_amalgamation.pyx"] \
                                + source_c,
            language          = "c",                              # generate and compile C code
            library_dirs      = library_dirs,
            libraries         = libraries,
            extra_compile_args= compile_args,
            extra_link_args   = link_args,           
            include_dirs      = include_dirs,
            define_macros     = macros
      )))

# python3 cystdf_amalgamation_setup.py build_ext --inplace
# python cystdf_amalgamation_setup.py build_ext --inplace --compile=mingw32