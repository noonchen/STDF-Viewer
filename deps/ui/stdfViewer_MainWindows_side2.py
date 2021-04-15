# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stdfViewer_MainWindows.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1440, 847)
        font = QFont()
        font.setFamily(u"Tahoma")
        font.setPointSize(11)
        MainWindow.setFont(font)
        MainWindow.setStyleSheet(u"QScrollArea { background: transparent; }\n"
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
""
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
        MainWindow.setIconSize(QSize(30, 30))
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setObjectName(u"actionOpen")
        font1 = QFont()
        font1.setFamily(u"Tahoma")
        font1.setPointSize(14)
        font1.setBold(False)
        font1.setWeight(50)
        self.actionOpen.setFont(font1)
        self.actionExport = QAction(MainWindow)
        self.actionExport.setObjectName(u"actionExport")
        self.actionExport.setFont(font1)
        self.actionCompare = QAction(MainWindow)
        self.actionCompare.setObjectName(u"actionCompare")
        self.actionCompare.setFont(font1)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        font2 = QFont()
        font2.setFamily(u"Tahoma")
        font2.setPointSize(14)
        self.actionAbout.setFont(font2)
        self.actionSettings = QAction(MainWindow)
        self.actionSettings.setObjectName(u"actionSettings")
        self.actionSettings.setFont(font1)
        self.actionFailMarker = QAction(MainWindow)
        self.actionFailMarker.setObjectName(u"actionFailMarker")
        self.actionFailMarker.setFont(font1)
        self.actionReadDutData_DS = QAction(MainWindow)
        self.actionReadDutData_DS.setObjectName(u"actionReadDutData_DS")
        self.actionReadDutData_TS = QAction(MainWindow)
        self.actionReadDutData_TS.setObjectName(u"actionReadDutData_TS")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.LR_splitter = QSplitter(self.centralwidget)
        self.LR_splitter.setObjectName(u"LR_splitter")
        self.LR_splitter.setOrientation(Qt.Horizontal)
        self.LR_splitter.setOpaqueResize(False)
        self.LR_splitter.setHandleWidth(10)
        self.LR_splitter.setChildrenCollapsible(True)
        self.Selection_splitter = QSplitter(self.LR_splitter)
        self.Selection_splitter.setObjectName(u"Selection_splitter")
        self.Selection_splitter.setOrientation(Qt.Vertical)
        self.Selection_splitter.setHandleWidth(10)
        self.Selection_splitter.setChildrenCollapsible(False)
        self.Selection_stackedWidget = QStackedWidget(self.Selection_splitter)
        self.Selection_stackedWidget.setObjectName(u"Selection_stackedWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Selection_stackedWidget.sizePolicy().hasHeightForWidth())
        self.Selection_stackedWidget.setSizePolicy(sizePolicy)
        self.FT_page = QWidget()
        self.FT_page.setObjectName(u"FT_page")
        self.verticalLayout_13 = QVBoxLayout(self.FT_page)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.test_selection = QGroupBox(self.FT_page)
        self.test_selection.setObjectName(u"test_selection")
        sizePolicy.setHeightForWidth(self.test_selection.sizePolicy().hasHeightForWidth())
        self.test_selection.setSizePolicy(sizePolicy)
        self.verticalLayout_5 = QVBoxLayout(self.test_selection)
        self.verticalLayout_5.setSpacing(6)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(10, 10, 10, 10)
        self.TestList = QListView(self.test_selection)
        self.TestList.setObjectName(u"TestList")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.TestList.sizePolicy().hasHeightForWidth())
        self.TestList.setSizePolicy(sizePolicy1)
        self.TestList.setMinimumSize(QSize(0, 0))
        font3 = QFont()
        font3.setFamily(u"Courier")
        font3.setPointSize(12)
        font3.setBold(False)
        font3.setItalic(False)
        font3.setWeight(50)
        self.TestList.setFont(font3)

        self.verticalLayout_5.addWidget(self.TestList)

        self.horizontalLayout_search = QHBoxLayout()
        self.horizontalLayout_search.setObjectName(u"horizontalLayout_search")
        self.Search = QLabel(self.test_selection)
        self.Search.setObjectName(u"Search")

        self.horizontalLayout_search.addWidget(self.Search)

        self.SearchBox = QLineEdit(self.test_selection)
        self.SearchBox.setObjectName(u"SearchBox")
        sizePolicy2 = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.SearchBox.sizePolicy().hasHeightForWidth())
        self.SearchBox.setSizePolicy(sizePolicy2)
        self.SearchBox.setMinimumSize(QSize(160, 0))

        self.horizontalLayout_search.addWidget(self.SearchBox)

        self.ClearButton = QPushButton(self.test_selection)
        self.ClearButton.setObjectName(u"ClearButton")

        self.horizontalLayout_search.addWidget(self.ClearButton)


        self.verticalLayout_5.addLayout(self.horizontalLayout_search)


        self.verticalLayout_13.addWidget(self.test_selection)

        self.Selection_stackedWidget.addWidget(self.FT_page)
        self.CP_page = QWidget()
        self.CP_page.setObjectName(u"CP_page")
        self.verticalLayout_15 = QVBoxLayout(self.CP_page)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.wafer_selection = QGroupBox(self.CP_page)
        self.wafer_selection.setObjectName(u"wafer_selection")
        sizePolicy.setHeightForWidth(self.wafer_selection.sizePolicy().hasHeightForWidth())
        self.wafer_selection.setSizePolicy(sizePolicy)
        self.verticalLayout_14 = QVBoxLayout(self.wafer_selection)
        self.verticalLayout_14.setSpacing(6)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(10, 10, 10, 10)
        self.WaferList = QListView(self.wafer_selection)
        self.WaferList.setObjectName(u"WaferList")
        sizePolicy.setHeightForWidth(self.WaferList.sizePolicy().hasHeightForWidth())
        self.WaferList.setSizePolicy(sizePolicy)
        self.WaferList.setMinimumSize(QSize(0, 0))
        self.WaferList.setFont(font3)

        self.verticalLayout_14.addWidget(self.WaferList)


        self.verticalLayout_15.addWidget(self.wafer_selection)

        self.Selection_stackedWidget.addWidget(self.CP_page)
        self.Selection_splitter.addWidget(self.Selection_stackedWidget)
        self.site_head_selection = QTabWidget(self.Selection_splitter)
        self.site_head_selection.setObjectName(u"site_head_selection")
        sizePolicy3 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(10)
        sizePolicy3.setHeightForWidth(self.site_head_selection.sizePolicy().hasHeightForWidth())
        self.site_head_selection.setSizePolicy(sizePolicy3)
        self.site_head_selection.setMaximumSize(QSize(16777215, 81))
        self.site_head_selection.setTabShape(QTabWidget.Triangular)
        self.site_selection_tab = QWidget()
        self.site_selection_tab.setObjectName(u"site_selection_tab")
        self.horizontalLayout_site_sel = QHBoxLayout(self.site_selection_tab)
        self.horizontalLayout_site_sel.setSpacing(0)
        self.horizontalLayout_site_sel.setObjectName(u"horizontalLayout_site_sel")
        self.horizontalLayout_site_sel.setContentsMargins(12, 12, 12, 12)
        self.scrollArea_site_selection = QScrollArea(self.site_selection_tab)
        self.scrollArea_site_selection.setObjectName(u"scrollArea_site_selection")
        sizePolicy4 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.scrollArea_site_selection.sizePolicy().hasHeightForWidth())
        self.scrollArea_site_selection.setSizePolicy(sizePolicy4)
        self.scrollArea_site_selection.setMinimumSize(QSize(0, 32))
        self.scrollArea_site_selection.setFrameShape(QFrame.NoFrame)
        self.scrollArea_site_selection.setLineWidth(0)
        self.scrollArea_site_selection.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea_site_selection.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_site_selection.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.scrollArea_site_selection.setWidgetResizable(True)
        self.scrollArea_site_selection.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.site_selection_contents = QWidget()
        self.site_selection_contents.setObjectName(u"site_selection_contents")
        self.site_selection_contents.setGeometry(QRect(0, 0, 297, 34))
        sizePolicy1.setHeightForWidth(self.site_selection_contents.sizePolicy().hasHeightForWidth())
        self.site_selection_contents.setSizePolicy(sizePolicy1)
        self.verticalLayout_7 = QVBoxLayout(self.site_selection_contents)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_site_hspacer = QHBoxLayout()
        self.horizontalLayout_site_hspacer.setObjectName(u"horizontalLayout_site_hspacer")
        self.gridLayout_site_select = QGridLayout()
        self.gridLayout_site_select.setSpacing(10)
        self.gridLayout_site_select.setObjectName(u"gridLayout_site_select")
        self.gridLayout_site_select.setSizeConstraint(QLayout.SetFixedSize)
        self.gridLayout_site_select.setContentsMargins(0, 0, 0, 0)
        self.All = QCheckBox(self.site_selection_contents)
        self.All.setObjectName(u"All")
        self.All.setChecked(True)

        self.gridLayout_site_select.addWidget(self.All, 0, 0, 1, 1)

        self.checkAll = QPushButton(self.site_selection_contents)
        self.checkAll.setObjectName(u"checkAll")
        sizePolicy5 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.checkAll.sizePolicy().hasHeightForWidth())
        self.checkAll.setSizePolicy(sizePolicy5)
        self.checkAll.setMinimumSize(QSize(65, 0))
        self.checkAll.setMaximumSize(QSize(65, 16777215))

        self.gridLayout_site_select.addWidget(self.checkAll, 0, 1, 1, 1)

        self.cancelAll = QPushButton(self.site_selection_contents)
        self.cancelAll.setObjectName(u"cancelAll")
        sizePolicy5.setHeightForWidth(self.cancelAll.sizePolicy().hasHeightForWidth())
        self.cancelAll.setSizePolicy(sizePolicy5)
        self.cancelAll.setMinimumSize(QSize(65, 0))
        self.cancelAll.setMaximumSize(QSize(65, 16777215))

        self.gridLayout_site_select.addWidget(self.cancelAll, 0, 2, 1, 1)


        self.horizontalLayout_site_hspacer.addLayout(self.gridLayout_site_select)

        self.horizontalSpacer_site = QSpacerItem(30, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_site_hspacer.addItem(self.horizontalSpacer_site)


        self.verticalLayout_7.addLayout(self.horizontalLayout_site_hspacer)

        self.verticalSpacer_site = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_site)

        self.scrollArea_site_selection.setWidget(self.site_selection_contents)

        self.horizontalLayout_site_sel.addWidget(self.scrollArea_site_selection)

        self.site_head_selection.addTab(self.site_selection_tab, "")
        self.head_selection_tab = QWidget()
        self.head_selection_tab.setObjectName(u"head_selection_tab")
        self.horizontalLayout_head_sel = QHBoxLayout(self.head_selection_tab)
        self.horizontalLayout_head_sel.setSpacing(0)
        self.horizontalLayout_head_sel.setObjectName(u"horizontalLayout_head_sel")
        self.horizontalLayout_head_sel.setContentsMargins(12, 12, 12, 12)
        self.verticalLayout_header = QVBoxLayout()
        self.verticalLayout_header.setSpacing(0)
        self.verticalLayout_header.setObjectName(u"verticalLayout_header")
        self.verticalLayout_header.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_head_hspacer = QHBoxLayout()
        self.horizontalLayout_head_hspacer.setObjectName(u"horizontalLayout_head_hspacer")
        self.gridLayout_head_select = QGridLayout()
        self.gridLayout_head_select.setSpacing(10)
        self.gridLayout_head_select.setObjectName(u"gridLayout_head_select")
        self.gridLayout_head_select.setSizeConstraint(QLayout.SetFixedSize)
        self.gridLayout_head_select.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_head_hspacer.addLayout(self.gridLayout_head_select)

        self.horizontalSpacer_head = QSpacerItem(30, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_head_hspacer.addItem(self.horizontalSpacer_head)


        self.verticalLayout_header.addLayout(self.horizontalLayout_head_hspacer)

        self.verticalSpacer_head = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_header.addItem(self.verticalSpacer_head)


        self.horizontalLayout_head_sel.addLayout(self.verticalLayout_header)

        self.site_head_selection.addTab(self.head_selection_tab, "")
        self.Selection_splitter.addWidget(self.site_head_selection)
        self.LR_splitter.addWidget(self.Selection_splitter)
        self.Tab_Table_splitter = QSplitter(self.LR_splitter)
        self.Tab_Table_splitter.setObjectName(u"Tab_Table_splitter")
        sizePolicy6 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy6.setHorizontalStretch(3)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.Tab_Table_splitter.sizePolicy().hasHeightForWidth())
        self.Tab_Table_splitter.setSizePolicy(sizePolicy6)
        self.Tab_Table_splitter.setOrientation(Qt.Vertical)
        self.Tab_Table_splitter.setOpaqueResize(False)
        self.Tab_Table_splitter.setHandleWidth(5)
        self.Tab_Table_splitter.setChildrenCollapsible(True)
        self.tabControl = QTabWidget(self.Tab_Table_splitter)
        self.tabControl.setObjectName(u"tabControl")
        sizePolicy7 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(4)
        sizePolicy7.setHeightForWidth(self.tabControl.sizePolicy().hasHeightForWidth())
        self.tabControl.setSizePolicy(sizePolicy7)
        self.tabControl.setTabShape(QTabWidget.Triangular)
        self.info_tab = QWidget()
        self.info_tab.setObjectName(u"info_tab")
        self.verticalLayout = QVBoxLayout(self.info_tab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_info = QHBoxLayout()
        self.horizontalLayout_info.setObjectName(u"horizontalLayout_info")
        self.horizontalLayout_info.setContentsMargins(30, 20, 30, 20)
        self.infoBox = QToolBox(self.info_tab)
        self.infoBox.setObjectName(u"infoBox")
        self.infoBox.setStyleSheet(u"QToolBox::tab {\n"
"    background: #BEBDBF;\n"
"    border-radius: 3px;\n"
"    color: black;\n"
"}\n"
"\n"
"QToolBox::tab:selected { /* italicize selected tabs */\n"
"    color: white;\n"
"	background: #009deb\n"
"}")
        self.fileInfoPage = QWidget()
        self.fileInfoPage.setObjectName(u"fileInfoPage")
        self.fileInfoPage.setGeometry(QRect(0, 0, 1013, 410))
        self.verticalLayout_11 = QVBoxLayout(self.fileInfoPage)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(20, 10, 20, -1)
        self.fileInfoTable = QTableView(self.fileInfoPage)
        self.fileInfoTable.setObjectName(u"fileInfoTable")
        self.fileInfoTable.setStyleSheet(u"QTableView {\n"
"background: transparent;\n"
"font: 13pt \"Courier\";}\n"
"\n"
"")
        self.fileInfoTable.setFrameShape(QFrame.NoFrame)
        self.fileInfoTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.fileInfoTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fileInfoTable.setProperty("showDropIndicator", False)
        self.fileInfoTable.setDragDropOverwriteMode(False)
        self.fileInfoTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fileInfoTable.setTextElideMode(Qt.ElideNone)
        self.fileInfoTable.setShowGrid(False)
        self.fileInfoTable.setGridStyle(Qt.NoPen)
        self.fileInfoTable.setCornerButtonEnabled(False)
        self.fileInfoTable.horizontalHeader().setVisible(False)
        self.fileInfoTable.verticalHeader().setVisible(False)

        self.verticalLayout_11.addWidget(self.fileInfoTable)

        self.infoBox.addItem(self.fileInfoPage, u"File Info")
        self.dutInfoPage = QWidget()
        self.dutInfoPage.setObjectName(u"dutInfoPage")
        self.dutInfoPage.setGeometry(QRect(0, 0, 1013, 410))
        self.verticalLayout_12 = QVBoxLayout(self.dutInfoPage)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.dutInfoTable = QTableView(self.dutInfoPage)
        self.dutInfoTable.setObjectName(u"dutInfoTable")
        self.dutInfoTable.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.dutInfoTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dutInfoTable.verticalHeader().setVisible(False)

        self.verticalLayout_12.addWidget(self.dutInfoTable)

        self.infoBox.addItem(self.dutInfoPage, u"DUT Summary")
        self.rawDataPage = QWidget()
        self.rawDataPage.setObjectName(u"rawDataPage")
        self.rawDataPage.setGeometry(QRect(0, 0, 1013, 410))
        self.verticalLayout_9 = QVBoxLayout(self.rawDataPage)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.rawDataTable = QTableView(self.rawDataPage)
        self.rawDataTable.setObjectName(u"rawDataTable")
        self.rawDataTable.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.rawDataTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rawDataTable.verticalHeader().setVisible(False)

        self.verticalLayout_9.addWidget(self.rawDataTable)

        self.infoBox.addItem(self.rawDataPage, u"Test Summary")

        self.horizontalLayout_info.addWidget(self.infoBox)


        self.verticalLayout.addLayout(self.horizontalLayout_info)

        self.tabControl.addTab(self.info_tab, "")
        self.trend_tab = QWidget()
        self.trend_tab.setObjectName(u"trend_tab")
        self.verticalLayout_4 = QVBoxLayout(self.trend_tab)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_trend = QHBoxLayout()
        self.horizontalLayout_trend.setObjectName(u"horizontalLayout_trend")
        self.scrollArea_trend = QScrollArea(self.trend_tab)
        self.scrollArea_trend.setObjectName(u"scrollArea_trend")
        self.scrollArea_trend.setAutoFillBackground(False)
        self.scrollArea_trend.setStyleSheet(u"background-color: white")
        self.scrollArea_trend.setFrameShape(QFrame.NoFrame)
        self.scrollArea_trend.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 1071, 550))
        self.verticalLayout_8 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_trend = QVBoxLayout()
        self.verticalLayout_trend.setObjectName(u"verticalLayout_trend")

        self.verticalLayout_8.addLayout(self.verticalLayout_trend)

        self.scrollArea_trend.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout_trend.addWidget(self.scrollArea_trend)


        self.verticalLayout_4.addLayout(self.horizontalLayout_trend)

        self.tabControl.addTab(self.trend_tab, "")
        self.histo_tab = QWidget()
        self.histo_tab.setObjectName(u"histo_tab")
        self.verticalLayout_3 = QVBoxLayout(self.histo_tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_histo = QHBoxLayout()
        self.horizontalLayout_histo.setObjectName(u"horizontalLayout_histo")
        self.scrollArea_histo = QScrollArea(self.histo_tab)
        self.scrollArea_histo.setObjectName(u"scrollArea_histo")
        self.scrollArea_histo.setStyleSheet(u"background-color: white")
        self.scrollArea_histo.setFrameShape(QFrame.NoFrame)
        self.scrollArea_histo.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 1071, 550))
        self.scrollAreaWidgetContents_2.setStyleSheet(u"")
        self.verticalLayout_6 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_histo = QVBoxLayout()
        self.verticalLayout_histo.setObjectName(u"verticalLayout_histo")

        self.verticalLayout_6.addLayout(self.verticalLayout_histo)

        self.scrollArea_histo.setWidget(self.scrollAreaWidgetContents_2)

        self.horizontalLayout_histo.addWidget(self.scrollArea_histo)


        self.verticalLayout_3.addLayout(self.horizontalLayout_histo)

        self.tabControl.addTab(self.histo_tab, "")
        self.bin_tab = QWidget()
        self.bin_tab.setObjectName(u"bin_tab")
        self.verticalLayout_10 = QVBoxLayout(self.bin_tab)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_bin = QHBoxLayout()
        self.horizontalLayout_bin.setObjectName(u"horizontalLayout_bin")
        self.scrollArea_bin = QScrollArea(self.bin_tab)
        self.scrollArea_bin.setObjectName(u"scrollArea_bin")
        self.scrollArea_bin.setStyleSheet(u"background-color: white")
        self.scrollArea_bin.setFrameShape(QFrame.NoFrame)
        self.scrollArea_bin.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 1071, 550))
        self.horizontalLayout_3 = QHBoxLayout(self.scrollAreaWidgetContents_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_bin = QVBoxLayout()
        self.verticalLayout_bin.setObjectName(u"verticalLayout_bin")

        self.horizontalLayout_3.addLayout(self.verticalLayout_bin)

        self.scrollArea_bin.setWidget(self.scrollAreaWidgetContents_4)

        self.horizontalLayout_bin.addWidget(self.scrollArea_bin)


        self.verticalLayout_10.addLayout(self.horizontalLayout_bin)

        self.tabControl.addTab(self.bin_tab, "")
        self.wafer_tab = QWidget()
        self.wafer_tab.setObjectName(u"wafer_tab")
        self.verticalLayout_17 = QVBoxLayout(self.wafer_tab)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_wafer = QHBoxLayout()
        self.horizontalLayout_wafer.setObjectName(u"horizontalLayout_wafer")
        self.scrollArea_wafer = QScrollArea(self.wafer_tab)
        self.scrollArea_wafer.setObjectName(u"scrollArea_wafer")
        self.scrollArea_wafer.setStyleSheet(u"background-color: white")
        self.scrollArea_wafer.setFrameShape(QFrame.NoFrame)
        self.scrollArea_wafer.setWidgetResizable(True)
        self.scrollAreaWidgetContents_5 = QWidget()
        self.scrollAreaWidgetContents_5.setObjectName(u"scrollAreaWidgetContents_5")
        self.scrollAreaWidgetContents_5.setGeometry(QRect(0, 0, 1071, 550))
        self.verticalLayout_16 = QVBoxLayout(self.scrollAreaWidgetContents_5)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_wafer = QVBoxLayout()
        self.verticalLayout_wafer.setObjectName(u"verticalLayout_wafer")

        self.verticalLayout_16.addLayout(self.verticalLayout_wafer)

        self.scrollArea_wafer.setWidget(self.scrollAreaWidgetContents_5)

        self.horizontalLayout_wafer.addWidget(self.scrollArea_wafer)


        self.verticalLayout_17.addLayout(self.horizontalLayout_wafer)

        self.tabControl.addTab(self.wafer_tab, "")
        self.Tab_Table_splitter.addWidget(self.tabControl)
        self.groupBox_stats = QGroupBox(self.Tab_Table_splitter)
        self.groupBox_stats.setObjectName(u"groupBox_stats")
        sizePolicy8 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(2)
        sizePolicy8.setHeightForWidth(self.groupBox_stats.sizePolicy().hasHeightForWidth())
        self.groupBox_stats.setSizePolicy(sizePolicy8)
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_stats)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.dataTable = QTableView(self.groupBox_stats)
        self.dataTable.setObjectName(u"dataTable")
        self.dataTable.setStyleSheet(u"font: 9pt \"Tahoma\";")
        self.dataTable.verticalHeader().setVisible(True)

        self.verticalLayout_2.addWidget(self.dataTable)

        self.Tab_Table_splitter.addWidget(self.groupBox_stats)
        self.LR_splitter.addWidget(self.Tab_Table_splitter)

        self.horizontalLayout.addWidget(self.LR_splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setFont(font)
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QToolBar(MainWindow)
        self.toolBar.setObjectName(u"toolBar")
        sizePolicy.setHeightForWidth(self.toolBar.sizePolicy().hasHeightForWidth())
        self.toolBar.setSizePolicy(sizePolicy)
        self.toolBar.setMinimumSize(QSize(0, 0))
        font4 = QFont()
        font4.setFamily(u"Tahoma")
        font4.setPointSize(16)
        self.toolBar.setFont(font4)
        self.toolBar.setAutoFillBackground(False)
        self.toolBar.setStyleSheet(u"##background-color:rgb(71, 187, 241)")
        self.toolBar.setMovable(False)
        self.toolBar.setIconSize(QSize(20, 20))
        self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolBar.setFloatable(False)
        MainWindow.addToolBar(Qt.TopToolBarArea, self.toolBar)

        self.toolBar.addAction(self.actionOpen)
        self.toolBar.addAction(self.actionFailMarker)
        self.toolBar.addAction(self.actionExport)
        self.toolBar.addAction(self.actionSettings)

        self.retranslateUi(MainWindow)

        self.Selection_stackedWidget.setCurrentIndex(0)
        self.site_head_selection.setCurrentIndex(0)
        self.tabControl.setCurrentIndex(0)
        self.infoBox.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"STDF Viewer", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", u"Open", None))
#if QT_CONFIG(tooltip)
        self.actionOpen.setToolTip(QCoreApplication.translate("MainWindow", u"Open STDF file", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionOpen.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionExport.setText(QCoreApplication.translate("MainWindow", u"Export", None))
#if QT_CONFIG(tooltip)
        self.actionExport.setToolTip(QCoreApplication.translate("MainWindow", u"Customize a STDF report", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionExport.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+E", None))
#endif // QT_CONFIG(shortcut)
        self.actionCompare.setText(QCoreApplication.translate("MainWindow", u"Compare", None))
#if QT_CONFIG(tooltip)
        self.actionCompare.setToolTip(QCoreApplication.translate("MainWindow", u"Compare another STDF file", None))
#endif // QT_CONFIG(tooltip)
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionSettings.setText(QCoreApplication.translate("MainWindow", u"Settings", None))
#if QT_CONFIG(tooltip)
        self.actionSettings.setToolTip(QCoreApplication.translate("MainWindow", u"Configure the plot & table", None))
#endif // QT_CONFIG(tooltip)
        self.actionFailMarker.setText(QCoreApplication.translate("MainWindow", u"Fail Marker", None))
#if QT_CONFIG(tooltip)
        self.actionFailMarker.setToolTip(QCoreApplication.translate("MainWindow", u"Mark failed test items in Test Selection", None))
#endif // QT_CONFIG(tooltip)
        self.actionReadDutData_DS.setText(QCoreApplication.translate("MainWindow", u"Read selected DUT data", None))
        self.actionReadDutData_TS.setText(QCoreApplication.translate("MainWindow", u"Read selected DUT data", None))
        self.test_selection.setTitle(QCoreApplication.translate("MainWindow", u"Test Selection", None))
        self.Search.setText(QCoreApplication.translate("MainWindow", u"Search: ", None))
        self.ClearButton.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
        self.wafer_selection.setTitle(QCoreApplication.translate("MainWindow", u"Wafer Selection", None))
        self.All.setText(QCoreApplication.translate("MainWindow", u"All Sites", None))
        self.checkAll.setText(QCoreApplication.translate("MainWindow", u"\u2713 All", None))
        self.cancelAll.setText(QCoreApplication.translate("MainWindow", u"\u2715 All", None))
        self.site_head_selection.setTabText(self.site_head_selection.indexOf(self.site_selection_tab), QCoreApplication.translate("MainWindow", u"Site Selection", None))
        self.site_head_selection.setTabText(self.site_head_selection.indexOf(self.head_selection_tab), QCoreApplication.translate("MainWindow", u"Test Head Selection", None))
        self.infoBox.setItemText(self.infoBox.indexOf(self.fileInfoPage), QCoreApplication.translate("MainWindow", u"File Info", None))
        self.infoBox.setItemText(self.infoBox.indexOf(self.dutInfoPage), QCoreApplication.translate("MainWindow", u"DUT Summary", None))
        self.infoBox.setItemText(self.infoBox.indexOf(self.rawDataPage), QCoreApplication.translate("MainWindow", u"Test Summary", None))
        self.tabControl.setTabText(self.tabControl.indexOf(self.info_tab), QCoreApplication.translate("MainWindow", u"Detailed Info", None))
        self.tabControl.setTabText(self.tabControl.indexOf(self.trend_tab), QCoreApplication.translate("MainWindow", u"Trend Chart", None))
        self.tabControl.setTabText(self.tabControl.indexOf(self.histo_tab), QCoreApplication.translate("MainWindow", u"Histogram", None))
        self.tabControl.setTabText(self.tabControl.indexOf(self.bin_tab), QCoreApplication.translate("MainWindow", u"Bin Summary", None))
        self.tabControl.setTabText(self.tabControl.indexOf(self.wafer_tab), QCoreApplication.translate("MainWindow", u"Wafer Map", None))
        self.groupBox_stats.setTitle(QCoreApplication.translate("MainWindow", u"Test Statistics", None))
        self.toolBar.setWindowTitle(QCoreApplication.translate("MainWindow", u"toolBar", None))
    # retranslateUi

