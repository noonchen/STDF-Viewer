# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stdfViewer_settingsUI.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_Setting(object):
    def setupUi(self, Setting):
        if not Setting.objectName():
            Setting.setObjectName(u"Setting")
        Setting.resize(378, 381)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Setting.sizePolicy().hasHeightForWidth())
        Setting.setSizePolicy(sizePolicy)
        Setting.setMinimumSize(QSize(370, 0))
        Setting.setStyleSheet(u"QToolBox::tab {\n"
"    background: gray;\n"
"    border-radius: 3px;\n"
"    color: black;\n"
"}\n"
"\n"
"QToolBox::tab:selected { /* italicize selected tabs */\n"
"    color: white;\n"
"	background: #009deb\n"
"}")
        self.verticalLayout = QVBoxLayout(Setting)
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.settingBox = QToolBox(Setting)
        self.settingBox.setObjectName(u"settingBox")
        font = QFont()
        font.setFamily(u"Tahoma")
        font.setBold(True)
        font.setWeight(75)
        self.settingBox.setFont(font)
        self.trendSetting = QWidget()
        self.trendSetting.setObjectName(u"trendSetting")
        self.trendSetting.setGeometry(QRect(0, 0, 98, 72))
        font1 = QFont()
        font1.setFamily(u"Tahoma")
        font1.setBold(False)
        font1.setWeight(50)
        self.trendSetting.setFont(font1)
        self.verticalLayout_2 = QVBoxLayout(self.trendSetting)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.trendscrollArea = QScrollArea(self.trendSetting)
        self.trendscrollArea.setObjectName(u"trendscrollArea")
        self.trendscrollArea.setFrameShape(QFrame.NoFrame)
        self.trendscrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 324, 92))
        self.verticalLayout_5 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_5.setSpacing(20)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(12, 0, -1, -1)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(50)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.showHL_trend = QCheckBox(self.scrollAreaWidgetContents)
        self.showHL_trend.setObjectName(u"showHL_trend")
        self.showHL_trend.setChecked(True)

        self.horizontalLayout.addWidget(self.showHL_trend)

        self.showLL_trend = QCheckBox(self.scrollAreaWidgetContents)
        self.showLL_trend.setObjectName(u"showLL_trend")
        self.showLL_trend.setChecked(True)

        self.horizontalLayout.addWidget(self.showLL_trend)


        self.verticalLayout_5.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(50)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.showMedian_trend = QCheckBox(self.scrollAreaWidgetContents)
        self.showMedian_trend.setObjectName(u"showMedian_trend")
        self.showMedian_trend.setChecked(True)

        self.horizontalLayout_2.addWidget(self.showMedian_trend)

        self.showMean_trend = QCheckBox(self.scrollAreaWidgetContents)
        self.showMean_trend.setObjectName(u"showMean_trend")
        self.showMean_trend.setChecked(True)

        self.horizontalLayout_2.addWidget(self.showMean_trend)


        self.verticalLayout_5.addLayout(self.horizontalLayout_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer)

        self.trendscrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.trendscrollArea)

        self.settingBox.addItem(self.trendSetting, u"Trend Plot")
        self.histoSetting = QWidget()
        self.histoSetting.setObjectName(u"histoSetting")
        self.histoSetting.setGeometry(QRect(0, 0, 98, 72))
        self.histoSetting.setFont(font1)
        self.verticalLayout_3 = QVBoxLayout(self.histoSetting)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.histoscrollArea = QScrollArea(self.histoSetting)
        self.histoscrollArea.setObjectName(u"histoscrollArea")
        self.histoscrollArea.setFrameShape(QFrame.NoFrame)
        self.histoscrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 324, 227))
        self.verticalLayout_6 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.setSpacing(20)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setSpacing(50)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.showHL_histo = QCheckBox(self.scrollAreaWidgetContents_2)
        self.showHL_histo.setObjectName(u"showHL_histo")
        self.showHL_histo.setChecked(True)

        self.horizontalLayout_6.addWidget(self.showHL_histo)

        self.showLL_histo = QCheckBox(self.scrollAreaWidgetContents_2)
        self.showLL_histo.setObjectName(u"showLL_histo")
        self.showLL_histo.setChecked(True)

        self.horizontalLayout_6.addWidget(self.showLL_histo)


        self.verticalLayout_6.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setSpacing(50)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.showMedian_histo = QCheckBox(self.scrollAreaWidgetContents_2)
        self.showMedian_histo.setObjectName(u"showMedian_histo")
        self.showMedian_histo.setChecked(True)

        self.horizontalLayout_5.addWidget(self.showMedian_histo)

        self.showMean_histo = QCheckBox(self.scrollAreaWidgetContents_2)
        self.showMean_histo.setObjectName(u"showMean_histo")
        self.showMean_histo.setChecked(True)

        self.horizontalLayout_5.addWidget(self.showMean_histo)


        self.verticalLayout_6.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setSpacing(50)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.showGaus_histo = QCheckBox(self.scrollAreaWidgetContents_2)
        self.showGaus_histo.setObjectName(u"showGaus_histo")
        self.showGaus_histo.setChecked(True)

        self.horizontalLayout_8.addWidget(self.showGaus_histo)

        self.showBoxp_histo = QCheckBox(self.scrollAreaWidgetContents_2)
        self.showBoxp_histo.setObjectName(u"showBoxp_histo")
        self.showBoxp_histo.setChecked(True)

        self.horizontalLayout_8.addWidget(self.showBoxp_histo)


        self.verticalLayout_6.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label = QLabel(self.scrollAreaWidgetContents_2)
        self.label.setObjectName(u"label")

        self.horizontalLayout_4.addWidget(self.label)

        self.lineEdit_binCount = QLineEdit(self.scrollAreaWidgetContents_2)
        self.lineEdit_binCount.setObjectName(u"lineEdit_binCount")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lineEdit_binCount.sizePolicy().hasHeightForWidth())
        self.lineEdit_binCount.setSizePolicy(sizePolicy1)
        self.lineEdit_binCount.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_4.addWidget(self.lineEdit_binCount)


        self.verticalLayout_6.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_2 = QLabel(self.scrollAreaWidgetContents_2)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_7.addWidget(self.label_2)

        self.sigmaCombobox = QComboBox(self.scrollAreaWidgetContents_2)
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.setObjectName(u"sigmaCombobox")
        sizePolicy1.setHeightForWidth(self.sigmaCombobox.sizePolicy().hasHeightForWidth())
        self.sigmaCombobox.setSizePolicy(sizePolicy1)

        self.horizontalLayout_7.addWidget(self.sigmaCombobox)


        self.verticalLayout_6.addLayout(self.horizontalLayout_7)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_6.addItem(self.verticalSpacer_2)

        self.histoscrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_3.addWidget(self.histoscrollArea)

        self.settingBox.addItem(self.histoSetting, u"Histo Plot")
        self.tableSetting = QWidget()
        self.tableSetting.setObjectName(u"tableSetting")
        self.tableSetting.setGeometry(QRect(0, 0, 354, 210))
        self.tableSetting.setFont(font1)
        self.verticalLayout_4 = QVBoxLayout(self.tableSetting)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.tablescrollArea = QScrollArea(self.tableSetting)
        self.tablescrollArea.setObjectName(u"tablescrollArea")
        self.tablescrollArea.setFrameShape(QFrame.NoFrame)
        self.tablescrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tablescrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tablescrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 354, 210))
        self.verticalLayout_7 = QVBoxLayout(self.scrollAreaWidgetContents_3)
        self.verticalLayout_7.setSpacing(20)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.label_3 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_9.addWidget(self.label_3)

        self.notationCombobox = QComboBox(self.scrollAreaWidgetContents_3)
        self.notationCombobox.addItem("")
        self.notationCombobox.addItem("")
        self.notationCombobox.addItem("")
        self.notationCombobox.setObjectName(u"notationCombobox")
        sizePolicy1.setHeightForWidth(self.notationCombobox.sizePolicy().hasHeightForWidth())
        self.notationCombobox.setSizePolicy(sizePolicy1)

        self.horizontalLayout_9.addWidget(self.notationCombobox)


        self.verticalLayout_7.addLayout(self.horizontalLayout_9)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_4 = QLabel(self.scrollAreaWidgetContents_3)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_10.addWidget(self.label_4)

        self.precisionLCD = QLCDNumber(self.scrollAreaWidgetContents_3)
        self.precisionLCD.setObjectName(u"precisionLCD")
        self.precisionLCD.setFrameShape(QFrame.NoFrame)
        self.precisionLCD.setDigitCount(2)
        self.precisionLCD.setProperty("intValue", 3)

        self.horizontalLayout_10.addWidget(self.precisionLCD)

        self.precisionSlider = QSlider(self.scrollAreaWidgetContents_3)
        self.precisionSlider.setObjectName(u"precisionSlider")
        self.precisionSlider.setMaximum(12)
        self.precisionSlider.setPageStep(3)
        self.precisionSlider.setValue(3)
        self.precisionSlider.setOrientation(Qt.Horizontal)
        self.precisionSlider.setTickPosition(QSlider.NoTicks)

        self.horizontalLayout_10.addWidget(self.precisionSlider)


        self.verticalLayout_7.addLayout(self.horizontalLayout_10)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_3)

        self.tablescrollArea.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout_4.addWidget(self.tablescrollArea)

        self.settingBox.addItem(self.tableSetting, u"Statistic Table")

        self.verticalLayout.addWidget(self.settingBox)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setSpacing(20)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.Confirm = QPushButton(Setting)
        self.Confirm.setObjectName(u"Confirm")
        sizePolicy2 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.Confirm.sizePolicy().hasHeightForWidth())
        self.Confirm.setSizePolicy(sizePolicy2)
        self.Confirm.setMinimumSize(QSize(0, 25))
        font2 = QFont()
        font2.setFamily(u"Menlo")
        font2.setBold(True)
        font2.setWeight(75)
        self.Confirm.setFont(font2)
        self.Confirm.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(0, 120, 0); \n"
