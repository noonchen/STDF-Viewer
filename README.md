# STDF Viewer <img src="screenshots/stdfViewer.png" height=50>

[![build](https://github.com/noonchen/STDF-Viewer/actions/workflows/build.yml/badge.svg)](https://github.com/noonchen/STDF-Viewer/actions/workflows/build.yml)  [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/noonchen/STDF-Viewer.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/noonchen/STDF-Viewer/context:python)  [![Codacy Badge](https://api.codacy.com/project/badge/Grade/d773b27672d34686bee9631f393d2ea6)](https://app.codacy.com/gh/noonchen/STDF-Viewer?utm_source=github.com&utm_medium=referral&utm_content=noonchen/STDF-Viewer&utm_campaign=Badge_Grade_Settings)  [![version](https://img.shields.io/github/v/release/noonchen/STDF-Viewer?include_prereleases)](https://github.com/noonchen/STDF-Viewer/releases/latest)  [![downloads](https://img.shields.io/github/downloads/noonchen/STDF-Viewer/total?label=total%20downloads)](https://github.com/noonchen/STDF-Viewer/releases)  [![license](https://img.shields.io/github/license/noonchen/STDF-Viewer)](https://github.com/noonchen/STDF-Viewer/blob/main/LICENSE)

STDF Viewer is a free, fast and powerful GUI tool to visualize STDF (semiconductor Standard Test Data Format) data files.

Devloped by Noon Chen <chennoon233@foxmail.com>

| [中文版](README_CN.md) |

<img src="screenshots/mainUI.png">

## Table of Content
- [**Build**](#build)
- [**Usage**](#usage)
  - [Open STDF files](#open-stdf-files)
  - [Merge STDF files](#merge-stdf-files)
  - [Find failed test items](#find-failed-test-items)
  - [Looking for DUTs' info](#looking-for-duts-info)
  - [Display GDRs & DTRs info](#display-gdrs--dtrs-info)
  - [Analyzing test data](#analyzing-test-data)
      - [Test data](#test-data)
      - [Trend chart](#trend-chart)
      - [Histogram](#histogram)
  - [Analyzing bin distribution](#analyzing-bin-distribution)
  - [Viewing wafer maps](#viewing-wafer-maps)
  - [Read complete test data of specific DUTs](#read-complete-test-data-of-specific-duts)
      - [From `DUT Summary`](#from-dut-summary)
      - [From `Test Summary`](#from-test-summary)
      - [From Plots](#from-plots)
  - [Generating an Excel report](#generating-an-excel-report)
  - [Settings](#settings)
  - [Utilities](#utilities)
      - [Load / Save Session](#load--save-session)
      - [Add Font](#add-font)
      - [Converter](#converter)
- [**Having issues?**](#having-issues)
- [**Acknowledgements**](#acknowledgements)
- [**License**](#license)
- [**Download**](#download)
- [**Contributions**](#contributions)


## Build

1. Install Python 3.9+ and [Rust](https://www.rust-lang.org/tools/install)
2. Install python modules, `maturin` is required to build `rust_stdf_helper`.

```
pip install -r requirements.txt
pip install maturin
```

3. Build `rust_stdf_helper`

```
cd ./deps/rust_stdf_helper
maturin build -f -r
```

4. Install `rust_stdf_helper`, the wheel is located in `target/wheels/`.
```
pip install /path/to/whl/file
```

5. You can run `STDF-Viewer.py` directly, or using your favorite tool to bundle it to an executable.


## Usage

### **Open STDF files**

STDF Viewer supports files under STDF V4 and V4-2007 Specification, ZIP*, GZ and BZIP compressed STDF files can also be opened without decompression.

STDF files can be opened in 3 ways:

1. Select STDF files in a file dialog by clicking `open` button on the toolbar.
2. Right click on a STDF file and select STDF Viewer to open.
3. Drag STDF files into the GUI to open.

If multiple STDF files are selected, compare mode is automatically enabled, you will see multiple sections in a single plot

***Note**: ZIP format support is limited, works only if:*
- *ZIP file is not password protected.*
- *Contains only 1 file per ZIP.*
- ~~*ZIP file is created using `DEFLATE` compression method, which is the default on popular OSs' native zip tool.*~~ (V4.0.0)

<br>

### **Merge STDF files**

(Introduced in V4.0.0) Open the merge panel by clicking `Merge` button on the toolbar, user can add multiple files in merge groups,
files in a same group will be merged into a single file and index 0 is regarded as the first file in a group.

<img src="screenshots/merge panel.png">

Adding multiple merge groups is also supported, in case you'd like to compare merge groups.

<img src="screenshots/merge result.png">

<br>

### **Find failed test items**

By clicking the `Fail Marker` button on the toolbar can paint all failed test items in <span style="color:red">red</span>, if the `Find Low Cpk` is enabled in `Settings`, test items with Cpk lower than the threshold (can be set in `Settings`) will be painted in <span style="color:orange">orange</span>.

<img src="screenshots/failmarker.png">

<br>

### **Looking for DUTs' info**

DUTs' info can be viewed in `Detailed Info` -> `DUT Summary`. Each line in the table represents a single DUT, and it will be marked in <span style="color:red">red</span> if this DUT is failed.

(Introduced in V4.0.0) Superseded DUTs will be marked in grey. A normal stdf file will contains several K DUTs, in order to improve performance, DUT Summary will not load all DUTs to the table, but if you want to load all, right click on the table and select `Fetch All Rows`.

If STDF files contain multiple heads and/or sites, you may also filter out the DUTs of non-interest by selecting specific heads and/or sites in `Site/Head Selection`.

DUTs' info can be sorted by any columns. For instance, the screenshot below showing the result of sorting the DUTs by Part ID.

<img src="screenshots/dut summary.png">

<br>

### **Display GDRs & DTRs info**

All the GDR (Generic Data Record) and DTR (Datalog Text Record) will be listed in `Detailed Info` -> `GDR & DTR Summary`. The precise location of GDR & DTR is hard to trace, the relative location compared to PIR/PRR is given instead.

For GDR, each line in the `Value` column represents a V1 data, which is displayed in the format of `{V1 index} {V1 data type}: {V1 data}`.

Same as DUT Summary table, use `Fetch All Rows` to load all data into the table.

*Note: Data of `Bn` & `Dn` type is shown in HEX string.*

<img src="screenshots/GDR DTR summary.png">

<br>

### **Analyzing test data**

***Importance Notice**: Functional Tests (FTR) have no test value, instead, the test flag is used as the test value for drawing trend charts and histograms*

All test items in the STDF file will be shown in the `Test Selection`, in which you can select single or multiple test item(s). The search box below can help you find test item(s) more easily.

Statistic (Cpk, mean, std dev, etc.) of the test items in the selected heads and sites is displayed in `Test Statistics`.

#### **Test data**
Select test item(s) and then navigate to `Detailed Info` -> `Test Summary`. Each row is a DUT that's been tested in the selected heads and sites, data of selected tests will be appended to the rightmost column.

<img src="screenshots/test summary.png">

#### **Trend chart**
Display interactive trend charts of test item(s), y axis is the value of the test item, x axis is the index of DUTs that's been tested in selected head and site. You can hover over the point to show more information.

<img src="screenshots/trend interactive.png">

If the test have PAT enabled, e.g. high/low limits in PTRs are changing over duts, the dynamic limits will be shown instead.

<img src="screenshots/trend dynamic limit.png">

#### **Histogram**
Display interactive histograms of test item(s), y axis is the test value distribution. ~~you can hover over the rectangle to display its data range and dut counts.~~

<img src="screenshots/histo.png">

<br>

### **Analyzing bin distribution**
Display histograms of dut counts of each hardware bin and software bin in selected heads and sites. 

`Test Statistic` table displays the dut counts, bin name, bin number and precentage, bins with DUT counts of 0 will be hidden.

<img src="screenshots/bin.png">

<br>

### **Viewing wafer maps**
If STDF files contain wafer information (WCR, WIR, WRR records), the `Wafer Map` tab will be enabled. 

There is a stacked wafer map at the top of `Wafer Selection` that summarizes the total count of fail dut in each (X, Y) coordinates of all wafermaps in the current file.

<img src="screenshots/wafer stacked.png">

Other entries in `Wafer Selection` represents the wafer maps in the file, color of each die is determined by its software bin.

<img src="screenshots/wafer.png">

You can hide some software bins by clicking icons in the legend.

<img src="screenshots/wafer hide.png">

<br>

### **Read complete test data of specific DUTs**
In some cases, it would be helpful to see the detailed test results of some DUTs, as shown below. It can be achieved by several methods in the STDF Viewer.

<img src="screenshots/dut data table.png">

#### **From `DUT Summary`**
Select row(s) of interest and right click, click `Read selected DUT data` in the context menu.

<img src="screenshots/dut summary read dut data.png">

#### **From `Test Summary`**
Select cell(s) of interest and right click, click `Read selected DUT data` in the context menu.

<img src="screenshots/test summary read dut data.png">

#### **From Plots**
Right click on a plot and select `Data Pick Mode`, select a region of interest then right click and select `Show Selected DUT Data`. Remember you can use legend icon to hide some data to help you select.

<img src="screenshots/trend interactive 2.png">

<img src="screenshots/histo interactive.png">

<img src="screenshots/bin interactive.png">

<img src="screenshots/wafer interactive.png">

<br>

### **Generating an Excel report**
Almost all information displayed on STDF Viewer can be exported to a Excel report.

<img src="screenshots/report content selection.png">
<img src="screenshots/report test selection.png">
<img src="screenshots/report site selection.png">

Each checkbox in `Report Content Selection` will be saved in a individual sheet in the report. 

- `File Info`: File properties, MIR, MRR, ATR, RDR and SDR inifo.
- `DUT Summary`: Content in DUT Summary table, test data will be added if test items are selected.
- `Trend Chart`: Trend Plot + Statistics.
- `Histogram`: Histogram Plot + Statistics.
- `Bin Chart`: Bin Plot + bin summary.
- `Wafer Map`: All Wafermap Plots.
- `Test Statistics`: Statistics of all selected test items.
- `GDR & DTR Summary`: All GDR and DTR info.

The numbers of figures/data in the report are based on numbers of tests in `Export Tests` and selected Heads and Sites.

<br>

### **Settings**
STDF Viewer offers a global setting UI, which can change the appearance of figures, colors of each sites/bins, etc. in STDF Viewer or the exported report. 

The description should be self-explanatory, feel free to play it around.

<img src="screenshots/setting.png">

### **Utilities**
There is a `Utilities` button on toolbar from V4.0.0.

<img src="screenshots/utilities.png">

#### **Load & Save Session**

You can save current parse cache as a session so that you don't have to reload STDF files again, it can be helpful if you need to access some STDF multiple times.

#### **Add Font**
This process is much simpler then previous releases. All you need to do is select a `.ttf` font and select it in `Settings`!

#### **Converter**
This tool can dump STDF records into a xlsx file, it can be used for debugging.

<br>

## Having issues?
If you have encountered any error, follow these steps to create a report:
1. Open STDF-Viewer and click `About` in the top-right corner.<img src="screenshots/how to open debug panel.png">
2. Click `debug` button to show the debug panel.<img src="screenshots/debug panel.png">
3. Click `Display Log File` to print all the error logs on the screen; If the error is file-related, click `STDF Record Type Reader` and select the file that triggers the error.
4. Click `Save Result` and create an issue on github.


## Acknowledgements

STDF Viewer uses code from the following open sources, much thanks to their authors.
 - [rust-stdf](https://github.com/noonchen/rust-stdf) <- I'm the author
 - [pyqtgraph](https://github.com/pyqtgraph/pyqtgraph)
 - [flate2](https://crates.io/crates/flate2)
 - [bzip2](https://crates.io/crates/bzip2)
 - [rusqlite](https://crates.io/crates/rusqlite)

Not used in version 4.0.0 and above:
 - ~~[minizip](https://www.winimage.com/zLibDll/minizip.html)~~
 - ~~[hashmap](https://gist.github.com/warmwaffles/6fb6786be7c86ed51fce)~~
 - ~~[message_queue](https://github.com/LnxPrgr3/message_queue)~~

 Not used in version 3.0.5 and above:
 - ~~[pystdf](https://github.com/cmars/pystdf)~~

<br>

## License

STDF Viewer is licensed under GPL V3.0, which means the software is free but I don't take any responsibilites if anything goes wrong due to the usage of the STDF Viewer, it is always safe to be skeptical about the results or images on the STDF Viewer.

The icons that I designed for STDF Viewer is licensed under [Attribution-NonCommercial 4.0 (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).

<br>

## Download

[Click here](https://github.com/noonchen/STDF-Viewer/releases)

<br>

## Contributions

Pull requests and bug reports are always welcomed. 