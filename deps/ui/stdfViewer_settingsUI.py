# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/nochenon/Library/Mobile Documents/iCloud~com~omz-software~Pythonista3/Documents/My Projects/STDF Viewer/ui/stdfViewer_settingsUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Setting(object):
    def setupUi(self, Setting):
        Setting.setObjectName("Setting")
        Setting.resize(378, 381)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Setting.sizePolicy().hasHeightForWidth())
        Setting.setSizePolicy(sizePolicy)
        Setting.setMinimumSize(QtCore.QSize(370, 0))
        Setting.setStyleSheet("QToolBox::tab {\n"
"    background: gray;\n"
"    border-radius: 3px;\n"
"    color: black;\n"
"}\n"
"\n"
"QToolBox::tab:selected { /* italicize selected tabs */\n"
"    color: white;\n"
"    background: #009deb\n"
"}")
        self.verticalLayout = QtWidgets.QVBoxLayout(Setting)
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setObjectName("verticalLayout")
        self.settingBox = QtWidgets.QToolBox(Setting)
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setBold(True)
        font.setWeight(75)
        self.settingBox.setFont(font)
        self.settingBox.setObjectName("settingBox")
        self.trendSetting = QtWidgets.QWidget()
        self.trendSetting.setGeometry(QtCore.QRect(0, 0, 98, 72))
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setBold(False)
        font.setWeight(50)
        self.trendSetting.setFont(font)
        self.trendSetting.setObjectName("trendSetting")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.trendSetting)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.trendscrollArea = QtWidgets.QScrollArea(self.trendSetting)
        self.trendscrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.trendscrollArea.setWidgetResizable(True)
        self.trendscrollArea.setObjectName("trendscrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 324, 92))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_5.setContentsMargins(12, 0, -1, -1)
        self.verticalLayout_5.setSpacing(20)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout.setSpacing(50)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.showHL_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showHL_trend.setChecked(True)
        self.showHL_trend.setObjectName("showHL_trend")
        self.horizontalLayout.addWidget(self.showHL_trend)
        self.showLL_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showLL_trend.setChecked(True)
        self.showLL_trend.setObjectName("showLL_trend")
        self.horizontalLayout.addWidget(self.showLL_trend)
        self.verticalLayout_5.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout_2.setSpacing(50)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.showMedian_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showMedian_trend.setChecked(True)
        self.showMedian_trend.setObjectName("showMedian_trend")
        self.horizontalLayout_2.addWidget(self.showMedian_trend)
        self.showMean_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showMean_trend.setChecked(True)
        self.showMean_trend.setObjectName("showMean_trend")
        self.horizontalLayout_2.addWidget(self.showMean_trend)
        self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem)
        self.trendscrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_2.addWidget(self.trendscrollArea)
        self.settingBox.addItem(self.trendSetting, "")
        self.histoSetting = QtWidgets.QWidget()
        self.histoSetting.setGeometry(QtCore.QRect(0, 0, 98, 72))
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setBold(False)
        font.setWeight(50)
        self.histoSetting.setFont(font)
        self.histoSetting.setObjectName("histoSetting")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.histoSetting)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.histoscrollArea = QtWidgets.QScrollArea(self.histoSetting)
        self.histoscrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.histoscrollArea.setWidgetResizable(True)
        self.histoscrollArea.setObjectName("histoscrollArea")
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 324, 227))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_6.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_6.setSpacing(20)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout_6.setSpacing(50)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.showHL_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showHL_histo.setChecked(True)
        self.showHL_histo.setObjectName("showHL_histo")
        self.horizontalLayout_6.addWidget(self.showHL_histo)
        self.showLL_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showLL_histo.setChecked(True)
        self.showLL_histo.setObjectName("showLL_histo")
        self.horizontalLayout_6.addWidget(self.showLL_histo)
        self.verticalLayout_6.addLayout(self.horizontalLayout_6)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout_5.setSpacing(50)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.showMedian_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showMedian_histo.setChecked(True)
        self.showMedian_histo.setObjectName("showMedian_histo")
        self.horizontalLayout_5.addWidget(self.showMedian_histo)
        self.showMean_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showMean_histo.setChecked(True)
        self.showMean_histo.setObjectName("showMean_histo")
        self.horizontalLayout_5.addWidget(self.showMean_histo)
        self.verticalLayout_6.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout_8.setSpacing(50)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.showGaus_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showGaus_histo.setChecked(True)
        self.showGaus_histo.setObjectName("showGaus_histo")
        self.horizontalLayout_8.addWidget(self.showGaus_histo)
        self.showBoxp_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showBoxp_histo.setChecked(True)
        self.showBoxp_histo.setObjectName("showBoxp_histo")
        self.horizontalLayout_8.addWidget(self.showBoxp_histo)
        self.verticalLayout_6.addLayout(self.horizontalLayout_8)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents_2)
        self.label.setObjectName("label")
        self.horizontalLayout_4.addWidget(self.label)
        self.lineEdit_binCount = QtWidgets.QLineEdit(self.scrollAreaWidgetContents_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_binCount.sizePolicy().hasHeightForWidth())
        self.lineEdit_binCount.setSizePolicy(sizePolicy)
        self.lineEdit_binCount.setText("")
        self.lineEdit_binCount.setAlignment(QtCore.Qt.AlignCenter)
        self.lineEdit_binCount.setObjectName("lineEdit_binCount")
        self.horizontalLayout_4.addWidget(self.lineEdit_binCount)
        self.verticalLayout_6.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_2 = QtWidgets.QLabel(self.scrollAreaWidgetContents_2)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_7.addWidget(self.label_2)
        self.sigmaCombobox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sigmaCombobox.sizePolicy().hasHeightForWidth())
        self.sigmaCombobox.setSizePolicy(sizePolicy)
        self.sigmaCombobox.setObjectName("sigmaCombobox")
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.addItem("")
        self.sigmaCombobox.addItem("")
        self.horizontalLayout_7.addWidget(self.sigmaCombobox)
        self.verticalLayout_6.addLayout(self.horizontalLayout_7)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_6.addItem(spacerItem1)
        self.histoscrollArea.setWidget(self.scrollAreaWidgetContents_2)
        self.verticalLayout_3.addWidget(self.histoscrollArea)
        self.settingBox.addItem(self.histoSetting, "")
        self.tableSetting = QtWidgets.QWidget()
        self.tableSetting.setGeometry(QtCore.QRect(0, 0, 354, 210))
        font = QtGui.QFont()
        font.setFamily("Tahoma")
        font.setBold(False)
        font.setWeight(50)
        self.tableSetting.setFont(font)
        self.tableSetting.setObjectName("tableSetting")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.tableSetting)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.tablescrollArea = QtWidgets.QScrollArea(self.tableSetting)
        self.tablescrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tablescrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tablescrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tablescrollArea.setWidgetResizable(True)
        self.tablescrollArea.setObjectName("tablescrollArea")
        self.scrollAreaWidgetContents_3 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_3.setGeometry(QtCore.QRect(0, 0, 354, 210))
        self.scrollAreaWidgetContents_3.setObjectName("scrollAreaWidgetContents_3")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_3)
        self.verticalLayout_7.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_7.setSpacing(20)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.label_3 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_9.addWidget(self.label_3)
        self.notationCombobox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.notationCombobox.sizePolicy().hasHeightForWidth())
        self.notationCombobox.setSizePolicy(sizePolicy)
        self.notationCombobox.setObjectName("notationCombobox")
        self.notationCombobox.addItem("")
        self.notationCombobox.addItem("")
        self.notationCombobox.addItem("")
        self.horizontalLayout_9.addWidget(self.notationCombobox)
        self.verticalLayout_7.addLayout(self.horizontalLayout_9)
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_4 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_10.addWidget(self.label_4)
        self.precisionLCD = QtWidgets.QLCDNumber(self.scrollAreaWidgetContents_3)
        self.precisionLCD.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.precisionLCD.setDigitCount(2)
        self.precisionLCD.setProperty("intValue", 3)
        self.precisionLCD.setObjectName("precisionLCD")
        self.horizontalLayout_10.addWidget(self.precisionLCD)
        self.precisionSlider = QtWidgets.QSlider(self.scrollAreaWidgetContents_3)
        self.precisionSlider.setMaximum(12)
        self.precisionSlider.setPageStep(3)
        self.precisionSlider.setProperty("value", 3)
        self.precisionSlider.setOrientation(QtCore.Qt.Horizontal)
        self.precisionSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.precisionSlider.setObjectName("precisionSlider")
        self.horizontalLayout_10.addWidget(self.precisionSlider)
        self.verticalLayout_7.addLayout(self.horizontalLayout_10)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_7.addItem(spacerItem2)
        self.tablescrollArea.setWidget(self.scrollAreaWidgetContents_3)
        self.verticalLayout_4.addWidget(self.tablescrollArea)
        self.settingBox.addItem(self.tableSetting, "")
        self.verticalLayout.addWidget(self.settingBox)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(20)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.Confirm = QtWidgets.QPushButton(Setting)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Confirm.sizePolicy().hasHeightForWidth())
        self.Confirm.setSizePolicy(sizePolicy)
        self.Confirm.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setFamily("Menlo")
        font.setBold(True)
        font.setWeight(75)
        self.Confirm.setFont(font)
        self.Confirm.setStyleSheet("QPushButton {\n"
"color: white;\n"
"background-color: rgb(0, 120, 0); \n"
"border: 1px solid rgb(0, 120, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(0, 50, 0); \n"
"border: 1px solid rgb(0, 50, 0);}")
        self.Confirm.setObjectName("Confirm")
        self.horizontalLayout_3.addWidget(self.Confirm)
        self.Cancel = QtWidgets.QPushButton(Setting)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Cancel.sizePolicy().hasHeightForWidth())
        self.Cancel.setSizePolicy(sizePolicy)
        self.Cancel.setMinimumSize(QtCore.QSize(0, 25))
        font = QtGui.QFont()
        font.setFamily("Menlo")
        font.setBold(True)
        font.setWeight(75)
        self.Cancel.setFont(font)
        self.Cancel.setStyleSheet("QPushButton {\n"
"color: white;\n"
"background-color: rgb(83, 0, 0); \n"
"border: 1px solid rgb(83, 0, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(40, 0, 0); \n"
"border: 1px solid rgb(40, 0, 0);}")
        self.Cancel.setObjectName("Cancel")
        self.horizontalLayout_3.addWidget(self.Cancel)
        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(Setting)
        self.settingBox.setCurrentIndex(0)
        self.precisionSlider.valueChanged['int'].connect(self.precisionLCD.display)
        self.precisionSlider.sliderMoved['int'].connect(self.precisionLCD.display)
        QtCore.QMetaObject.connectSlotsByName(Setting)

    def retranslateUi(self, Setting):
        _translate = QtCore.QCoreApplication.translate
        Setting.setWindowTitle(_translate("Setting", "Settings"))
        self.showHL_trend.setText(_translate("Setting", "Show Upper Limit"))
        self.showLL_trend.setText(_translate("Setting", "Show Lower Limit"))
        self.showMedian_trend.setText(_translate("Setting", "Show Median Line"))
        self.showMean_trend.setText(_translate("Setting", "Show Mean Line"))
        self.settingBox.setItemText(self.settingBox.indexOf(self.trendSetting), _translate("Setting", "Trend Plot"))
        self.showHL_histo.setText(_translate("Setting", "Show Upper Limit"))
        self.showLL_histo.setText(_translate("Setting", "Show Lower Limit"))
        self.showMedian_histo.setText(_translate("Setting", "Show Median Line"))
        self.showMean_histo.setText(_translate("Setting", "Show Mean Line"))
        self.showGaus_histo.setText(_translate("Setting", "Show Gaussian"))
        self.showBoxp_histo.setText(_translate("Setting", "Show Boxplot"))
        self.label.setText(_translate("Setting", "Bin Count:"))
        self.label_2.setText(_translate("Setting", "σ Lines:"))
        self.sigmaCombobox.setItemText(0, _translate("Setting", "Hide All"))
        self.sigmaCombobox.setItemText(1, _translate("Setting", "Show ±3σ"))
        self.sigmaCombobox.setItemText(2, _translate("Setting", "Show ±3σ, ±6σ"))
        self.sigmaCombobox.setItemText(3, _translate("Setting", "Show ±3σ, ±6σ, ±9σ"))
        self.settingBox.setItemText(self.settingBox.indexOf(self.histoSetting), _translate("Setting", "Histo Plot"))
        self.label_3.setText(_translate("Setting", "Data Notation:"))
        self.notationCombobox.setItemText(0, _translate("Setting", "Automatic"))
        self.notationCombobox.setItemText(1, _translate("Setting", "Float Number"))
        self.notationCombobox.setItemText(2, _translate("Setting", "Scientific Notation"))
        self.label_4.setText(_translate("Setting", "Data Precison:"))
        self.settingBox.setItemText(self.settingBox.indexOf(self.tableSetting), _translate("Setting", "Statistic Table"))
        self.Confirm.setText(_translate("Setting", "Confirm"))
        self.Confirm.setShortcut(_translate("Setting", "Return"))
        self.Cancel.setText(_translate("Setting", "Cancel"))
        self.Cancel.setShortcut(_translate("Setting", "Esc"))
