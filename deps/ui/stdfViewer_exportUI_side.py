# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stdfViewer_exportUI.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_exportUI(object):
    def setupUi(self, exportUI):
        if not exportUI.objectName():
            exportUI.setObjectName(u"exportUI")
        exportUI.resize(572, 660)
        exportUI.setStyleSheet(u"")
        self.verticalLayout_2 = QVBoxLayout(exportUI)
        self.verticalLayout_2.setSpacing(20)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(12, 0, -1, 0)
        self.horizontalLayout_box = QHBoxLayout()
        self.horizontalLayout_box.setObjectName(u"horizontalLayout_box")
        self.test_selection = QGroupBox(exportUI)
        self.test_selection.setObjectName(u"test_selection")
        self.verticalLayout_5 = QVBoxLayout(self.test_selection)
#ifndef Q_OS_MAC
        self.verticalLayout_5.setSpacing(-1)
#endif
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(10, 10, 10, 10)
        self.TestList = QListView(self.test_selection)
        self.TestList.setObjectName(u"TestList")
        font = QFont()
        font.setFamily(u"Courier New")
        font.setPointSize(10)
        self.TestList.setFont(font)

        self.verticalLayout_5.addWidget(self.TestList)

        self.horizontalLayout_search = QHBoxLayout()
        self.horizontalLayout_search.setObjectName(u"horizontalLayout_search")
        self.Search = QLabel(self.test_selection)
        self.Search.setObjectName(u"Search")

        self.horizontalLayout_search.addWidget(self.Search)

        self.SearchBox = QLineEdit(self.test_selection)
        self.SearchBox.setObjectName(u"SearchBox")

        self.horizontalLayout_search.addWidget(self.SearchBox)

        self.Clear = QToolButton(self.test_selection)
        self.Clear.setObjectName(u"Clear")
        self.Clear.setAutoFillBackground(False)

        self.horizontalLayout_search.addWidget(self.Clear)


        self.verticalLayout_5.addLayout(self.horizontalLayout_search)


        self.horizontalLayout_box.addWidget(self.test_selection)

        self.verticalLayout_buttons = QVBoxLayout()
        self.verticalLayout_buttons.setObjectName(u"verticalLayout_buttons")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_buttons.addItem(self.verticalSpacer_2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetFixedSize)
        self.verticalLayout.setContentsMargins(-1, 20, -1, 20)
        self.Addbutton = QPushButton(exportUI)
        self.Addbutton.setObjectName(u"Addbutton")
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Addbutton.sizePolicy().hasHeightForWidth())
        self.Addbutton.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setFamily(u"Arial")
        font1.setPointSize(24)
        font1.setBold(True)
        font1.setWeight(75)
        self.Addbutton.setFont(font1)
        self.Addbutton.setAutoDefault(False)

        self.verticalLayout.addWidget(self.Addbutton)

        self.AddAllbutton = QPushButton(exportUI)
        self.AddAllbutton.setObjectName(u"AddAllbutton")
        sizePolicy.setHeightForWidth(self.AddAllbutton.sizePolicy().hasHeightForWidth())
        self.AddAllbutton.setSizePolicy(sizePolicy)
        self.AddAllbutton.setFont(font1)
        self.AddAllbutton.setAutoDefault(False)

        self.verticalLayout.addWidget(self.AddAllbutton)

        self.Removebutton = QPushButton(exportUI)
        self.Removebutton.setObjectName(u"Removebutton")
        sizePolicy.setHeightForWidth(self.Removebutton.sizePolicy().hasHeightForWidth())
        self.Removebutton.setSizePolicy(sizePolicy)
        self.Removebutton.setFont(font1)
        self.Removebutton.setAutoDefault(False)

        self.verticalLayout.addWidget(self.Removebutton)

        self.RemoveAllbutton = QPushButton(exportUI)
        self.RemoveAllbutton.setObjectName(u"RemoveAllbutton")
        sizePolicy.setHeightForWidth(self.RemoveAllbutton.sizePolicy().hasHeightForWidth())
        self.RemoveAllbutton.setSizePolicy(sizePolicy)
        self.RemoveAllbutton.setFont(font1)
        self.RemoveAllbutton.setAutoDefault(False)
        self.RemoveAllbutton.setFlat(False)

        self.verticalLayout.addWidget(self.RemoveAllbutton)


        self.verticalLayout_buttons.addLayout(self.verticalLayout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_buttons.addItem(self.verticalSpacer)


        self.horizontalLayout_box.addLayout(self.verticalLayout_buttons)

        self.exportTest = QGroupBox(exportUI)
        self.exportTest.setObjectName(u"exportTest")
        self.verticalLayout_6 = QVBoxLayout(self.exportTest)
#ifndef Q_OS_MAC
        self.verticalLayout_6.setSpacing(-1)
#endif
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(10, 10, 10, 10)
        self.ExportTestList = QListView(self.exportTest)
        self.ExportTestList.setObjectName(u"ExportTestList")
        self.ExportTestList.setFont(font)

        self.verticalLayout_6.addWidget(self.ExportTestList)


        self.horizontalLayout_box.addWidget(self.exportTest)


        self.verticalLayout_2.addLayout(self.horizontalLayout_box)

        self.site_selection = QGroupBox(exportUI)
        self.site_selection.setObjectName(u"site_selection")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.site_selection.sizePolicy().hasHeightForWidth())
        self.site_selection.setSizePolicy(sizePolicy1)
        font2 = QFont()
        font2.setFamily(u"Arial")
        font2.setPointSize(11)
        self.site_selection.setFont(font2)
        self.horizontalLayout_2 = QHBoxLayout(self.site_selection)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 5, -1, 5)
        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(20)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SetFixedSize)
        self.gridLayout.setContentsMargins(0, 0, 10, 0)
        self.All = QCheckBox(self.site_selection)
        self.All.setObjectName(u"All")
        sizePolicy1.setHeightForWidth(self.All.sizePolicy().hasHeightForWidth())
        self.All.setSizePolicy(sizePolicy1)
        self.All.setChecked(False)

        self.gridLayout.addWidget(self.All, 0, 0, 1, 1)

        self.cancelAll = QPushButton(self.site_selection)
        self.cancelAll.setObjectName(u"cancelAll")
        sizePolicy.setHeightForWidth(self.cancelAll.sizePolicy().hasHeightForWidth())
        self.cancelAll.setSizePolicy(sizePolicy)
        self.cancelAll.setMinimumSize(QSize(65, 0))
        self.cancelAll.setMaximumSize(QSize(65, 16777215))
        self.cancelAll.setAutoDefault(False)

        self.gridLayout.addWidget(self.cancelAll, 0, 2, 1, 1)

        self.checkAll = QPushButton(self.site_selection)
        self.checkAll.setObjectName(u"checkAll")
        sizePolicy.setHeightForWidth(self.checkAll.sizePolicy().hasHeightForWidth())
        self.checkAll.setSizePolicy(sizePolicy)
        self.checkAll.setMinimumSize(QSize(65, 0))
        self.checkAll.setMaximumSize(QSize(65, 16777215))
        self.checkAll.setAutoDefault(False)

        self.gridLayout.addWidget(self.checkAll, 0, 1, 1, 1)


        self.horizontalLayout_2.addLayout(self.gridLayout)

        self.horizontalSpacer = QSpacerItem(95, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.verticalLayout_2.addWidget(self.site_selection)

        self.content_selection = QGroupBox(exportUI)
        self.content_selection.setObjectName(u"content_selection")
        sizePolicy1.setHeightForWidth(self.content_selection.sizePolicy().hasHeightForWidth())
        self.content_selection.setSizePolicy(sizePolicy1)
        self.horizontalLayout_4 = QHBoxLayout(self.content_selection)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(-1, 5, -1, 5)
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setSizeConstraint(QLayout.SetFixedSize)
        self.gridLayout_2.setHorizontalSpacing(50)
        self.gridLayout_2.setContentsMargins(0, 0, 10, 0)
        self.Trend_cb = QCheckBox(self.content_selection)
        self.Trend_cb.setObjectName(u"Trend_cb")
        self.Trend_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.Trend_cb, 0, 0, 1, 1)

        self.Stat_cb = QCheckBox(self.content_selection)
        self.Stat_cb.setObjectName(u"Stat_cb")
        self.Stat_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.Stat_cb, 0, 3, 1, 1)

        self.Histo_cb = QCheckBox(self.content_selection)
        self.Histo_cb.setObjectName(u"Histo_cb")
        self.Histo_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.Histo_cb, 0, 1, 1, 1)

        self.Bin_cb = QCheckBox(self.content_selection)
        self.Bin_cb.setObjectName(u"Bin_cb")
        self.Bin_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.Bin_cb, 0, 2, 1, 1)

        self.DUT_cb = QCheckBox(self.content_selection)
        self.DUT_cb.setObjectName(u"DUT_cb")
        self.DUT_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.DUT_cb, 1, 0, 1, 1)

        self.RawData_cb = QCheckBox(self.content_selection)
        self.RawData_cb.setObjectName(u"RawData_cb")
        self.RawData_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.RawData_cb, 1, 1, 1, 1)

        self.FileInfo_cb = QCheckBox(self.content_selection)
        self.FileInfo_cb.setObjectName(u"FileInfo_cb")
        self.FileInfo_cb.setChecked(True)

        self.gridLayout_2.addWidget(self.FileInfo_cb, 1, 2, 1, 1)


        self.horizontalLayout_4.addLayout(self.gridLayout_2)


        self.verticalLayout_2.addWidget(self.content_selection)

        self.exportPath_selection = QGroupBox(exportUI)
        self.exportPath_selection.setObjectName(u"exportPath_selection")
        sizePolicy1.setHeightForWidth(self.exportPath_selection.sizePolicy().hasHeightForWidth())
        self.exportPath_selection.setSizePolicy(sizePolicy1)
        self.exportPath_selection.setMinimumSize(QSize(0, 70))
        self.exportPath_selection.setMaximumSize(QSize(16777215, 70))
        self.horizontalLayout_3 = QHBoxLayout(self.exportPath_selection)