"border: 1px solid rgb(0, 120, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(0, 50, 0); \n"
"border: 1px solid rgb(0, 50, 0);}")

        self.horizontalLayout_3.addWidget(self.Confirm)

        self.Cancel = QPushButton(Setting)
        self.Cancel.setObjectName(u"Cancel")
        sizePolicy2.setHeightForWidth(self.Cancel.sizePolicy().hasHeightForWidth())
        self.Cancel.setSizePolicy(sizePolicy2)
        self.Cancel.setMinimumSize(QSize(0, 25))
        self.Cancel.setFont(font2)
        self.Cancel.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(83, 0, 0); \n"
"border: 1px solid rgb(83, 0, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(40, 0, 0); \n"
"border: 1px solid rgb(40, 0, 0);}")

        self.horizontalLayout_3.addWidget(self.Cancel)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.retranslateUi(Setting)
        self.precisionSlider.valueChanged.connect(self.precisionLCD.display)
        self.precisionSlider.sliderMoved.connect(self.precisionLCD.display)

        self.settingBox.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Setting)
    # setupUi

    def retranslateUi(self, Setting):
        Setting.setWindowTitle(QCoreApplication.translate("Setting", u"Settings", None))
        self.showHL_trend.setText(QCoreApplication.translate("Setting", u"Show Upper Limit", None))
        self.showLL_trend.setText(QCoreApplication.translate("Setting", u"Show Lower Limit", None))
        self.showMedian_trend.setText(QCoreApplication.translate("Setting", u"Show Median Line", None))
        self.showMean_trend.setText(QCoreApplication.translate("Setting", u"Show Mean Line", None))
        self.settingBox.setItemText(self.settingBox.indexOf(self.trendSetting), QCoreApplication.translate("Setting", u"Trend Plot", None))
        self.showHL_histo.setText(QCoreApplication.translate("Setting", u"Show Upper Limit", None))
        self.showLL_histo.setText(QCoreApplication.translate("Setting", u"Show Lower Limit", None))
        self.showMedian_histo.setText(QCoreApplication.translate("Setting", u"Show Median Line", None))
        self.showMean_histo.setText(QCoreApplication.translate("Setting", u"Show Mean Line", None))
        self.showGaus_histo.setText(QCoreApplication.translate("Setting", u"Show Gaussian", None))
        self.showBoxp_histo.setText(QCoreApplication.translate("Setting", u"Show Boxplot", None))
        self.label.setText(QCoreApplication.translate("Setting", u"Bin Count:", None))
        self.lineEdit_binCount.setText("")
        self.label_2.setText(QCoreApplication.translate("Setting", u"\u03c3 Lines:", None))
        self.sigmaCombobox.setItemText(0, QCoreApplication.translate("Setting", u"Hide All", None))
        self.sigmaCombobox.setItemText(1, QCoreApplication.translate("Setting", u"Show \u00b13\u03c3", None))
        self.sigmaCombobox.setItemText(2, QCoreApplication.translate("Setting", u"Show \u00b13\u03c3, \u00b16\u03c3", None))
        self.sigmaCombobox.setItemText(3, QCoreApplication.translate("Setting", u"Show \u00b13\u03c3, \u00b16\u03c3, \u00b19\u03c3", None))

        self.settingBox.setItemText(self.settingBox.indexOf(self.histoSetting), QCoreApplication.translate("Setting", u"Histo Plot", None))
        self.label_3.setText(QCoreApplication.translate("Setting", u"Data Notation:", None))
        self.notationCombobox.setItemText(0, QCoreApplication.translate("Setting", u"Automatic", None))
        self.notationCombobox.setItemText(1, QCoreApplication.translate("Setting", u"Float Number", None))
        self.notationCombobox.setItemText(2, QCoreApplication.translate("Setting", u"Scientific Notation", None))

        self.label_4.setText(QCoreApplication.translate("Setting", u"Data Precison:", None))
        self.settingBox.setItemText(self.settingBox.indexOf(self.tableSetting), QCoreApplication.translate("Setting", u"Statistic Table", None))
        self.Confirm.setText(QCoreApplication.translate("Setting", u"Confirm", None))
#if QT_CONFIG(shortcut)
        self.Confirm.setShortcut(QCoreApplication.translate("Setting", u"Return", None))
#endif // QT_CONFIG(shortcut)
        self.Cancel.setText(QCoreApplication.translate("Setting", u"Cancel", None))
#if QT_CONFIG(shortcut)
        self.Cancel.setShortcut(QCoreApplication.translate("Setting", u"Esc", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

