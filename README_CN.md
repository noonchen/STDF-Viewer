# STDF Viewer <img src="screenshots/stdfViewer.png" height=50>

[![build](https://github.com/noonchen/STDF-Viewer/actions/workflows/build.yml/badge.svg)](https://github.com/noonchen/STDF-Viewer/actions/workflows/build.yml)  [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/noonchen/STDF-Viewer.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/noonchen/STDF-Viewer/context:python)  [![version](https://img.shields.io/github/v/release/noonchen/STDF-Viewer?include_prereleases)](https://github.com/noonchen/STDF-Viewer/releases/latest)  [![downloads](https://img.shields.io/github/downloads/noonchen/STDF-Viewer/total?label=total%20downloads)](https://github.com/noonchen/STDF-Viewer/releases)  [![license](https://img.shields.io/github/license/noonchen/STDF-Viewer)](https://github.com/noonchen/STDF-Viewer/blob/main/LICENSE)

STDF Viewer是一款用于分析半导体测试STDF报告的免费、高效的图形化界面程序。

作者：Noon Chen <chennoon233@foxmail.com>

| [English](README.md) |

<img src="screenshots/mainUI.png">

## 目录
- [使用方法](#使用方法)
  - [**打开STDF文件**](#打开stdf文件)
  - [**寻找失效测项**](#寻找失效测项)
  - [**查看DUT测试信息**](#查看dut测试信息)
  - [**显示GDR和DTR信息**](#显示gdr和dtr信息)
  - [**分析测试数据**](#分析测试数据)
    - [**测试原始数据**](#测试原始数据)
    - [**趋势图**](#趋势图)
    - [**直方图**](#直方图)
  - [**Bin桶分布**](#bin桶分布)
  - [**查看晶圆图**](#查看晶圆图)
  - [**读取特定DUT的所有测试数据**](#读取特定dut的所有测试数据)
    - [**在`DUT详情`中**](#在dut详情中)
    - [**在`数据详情`中**](#在数据详情中)
    - [**在`趋势图`中**](#在趋势图中)
    - [**在`直方图`中**](#在直方图中)
    - [**在`Bin桶分布`中**](#在bin桶分布中)
    - [**在`晶圆图`中**](#在晶圆图中)
  - [**生成Excel报告**](#生成excel报告)
  - [**设置**](#设置)
    - [**更改字体**](#更改字体)
- [遇到问题？](#遇到问题)
- [鸣谢](#鸣谢)
- [软件许可证](#软件许可证)
- [下载](#下载)
- [合作](#合作)

## 使用方法

### **打开STDF文件**

STDF Viewer可处理的文件为[第4套标准的STDF](http://www.kanwoda.com/wp-content/uploads/2015/05/std-spec.pdf)，ZIP*、GZ以及BZIP压缩的STDF文件可以不用解压直接打开。

打开的方式有三种:

1. 打开软件后点击工具栏的`打开`选择文件。
2. 文件右键选择用STDF Viewer打开（macOS由于pyinstaller的原因暂时不支持）。
3. 将文件直接拖到程序界面上。

***注意**: ZIP格式的STDF文件支持有限，需要满足以下条件:*
- *没有密码*
- *一个ZIP只包含一个文件*
- *ZIP的压缩方法为`DEFLATE`，这是各个平台的主流的压缩方式*

<br>

### **寻找失效测项**

点击工具栏的`标记失效`可以把所有存在失效测项标为<span style="color:red">红色</span>，如果在`设置`里开启了`搜索低Cpk测项`，Cpk低于阈值（也可在`设置`中设置）的测项会标为<span style="color:orange">橙色</span>。

<img src="screenshots/failmarker.png">

<br>

### **查看DUT测试信息**

DUT测试信息位于`STDF信息` -> `DUT详情`。表格中每行代表一个DUT，失效的DUT会被标为<span style="color:red">红色</span>。

<img src="screenshots/dut summary.png">

如果STDF包含多head/site测试数据，显示的DUT会根据`选择Site/Head`进行过滤。

DUT信息可以按照每列进行排列，点击对应列即可。

<img src="screenshots/dut summary sorting.png">

<br>

### **显示GDR和DTR信息**

所有GDR (Generic Data Record)和DTR (Datalog Text Record) 数据列在`STDF信息` -> `GDR & DTR汇总`中。这两种Record的精确位置不好确定，表中给出了相对于PIR/PRR的位置。

GDR的`值`的每一行代表一个V1数据，按照`{V1序列} {V1数据类型}: {V1数据}`的格式进行打印。

*注意：`Bn`和`Dn`格式的数据使用十六进制进行表示*

<img src="screenshots/GDR DTR summary.png">

<br>

### **分析测试数据**

***提示**: 功能测试 FTR 没有测试值，在趋势图和直方图中用的是FTR的测试标识（Test Flag）进行绘图*

STDF文件中所有的测项会显示在`选择测项`，可以多选。下方提供搜索框进行过滤。

测项的统计信息（Cpk、平均值、方差等）显示在`统计信息`中。

#### **测试原始数据**
选择测项后在`STDF信息` -> `数据详情`查看。表格中每行代表一个DUT，每列代表一个测项。

<img src="screenshots/test summary.png">

#### **趋势图**
显示测试值随DUT变化的趋势图，横轴为测试值，横轴为所选的head/site包含的所有DUT的序号。鼠标停留到数据点上可以查看详细数据。

<img src="screenshots/trend interactive.png">

如果STDF中测项开启了PAT，动态的上下限也会画出来。

<img src="screenshots/trend dynamic limit.png">

#### **直方图**
显示测项的数据分布，横轴为测试值，纵轴为每个区间的DUT个数。鼠标停留到区间上可以查看具体计数。

<img src="screenshots/histo.png">

<br>

### **Bin桶分布**
显示HBIN和SBIN桶的分布。

`统计信息`为每个Bin编号、名称和百分比，空的Bin自动隐藏.

<img src="screenshots/bin.png">

<br>

### **查看晶圆图**
`晶圆图`只会在STDF文件存在晶圆测试信息（WCR、WIR、WRR）的时候开启。 

`选择晶圆`的第一行（`Stacked Wafer Map`）是当前文件里失效个数的分布图，每个(X, Y)坐标的数字代表这个失效的DUT的个数。

<img src="screenshots/wafer stacked.png">

`选择晶圆`的其它行则是文件中记录的晶圆数据，每个方块的颜色由SBIN决定，可在设置中自定义。

<img src="screenshots/wafer.png">

<br>

### **读取特定DUT的所有测试数据**
有时你可能需要某几个DUT的所有测项的值，如下图所示，在STDF Viewer中有多种方式可以实现。

<img src="screenshots/dut data table.png">

#### **在`DUT详情`中**
选择行后，右键选择`读取DUT详细数据`。

<img src="screenshots/dut summary read dut data.png">

#### **在`数据详情`中**
选择单元格后，右键选`读取DUT详细数据`。

<img src="screenshots/test summary read dut data.png">

#### **在`趋势图`中**
点击图中数据点进行选择（或者按住`Shift`进行多选），选择的点会标为*`S`*，按`Enter`即可。

<img src="screenshots/trend interactive 2.png">

#### **在`直方图`中**
点击图中的长条进行选择（或者按住`Shift`进行多选），选中的长条显示为<span style="color:red">红色</span>，按`Enter`后显示所有测试值在所选范围内的DUT。

<img src="screenshots/histo interactive.png">

#### **在`Bin桶分布`中**
点击对应的Bin图形（按住`Shift`多选），按`Enter`显示所有分在所选Bin的DUT。

<img src="screenshots/bin interactive.png">

#### **在`晶圆图`中**
点击对应坐标的正方形后按`Enter`调出。

<img src="screenshots/wafer interactive.png">

<br>

### **生成Excel报告**
程序显示的内容基本上都可以导出到报告里。

<img src="screenshots/report content selection.png">
<img src="screenshots/report test selection.png">
<img src="screenshots/report site selection.png">

`Report Content Selection`的每个选项对应Excel里的sheet。

- `文件详情`：文件信息，包括MIR、MRR、ATR、RDR和SDR
- `DUT详情`：DUT信息
- `趋势图`：趋势图+统计信息
- `直方图`：直方图+统计信息
- `Bin桶分布`：Bin桶分布+Bin桶统计
- `晶圆图`：所有晶圆图
- `统计信息`：所选测项的统计信息
- `GDR & DTR汇总`：所有的GDR和DTR

报告的图片/数据数量取决于`已选测项`的内容和head/site的选择。

<br>

### **设置**
STDF Viewer提供了全局设置界面，可以用来更改程序界面中或导出报告中对图像元素、site/bin的颜色等等，可自行尝试修改。

<img src="screenshots/setting.png">

#### **更改字体**
用户可以自定义界面和图像中的字体。

首先需要重命名 .ttf 字体文件：
- 中文字体: 加前缀 `cn_`
- 英文字体: 加前缀 `en_`

例如，某个字体文件名为`testfontforchinese.ttf`作为中文的默认字体，要将文件名改为`cn_testfontforchinese.ttf`，其他语言的字体不受影响。

把重命名后的文件复制到`/fonts`文件夹中，位置如下：
- Windows：程序旁边
- macOS：`STDF Viewer.app/Contents/Resources/fonts`
- Ubuntu：`/usr/local/bin/STDF-Viewer/fonts`

重启软件后生效。

<img src="screenshots/change fonts.png">

<br>

## 遇到问题？
如果在使用过程中遇到问题，按照以下步骤进行：
1. 打开STDF-Viewer后点击右上角的`关于`。<img src="screenshots/how to open debug panel.png">
2. 点击`调试`按钮打开调试界面。<img src="screenshots/debug panel.png">
3. 点击`显示Log内容`打印出历史报告；如果错误是和文件有关，点击`分析文件Record类型`后选择出错的文件。
4. 点击`保存结果`保存结果，在GitHub上创建个issue。


## 鸣谢

STDF Viewer使用了下列开源项目的代码，感谢作者们：
 - [zlib](https://zlib.net/)
 - [minizip](https://www.winimage.com/zLibDll/minizip.html)
 - [bzip2](https://www.sourceware.org/bzip2/)
 - [sqlite3](https://www.sqlite.org/)
 - [hashmap](https://gist.github.com/warmwaffles/6fb6786be7c86ed51fce)
 - [message_queue](https://github.com/LnxPrgr3/message_queue)

 3.0.5及新版本不再使用：
 - ~~[pystdf](https://github.com/cmars/pystdf)~~

<br>

## 软件许可证

STDF Viewer采用GPL V3.0，程序完全免费，由于使用本软件导致的任何问题，作者概不负责，也请使用者抱着怀疑的态度使用本软件。

我为STDF Viewer设计的图标采用[Attribution-NonCommercial 4.0 (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/)许可。

<br>

## 下载

[点击这里](https://github.com/noonchen/STDF-Viewer/releases)

<br>

## 合作

欢迎各种PR和Issue～