#ifndef Q_OS_MAC
        self.horizontalLayout_3.setSpacing(-1)
#endif
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 5, -1, 5)
        self.plainTextEdit = QPlainTextEdit(self.exportPath_selection)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.plainTextEdit.sizePolicy().hasHeightForWidth())
        self.plainTextEdit.setSizePolicy(sizePolicy2)
        self.plainTextEdit.setMinimumSize(QSize(0, 35))
        self.plainTextEdit.setMaximumSize(QSize(16777215, 35))
        font3 = QFont()
        font3.setFamily(u"Courier New")
        font3.setPointSize(10)
        font3.setItalic(True)
        self.plainTextEdit.setFont(font3)

        self.horizontalLayout_3.addWidget(self.plainTextEdit)

        self.toolButton = QToolButton(self.exportPath_selection)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMinimumSize(QSize(35, 35))
        self.toolButton.setMaximumSize(QSize(35, 35))

        self.horizontalLayout_3.addWidget(self.toolButton)


        self.verticalLayout_2.addWidget(self.exportPath_selection)

        self.horizontalLayout_button = QHBoxLayout()
        self.horizontalLayout_button.setSpacing(10)
        self.horizontalLayout_button.setObjectName(u"horizontalLayout_button")
        self.horizontalLayout_button.setContentsMargins(-1, -1, -1, 15)
        self.Confirm = QPushButton(exportUI)
        self.Confirm.setObjectName(u"Confirm")
        sizePolicy3 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.Confirm.sizePolicy().hasHeightForWidth())
        self.Confirm.setSizePolicy(sizePolicy3)
        self.Confirm.setMinimumSize(QSize(0, 30))
        self.Confirm.setMaximumSize(QSize(16777215, 40))
        font4 = QFont()
        font4.setFamily(u"Menlo")
        font4.setBold(True)
        font4.setWeight(75)
        self.Confirm.setFont(font4)
        self.Confirm.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(0, 120, 0); \n"
