# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/nochenon/Library/Mobile Documents/iCloud~com~omz-software~Pythonista3/Documents/My Projects/STDF Viewer/deps/ui/stdfViewer_MainWindows.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1440, 847)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(11)
        MainWindow.setFont(font)
        MainWindow.setStyleSheet("QScrollArea { background: transparent; }\n"
"QScrollArea > QWidget > QWidget { background: transparent; }\n"
"QScrollArea > QWidget > QScrollBar { background: palette(base); }\n"
"\n"
"QScrollBar:vertical {\n"
"border: 0px;\n"
"background:transparent;\n"
"width:5px;\n"
"margin: 0px 0px 0px 0px;\n"
"}\n"
" QScrollBar::handle:vertical {\n"
"background: rgb(128, 128, 128);\n"
"min-height: 10px;\n"
"}\n"
"\n"
"QScrollBar::add-line:vertical {\n"
"background: transparent;\n"
"height: 0px;\n"
"subcontrol-position: bottom;\n"
"subcontrol-origin: margin;\n"
"}\n"
"QScrollBar::sub-line:vertical {\n"
"background: transparent;\n"
"height: 0 px;\n"
"subcontrol-position: top;\n"
"subcontrol-origin: margin;\n"
"}\n"
"QScrollBar:horizontal {\n"
"border: 0px;\n"
"background:transparent;\n"
"height:5px;\n"
"margin: 0px 0px 0px 0px;\n"
"}\n"
" QScrollBar::handle:horizontal {\n"
"background: rgb(128, 128, 128);\n"
"min-width: 10px;\n"
"}\n"
"\n"
"QScrollBar::add-line:horizontal {\n"
"background: transparent;\n"
"height: 0px;\n"
"subcontrol-position: right;\n"
"subcontrol-origin: margin;\n"
"}\n"
"QScrollBar::sub-line:horizontal {\n"
"background: transparent;\n"
"height: 0 px;\n"
"subcontrol-position: left;\n"
"subcontrol-origin: margin;\n"
"}\n"
"QListView::item { height: 20px; }")
        MainWindow.setIconSize(QtCore.QSize(30, 30))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.LR_splitter = QtWidgets.QSplitter(self.centralwidget)
        self.LR_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.LR_splitter.setOpaqueResize(False)
        self.LR_splitter.setHandleWidth(10)
        self.LR_splitter.setChildrenCollapsible(True)
        self.LR_splitter.setObjectName("LR_splitter")
        self.Selection_splitter = QtWidgets.QSplitter(self.LR_splitter)
        self.Selection_splitter.setOrientation(QtCore.Qt.Vertical)
        self.Selection_splitter.setHandleWidth(10)
        self.Selection_splitter.setChildrenCollapsible(False)
        self.Selection_splitter.setObjectName("Selection_splitter")
        self.Selection_stackedWidget = QtWidgets.QStackedWidget(self.Selection_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Selection_stackedWidget.sizePolicy().hasHeightForWidth())
        self.Selection_stackedWidget.setSizePolicy(sizePolicy)
        self.Selection_stackedWidget.setObjectName("Selection_stackedWidget")
        self.FT_page = QtWidgets.QWidget()
        self.FT_page.setObjectName("FT_page")
        self.verticalLayout_13 = QtWidgets.QVBoxLayout(self.FT_page)
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_13.setObjectName("verticalLayout_13")
        self.test_selection = QtWidgets.QGroupBox(self.FT_page)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.test_selection.sizePolicy().hasHeightForWidth())
        self.test_selection.setSizePolicy(sizePolicy)
        self.test_selection.setObjectName("test_selection")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.test_selection)
        self.verticalLayout_5.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout_5.setSpacing(6)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.TestList = QtWidgets.QListView(self.test_selection)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.TestList.sizePolicy().hasHeightForWidth())
        self.TestList.setSizePolicy(sizePolicy)
        self.TestList.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.TestList.setFont(font)
        self.TestList.setObjectName("TestList")
        self.verticalLayout_5.addWidget(self.TestList)
        self.horizontalLayout_search = QtWidgets.QHBoxLayout()
        self.horizontalLayout_search.setObjectName("horizontalLayout_search")
        self.Search = QtWidgets.QLabel(self.test_selection)
        self.Search.setObjectName("Search")
        self.horizontalLayout_search.addWidget(self.Search)
        self.SearchBox = QtWidgets.QLineEdit(self.test_selection)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.SearchBox.sizePolicy().hasHeightForWidth())
        self.SearchBox.setSizePolicy(sizePolicy)
        self.SearchBox.setMinimumSize(QtCore.QSize(160, 0))
        self.SearchBox.setObjectName("SearchBox")
        self.horizontalLayout_search.addWidget(self.SearchBox)
        self.ClearButton = QtWidgets.QPushButton(self.test_selection)
        self.ClearButton.setObjectName("ClearButton")
        self.horizontalLayout_search.addWidget(self.ClearButton)
        self.verticalLayout_5.addLayout(self.horizontalLayout_search)
        self.verticalLayout_13.addWidget(self.test_selection)
        self.Selection_stackedWidget.addWidget(self.FT_page)
        self.CP_page = QtWidgets.QWidget()
        self.CP_page.setObjectName("CP_page")
        self.verticalLayout_15 = QtWidgets.QVBoxLayout(self.CP_page)
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_15.setObjectName("verticalLayout_15")
        self.wafer_selection = QtWidgets.QGroupBox(self.CP_page)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.wafer_selection.sizePolicy().hasHeightForWidth())
        self.wafer_selection.setSizePolicy(sizePolicy)
        self.wafer_selection.setObjectName("wafer_selection")
        self.verticalLayout_14 = QtWidgets.QVBoxLayout(self.wafer_selection)
        self.verticalLayout_14.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout_14.setSpacing(6)
        self.verticalLayout_14.setObjectName("verticalLayout_14")
        self.WaferList = QtWidgets.QListView(self.wafer_selection)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.WaferList.sizePolicy().hasHeightForWidth())
        self.WaferList.setSizePolicy(sizePolicy)
        self.WaferList.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.WaferList.setFont(font)
        self.WaferList.setObjectName("WaferList")
        self.verticalLayout_14.addWidget(self.WaferList)
        self.verticalLayout_15.addWidget(self.wafer_selection)
        self.Selection_stackedWidget.addWidget(self.CP_page)
        self.site_head_selection = QtWidgets.QTabWidget(self.Selection_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setHeightForWidth(self.site_head_selection.sizePolicy().hasHeightForWidth())
        self.site_head_selection.setSizePolicy(sizePolicy)
        self.site_head_selection.setMaximumSize(QtCore.QSize(16777215, 81))
        self.site_head_selection.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.site_head_selection.setObjectName("site_head_selection")
        self.site_selection_tab = QtWidgets.QWidget()
        self.site_selection_tab.setObjectName("site_selection_tab")
        self.horizontalLayout_site_sel = QtWidgets.QHBoxLayout(self.site_selection_tab)
        self.horizontalLayout_site_sel.setContentsMargins(12, 12, 12, 12)
        self.horizontalLayout_site_sel.setSpacing(0)
        self.horizontalLayout_site_sel.setObjectName("horizontalLayout_site_sel")
        self.scrollArea_site_selection = QtWidgets.QScrollArea(self.site_selection_tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_site_selection.sizePolicy().hasHeightForWidth())
        self.scrollArea_site_selection.setSizePolicy(sizePolicy)
        self.scrollArea_site_selection.setMinimumSize(QtCore.QSize(0, 32))
        self.scrollArea_site_selection.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea_site_selection.setLineWidth(0)
        self.scrollArea_site_selection.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea_site_selection.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea_site_selection.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.scrollArea_site_selection.setWidgetResizable(True)
        self.scrollArea_site_selection.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.scrollArea_site_selection.setObjectName("scrollArea_site_selection")
        self.site_selection_contents = QtWidgets.QWidget()
        self.site_selection_contents.setGeometry(QtCore.QRect(0, 0, 295, 37))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.site_selection_contents.sizePolicy().hasHeightForWidth())
        self.site_selection_contents.setSizePolicy(sizePolicy)
        self.site_selection_contents.setObjectName("site_selection_contents")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.site_selection_contents)
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.horizontalLayout_site_hspacer = QtWidgets.QHBoxLayout()
        self.horizontalLayout_site_hspacer.setObjectName("horizontalLayout_site_hspacer")
        self.gridLayout_site_select = QtWidgets.QGridLayout()
        self.gridLayout_site_select.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.gridLayout_site_select.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_site_select.setSpacing(10)
        self.gridLayout_site_select.setObjectName("gridLayout_site_select")
        self.All = QtWidgets.QCheckBox(self.site_selection_contents)
        self.All.setChecked(True)
        self.All.setObjectName("All")
        self.gridLayout_site_select.addWidget(self.All, 0, 0, 1, 1)
        self.checkAll = QtWidgets.QPushButton(self.site_selection_contents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkAll.sizePolicy().hasHeightForWidth())
        self.checkAll.setSizePolicy(sizePolicy)
        self.checkAll.setMinimumSize(QtCore.QSize(65, 0))
        self.checkAll.setMaximumSize(QtCore.QSize(65, 16777215))
        self.checkAll.setObjectName("checkAll")
        self.gridLayout_site_select.addWidget(self.checkAll, 0, 1, 1, 1)
        self.cancelAll = QtWidgets.QPushButton(self.site_selection_contents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cancelAll.sizePolicy().hasHeightForWidth())
        self.cancelAll.setSizePolicy(sizePolicy)
        self.cancelAll.setMinimumSize(QtCore.QSize(65, 0))
        self.cancelAll.setMaximumSize(QtCore.QSize(65, 16777215))
        self.cancelAll.setObjectName("cancelAll")
        self.gridLayout_site_select.addWidget(self.cancelAll, 0, 2, 1, 1)
        self.horizontalLayout_site_hspacer.addLayout(self.gridLayout_site_select)
        spacerItem = QtWidgets.QSpacerItem(30, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_site_hspacer.addItem(spacerItem)
        self.verticalLayout_7.addLayout(self.horizontalLayout_site_hspacer)
        spacerItem1 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_7.addItem(spacerItem1)
        self.scrollArea_site_selection.setWidget(self.site_selection_contents)
        self.horizontalLayout_site_sel.addWidget(self.scrollArea_site_selection)
        self.site_head_selection.addTab(self.site_selection_tab, "")
        self.head_selection_tab = QtWidgets.QWidget()
        self.head_selection_tab.setObjectName("head_selection_tab")
        self.horizontalLayout_head_sel = QtWidgets.QHBoxLayout(self.head_selection_tab)
        self.horizontalLayout_head_sel.setContentsMargins(12, 12, 12, 12)
        self.horizontalLayout_head_sel.setSpacing(0)
        self.horizontalLayout_head_sel.setObjectName("horizontalLayout_head_sel")
        self.verticalLayout_header = QtWidgets.QVBoxLayout()
        self.verticalLayout_header.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_header.setSpacing(0)
        self.verticalLayout_header.setObjectName("verticalLayout_header")
        self.horizontalLayout_head_hspacer = QtWidgets.QHBoxLayout()
        self.horizontalLayout_head_hspacer.setObjectName("horizontalLayout_head_hspacer")
        self.gridLayout_head_select = QtWidgets.QGridLayout()
        self.gridLayout_head_select.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.gridLayout_head_select.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_head_select.setSpacing(10)
        self.gridLayout_head_select.setObjectName("gridLayout_head_select")
        self.horizontalLayout_head_hspacer.addLayout(self.gridLayout_head_select)
        spacerItem2 = QtWidgets.QSpacerItem(30, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_head_hspacer.addItem(spacerItem2)
        self.verticalLayout_header.addLayout(self.horizontalLayout_head_hspacer)
        spacerItem3 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_header.addItem(spacerItem3)
        self.horizontalLayout_head_sel.addLayout(self.verticalLayout_header)
        self.site_head_selection.addTab(self.head_selection_tab, "")
        self.Tab_Table_splitter = QtWidgets.QSplitter(self.LR_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Tab_Table_splitter.sizePolicy().hasHeightForWidth())
        self.Tab_Table_splitter.setSizePolicy(sizePolicy)
        self.Tab_Table_splitter.setOrientation(QtCore.Qt.Vertical)
        self.Tab_Table_splitter.setOpaqueResize(False)
        self.Tab_Table_splitter.setHandleWidth(5)
        self.Tab_Table_splitter.setChildrenCollapsible(True)
        self.Tab_Table_splitter.setObjectName("Tab_Table_splitter")
        self.tabControl = QtWidgets.QTabWidget(self.Tab_Table_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(4)
        sizePolicy.setHeightForWidth(self.tabControl.sizePolicy().hasHeightForWidth())
        self.tabControl.setSizePolicy(sizePolicy)
        self.tabControl.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.tabControl.setObjectName("tabControl")
        self.info_tab = QtWidgets.QWidget()
        self.info_tab.setObjectName("info_tab")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.info_tab)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_info = QtWidgets.QHBoxLayout()
        self.horizontalLayout_info.setContentsMargins(30, 20, 30, 20)
        self.horizontalLayout_info.setObjectName("horizontalLayout_info")
        self.infoBox = QtWidgets.QToolBox(self.info_tab)
        self.infoBox.setStyleSheet("QToolBox::tab {\n"
"    background: #BEBDBF;\n"
"    border-radius: 3px;\n"
"    color: black;\n"
"}\n"
"\n"
"QToolBox::tab:selected { /* italicize selected tabs */\n"
"    color: white;\n"
"    background: #009deb\n"
"}")
        self.infoBox.setObjectName("infoBox")
        self.fileInfoPage = QtWidgets.QWidget()
        self.fileInfoPage.setGeometry(QtCore.QRect(0, 0, 1025, 423))
        self.fileInfoPage.setObjectName("fileInfoPage")
        self.verticalLayout_11 = QtWidgets.QVBoxLayout(self.fileInfoPage)
        self.verticalLayout_11.setContentsMargins(20, 10, 20, -1)
        self.verticalLayout_11.setObjectName("verticalLayout_11")
        self.fileInfoTable = QtWidgets.QTableView(self.fileInfoPage)
        self.fileInfoTable.setStyleSheet("QTableView {\n"
"background: transparent;\n"
"font: 13pt \"Courier\";}\n"
"\n"
"")
        self.fileInfoTable.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.fileInfoTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.fileInfoTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.fileInfoTable.setProperty("showDropIndicator", False)
        self.fileInfoTable.setDragDropOverwriteMode(False)
        self.fileInfoTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.fileInfoTable.setTextElideMode(QtCore.Qt.ElideNone)
        self.fileInfoTable.setShowGrid(False)
        self.fileInfoTable.setGridStyle(QtCore.Qt.NoPen)
        self.fileInfoTable.setCornerButtonEnabled(False)
        self.fileInfoTable.setObjectName("fileInfoTable")
        self.fileInfoTable.horizontalHeader().setVisible(False)
        self.fileInfoTable.verticalHeader().setVisible(False)
        self.verticalLayout_11.addWidget(self.fileInfoTable)
        self.infoBox.addItem(self.fileInfoPage, "")
        self.dutInfoPage = QtWidgets.QWidget()
        self.dutInfoPage.setGeometry(QtCore.QRect(0, 0, 1025, 423))
        self.dutInfoPage.setObjectName("dutInfoPage")
        self.verticalLayout_12 = QtWidgets.QVBoxLayout(self.dutInfoPage)
        self.verticalLayout_12.setObjectName("verticalLayout_12")
        self.dutInfoTable = QtWidgets.QTableView(self.dutInfoPage)
        self.dutInfoTable.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.dutInfoTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.dutInfoTable.setObjectName("dutInfoTable")
        self.dutInfoTable.verticalHeader().setVisible(False)
        self.verticalLayout_12.addWidget(self.dutInfoTable)
        self.infoBox.addItem(self.dutInfoPage, "")
        self.rawDataPage = QtWidgets.QWidget()
        self.rawDataPage.setGeometry(QtCore.QRect(0, 0, 1025, 423))
        self.rawDataPage.setObjectName("rawDataPage")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.rawDataPage)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.rawDataTable = QtWidgets.QTableView(self.rawDataPage)
        self.rawDataTable.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.rawDataTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.rawDataTable.setObjectName("rawDataTable")
        self.rawDataTable.verticalHeader().setVisible(False)
        self.verticalLayout_9.addWidget(self.rawDataTable)
        self.infoBox.addItem(self.rawDataPage, "")
        self.datalogPage = QtWidgets.QWidget()
        self.datalogPage.setGeometry(QtCore.QRect(0, 0, 1025, 423))
        self.datalogPage.setObjectName("datalogPage")
        self.verticalLayout_18 = QtWidgets.QVBoxLayout(self.datalogPage)
        self.verticalLayout_18.setObjectName("verticalLayout_18")
        self.datalogTable = QtWidgets.QTableView(self.datalogPage)
        self.datalogTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.datalogTable.setObjectName("datalogTable")
        self.verticalLayout_18.addWidget(self.datalogTable)
        self.infoBox.addItem(self.datalogPage, "")
        self.horizontalLayout_info.addWidget(self.infoBox)
        self.verticalLayout.addLayout(self.horizontalLayout_info)
        self.tabControl.addTab(self.info_tab, "")
        self.trend_tab = QtWidgets.QWidget()
        self.trend_tab.setObjectName("trend_tab")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.trend_tab)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.horizontalLayout_trend = QtWidgets.QHBoxLayout()
        self.horizontalLayout_trend.setObjectName("horizontalLayout_trend")
        self.scrollArea_trend = QtWidgets.QScrollArea(self.trend_tab)
        self.scrollArea_trend.setAutoFillBackground(False)
        self.scrollArea_trend.setStyleSheet("background-color: white")
        self.scrollArea_trend.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea_trend.setWidgetResizable(True)
        self.scrollArea_trend.setObjectName("scrollArea_trend")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 1083, 581))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.verticalLayout_trend = QtWidgets.QVBoxLayout()
        self.verticalLayout_trend.setObjectName("verticalLayout_trend")
        self.verticalLayout_8.addLayout(self.verticalLayout_trend)
        self.scrollArea_trend.setWidget(self.scrollAreaWidgetContents)
        self.horizontalLayout_trend.addWidget(self.scrollArea_trend)
        self.verticalLayout_4.addLayout(self.horizontalLayout_trend)
        self.tabControl.addTab(self.trend_tab, "")
        self.histo_tab = QtWidgets.QWidget()
        self.histo_tab.setObjectName("histo_tab")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.histo_tab)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_histo = QtWidgets.QHBoxLayout()
        self.horizontalLayout_histo.setObjectName("horizontalLayout_histo")
        self.scrollArea_histo = QtWidgets.QScrollArea(self.histo_tab)
        self.scrollArea_histo.setStyleSheet("background-color: white")
        self.scrollArea_histo.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea_histo.setWidgetResizable(True)
        self.scrollArea_histo.setObjectName("scrollArea_histo")
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 1083, 581))
        self.scrollAreaWidgetContents_2.setStyleSheet("")
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.verticalLayout_histo = QtWidgets.QVBoxLayout()
        self.verticalLayout_histo.setObjectName("verticalLayout_histo")
        self.verticalLayout_6.addLayout(self.verticalLayout_histo)
        self.scrollArea_histo.setWidget(self.scrollAreaWidgetContents_2)
        self.horizontalLayout_histo.addWidget(self.scrollArea_histo)
        self.verticalLayout_3.addLayout(self.horizontalLayout_histo)
        self.tabControl.addTab(self.histo_tab, "")
        self.bin_tab = QtWidgets.QWidget()
        self.bin_tab.setObjectName("bin_tab")
        self.verticalLayout_10 = QtWidgets.QVBoxLayout(self.bin_tab)
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.horizontalLayout_bin = QtWidgets.QHBoxLayout()
        self.horizontalLayout_bin.setObjectName("horizontalLayout_bin")
        self.scrollArea_bin = QtWidgets.QScrollArea(self.bin_tab)
        self.scrollArea_bin.setStyleSheet("background-color: white")
        self.scrollArea_bin.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea_bin.setWidgetResizable(True)
        self.scrollArea_bin.setObjectName("scrollArea_bin")
        self.scrollAreaWidgetContents_4 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_4.setGeometry(QtCore.QRect(0, 0, 1083, 581))
        self.scrollAreaWidgetContents_4.setObjectName("scrollAreaWidgetContents_4")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents_4)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.verticalLayout_bin = QtWidgets.QVBoxLayout()
        self.verticalLayout_bin.setObjectName("verticalLayout_bin")
        self.horizontalLayout_3.addLayout(self.verticalLayout_bin)
        self.scrollArea_bin.setWidget(self.scrollAreaWidgetContents_4)
        self.horizontalLayout_bin.addWidget(self.scrollArea_bin)
        self.verticalLayout_10.addLayout(self.horizontalLayout_bin)
        self.tabControl.addTab(self.bin_tab, "")
        self.wafer_tab = QtWidgets.QWidget()
        self.wafer_tab.setObjectName("wafer_tab")
        self.verticalLayout_17 = QtWidgets.QVBoxLayout(self.wafer_tab)
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_17.setObjectName("verticalLayout_17")
        self.horizontalLayout_wafer = QtWidgets.QHBoxLayout()
        self.horizontalLayout_wafer.setObjectName("horizontalLayout_wafer")
        self.scrollArea_wafer = QtWidgets.QScrollArea(self.wafer_tab)
        self.scrollArea_wafer.setStyleSheet("background-color: white")
        self.scrollArea_wafer.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea_wafer.setWidgetResizable(True)
        self.scrollArea_wafer.setObjectName("scrollArea_wafer")
        self.scrollAreaWidgetContents_5 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_5.setGeometry(QtCore.QRect(0, 0, 1083, 581))
        self.scrollAreaWidgetContents_5.setObjectName("scrollAreaWidgetContents_5")
        self.verticalLayout_16 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_5)
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_16.setObjectName("verticalLayout_16")
        self.verticalLayout_wafer = QtWidgets.QVBoxLayout()
        self.verticalLayout_wafer.setObjectName("verticalLayout_wafer")
        self.verticalLayout_16.addLayout(self.verticalLayout_wafer)
        self.scrollArea_wafer.setWidget(self.scrollAreaWidgetContents_5)
        self.horizontalLayout_wafer.addWidget(self.scrollArea_wafer)
        self.verticalLayout_17.addLayout(self.horizontalLayout_wafer)
        self.tabControl.addTab(self.wafer_tab, "")
        self.groupBox_stats = QtWidgets.QGroupBox(self.Tab_Table_splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.groupBox_stats.sizePolicy().hasHeightForWidth())
        self.groupBox_stats.setSizePolicy(sizePolicy)
        self.groupBox_stats.setObjectName("groupBox_stats")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox_stats)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.dataTable = QtWidgets.QTableView(self.groupBox_stats)
        self.dataTable.setStyleSheet("font: 9pt;")
        self.dataTable.setObjectName("dataTable")
        self.dataTable.verticalHeader().setVisible(True)
        self.verticalLayout_2.addWidget(self.dataTable)
        self.horizontalLayout.addWidget(self.LR_splitter)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(11)
        self.statusbar.setFont(font)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QtWidgets.QToolBar(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolBar.sizePolicy().hasHeightForWidth())
        self.toolBar.setSizePolicy(sizePolicy)
        self.toolBar.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(16)
        self.toolBar.setFont(font)
        self.toolBar.setAutoFillBackground(False)
        self.toolBar.setStyleSheet("##background-color:rgb(71, 187, 241)")
        self.toolBar.setMovable(False)
        self.toolBar.setIconSize(QtCore.QSize(20, 20))
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolBar.setFloatable(False)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionOpen = QtWidgets.QAction(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.actionOpen.setFont(font)
        self.actionOpen.setObjectName("actionOpen")
        self.actionExport = QtWidgets.QAction(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.actionExport.setFont(font)
        self.actionExport.setObjectName("actionExport")
        self.actionCompare = QtWidgets.QAction(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.actionCompare.setFont(font)
        self.actionCompare.setObjectName("actionCompare")
        self.actionAbout = QtWidgets.QAction(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(14)
        self.actionAbout.setFont(font)
        self.actionAbout.setObjectName("actionAbout")
        self.actionSettings = QtWidgets.QAction(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.actionSettings.setFont(font)
        self.actionSettings.setObjectName("actionSettings")
        self.actionFailMarker = QtWidgets.QAction(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.actionFailMarker.setFont(font)
        self.actionFailMarker.setObjectName("actionFailMarker")
        self.actionReadDutData_DS = QtWidgets.QAction(MainWindow)
        self.actionReadDutData_DS.setObjectName("actionReadDutData_DS")
        self.actionReadDutData_TS = QtWidgets.QAction(MainWindow)
        self.actionReadDutData_TS.setObjectName("actionReadDutData_TS")
        self.toolBar.addAction(self.actionOpen)
        self.toolBar.addAction(self.actionFailMarker)
        self.toolBar.addAction(self.actionExport)
        self.toolBar.addAction(self.actionSettings)

        self.retranslateUi(MainWindow)
        self.Selection_stackedWidget.setCurrentIndex(0)
        self.site_head_selection.setCurrentIndex(0)
        self.tabControl.setCurrentIndex(0)
        self.infoBox.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "STDF Viewer"))
        self.test_selection.setTitle(_translate("MainWindow", "Test Selection"))
        self.Search.setText(_translate("MainWindow", "Search: "))
        self.ClearButton.setText(_translate("MainWindow", "Clear"))
        self.wafer_selection.setTitle(_translate("MainWindow", "Wafer Selection"))
        self.All.setText(_translate("MainWindow", "All Sites"))
        self.checkAll.setText(_translate("MainWindow", "✓ All"))
        self.cancelAll.setText(_translate("MainWindow", "✕ All"))
        self.site_head_selection.setTabText(self.site_head_selection.indexOf(self.site_selection_tab), _translate("MainWindow", "Site Selection"))
        self.site_head_selection.setTabText(self.site_head_selection.indexOf(self.head_selection_tab), _translate("MainWindow", "Test Head Selection"))
        self.infoBox.setItemText(self.infoBox.indexOf(self.fileInfoPage), _translate("MainWindow", "File Info"))
        self.infoBox.setItemText(self.infoBox.indexOf(self.dutInfoPage), _translate("MainWindow", "DUT Summary"))
        self.infoBox.setItemText(self.infoBox.indexOf(self.rawDataPage), _translate("MainWindow", "Test Summary"))
        self.infoBox.setItemText(self.infoBox.indexOf(self.datalogPage), _translate("MainWindow", "GDR && DTR Summary"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.info_tab), _translate("MainWindow", "Detailed Info"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.trend_tab), _translate("MainWindow", "Trend Chart"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.histo_tab), _translate("MainWindow", "Histogram"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.bin_tab), _translate("MainWindow", "Bin Summary"))
        self.tabControl.setTabText(self.tabControl.indexOf(self.wafer_tab), _translate("MainWindow", "Wafer Map"))
        self.groupBox_stats.setTitle(_translate("MainWindow", "Test Statistics"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setToolTip(_translate("MainWindow", "Open STDF file"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionExport.setText(_translate("MainWindow", "Export"))
        self.actionExport.setToolTip(_translate("MainWindow", "Customize a STDF report"))
        self.actionExport.setShortcut(_translate("MainWindow", "Ctrl+E"))
        self.actionCompare.setText(_translate("MainWindow", "Compare"))
        self.actionCompare.setToolTip(_translate("MainWindow", "Compare another STDF file"))
        self.actionAbout.setText(_translate("MainWindow", "About"))
        self.actionSettings.setText(_translate("MainWindow", "Settings"))
        self.actionSettings.setToolTip(_translate("MainWindow", "Configure the plot & table"))
        self.actionFailMarker.setText(_translate("MainWindow", "Fail Marker"))
        self.actionFailMarker.setToolTip(_translate("MainWindow", "Mark failed test items in Test Selection"))
        self.actionReadDutData_DS.setText(_translate("MainWindow", "Read selected DUT data"))
        self.actionReadDutData_TS.setText(_translate("MainWindow", "Read selected DUT data"))