"border: 1px solid rgb(0, 120, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(0, 50, 0); \n"
"border: 1px solid rgb(0, 50, 0);}")
        self.Confirm.setCheckable(False)

        self.horizontalLayout_button.addWidget(self.Confirm)

        self.Cancel = QPushButton(exportUI)
        self.Cancel.setObjectName(u"Cancel")
        sizePolicy3.setHeightForWidth(self.Cancel.sizePolicy().hasHeightForWidth())
        self.Cancel.setSizePolicy(sizePolicy3)
        self.Cancel.setMinimumSize(QSize(0, 30))
        self.Cancel.setMaximumSize(QSize(16777215, 40))
        self.Cancel.setFont(font4)
        self.Cancel.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(83, 0, 0); \n"
"border: 1px solid rgb(83, 0, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(40, 0, 0); \n"
"border: 1px solid rgb(40, 0, 0);}")

        self.horizontalLayout_button.addWidget(self.Cancel)


        self.verticalLayout_2.addLayout(self.horizontalLayout_button)


        self.retranslateUi(exportUI)

        self.RemoveAllbutton.setDefault(False)
        self.Confirm.setDefault(True)


        QMetaObject.connectSlotsByName(exportUI)
    # setupUi

    def retranslateUi(self, exportUI):
        exportUI.setWindowTitle(QCoreApplication.translate("exportUI", u"Report Generator", None))
        self.test_selection.setTitle(QCoreApplication.translate("exportUI", u"Test Selection", None))
        self.Search.setText(QCoreApplication.translate("exportUI", u"Search: ", None))
        self.Clear.setText(QCoreApplication.translate("exportUI", u"Clear", None))
#if QT_CONFIG(tooltip)
        self.Addbutton.setToolTip(QCoreApplication.translate("exportUI", u"Add", None))
#endif // QT_CONFIG(tooltip)
        self.Addbutton.setText(QCoreApplication.translate("exportUI", u" > ", None))
#if QT_CONFIG(tooltip)
        self.AddAllbutton.setToolTip(QCoreApplication.translate("exportUI", u"Add all", None))
#endif // QT_CONFIG(tooltip)
        self.AddAllbutton.setText(QCoreApplication.translate("exportUI", u">>", None))
#if QT_CONFIG(tooltip)
        self.Removebutton.setToolTip(QCoreApplication.translate("exportUI", u"Remove", None))
#endif // QT_CONFIG(tooltip)
        self.Removebutton.setText(QCoreApplication.translate("exportUI", u" < ", None))
#if QT_CONFIG(tooltip)
        self.RemoveAllbutton.setToolTip(QCoreApplication.translate("exportUI", u"Remove all", None))
#endif // QT_CONFIG(tooltip)
        self.RemoveAllbutton.setText(QCoreApplication.translate("exportUI", u"<<", None))
        self.exportTest.setTitle(QCoreApplication.translate("exportUI", u"Export Tests", None))
        self.site_selection.setTitle(QCoreApplication.translate("exportUI", u"Site Selection", None))
        self.All.setText(QCoreApplication.translate("exportUI", u"All Sites", None))
        self.cancelAll.setText(QCoreApplication.translate("exportUI", u"\u2715 All", None))
        self.checkAll.setText(QCoreApplication.translate("exportUI", u"\u2713 All", None))
        self.content_selection.setTitle(QCoreApplication.translate("exportUI", u"Report Content Selection", None))
        self.Trend_cb.setText(QCoreApplication.translate("exportUI", u"Trend Chart", None))
        self.Stat_cb.setText(QCoreApplication.translate("exportUI", u"Test Statistics", None))
        self.Histo_cb.setText(QCoreApplication.translate("exportUI", u"Histogram", None))
        self.Bin_cb.setText(QCoreApplication.translate("exportUI", u"Bin Chart", None))
        self.DUT_cb.setText(QCoreApplication.translate("exportUI", u"DUT Summary", None))
        self.RawData_cb.setText(QCoreApplication.translate("exportUI", u"Raw Data", None))
        self.FileInfo_cb.setText(QCoreApplication.translate("exportUI", u"File Info", None))
        self.exportPath_selection.setTitle(QCoreApplication.translate("exportUI", u"Export Path Selection", None))
        self.plainTextEdit.setPlainText("")
        self.toolButton.setText(QCoreApplication.translate("exportUI", u"...", None))
        self.Confirm.setText(QCoreApplication.translate("exportUI", u"Confirm", None))
#if QT_CONFIG(shortcut)
        self.Confirm.setShortcut(QCoreApplication.translate("exportUI", u"Return", None))
#endif // QT_CONFIG(shortcut)
        self.Cancel.setText(QCoreApplication.translate("exportUI", u"Cancel", None))
#if QT_CONFIG(shortcut)
        self.Cancel.setShortcut(QCoreApplication.translate("exportUI", u"Esc, Ctrl+W", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

