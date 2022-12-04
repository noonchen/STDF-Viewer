# -*- coding: utf-8 -*-

#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Setting(object):
    def setupUi(self, Setting):
        Setting.setObjectName("Setting")
        Setting.resize(655, 348)
        Setting.setMinimumSize(QtCore.QSize(655, 348))
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Setting)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtWidgets.QFrame(Setting)
        self.frame.setStyleSheet("QPushButton {\n"
"color: black;\n"
"background-color: #BEBDBF; \n"
"border-radius: 5px;\n"
"padding-left: 10px;\n"
"padding-right: 10px;}\n"
"\n"
"QPushButton:pressed,\n"
"QPushButton:checked {\n"
"color: white;\n"
"background-color: #009DEB; \n"
"border: 1px solid rgb(0, 50, 0);}")
        self.frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame.setObjectName("frame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.frame)
        self.verticalLayout.setContentsMargins(0, 9, 0, -1)
        self.verticalLayout.setSpacing(9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.generalBtn = QtWidgets.QPushButton(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.generalBtn.sizePolicy().hasHeightForWidth())
        self.generalBtn.setSizePolicy(sizePolicy)
        self.generalBtn.setMinimumSize(QtCore.QSize(100, 0))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.generalBtn.setFont(font)
        self.generalBtn.setIconSize(QtCore.QSize(20, 20))
        self.generalBtn.setCheckable(True)
        self.generalBtn.setAutoExclusive(True)
        self.generalBtn.setObjectName("generalBtn")
        self.verticalLayout.addWidget(self.generalBtn)
        self.trendBtn = QtWidgets.QPushButton(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.trendBtn.sizePolicy().hasHeightForWidth())
        self.trendBtn.setSizePolicy(sizePolicy)
        self.trendBtn.setMinimumSize(QtCore.QSize(100, 0))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.trendBtn.setFont(font)
        self.trendBtn.setIconSize(QtCore.QSize(20, 20))
        self.trendBtn.setCheckable(True)
        self.trendBtn.setAutoExclusive(True)
        self.trendBtn.setObjectName("trendBtn")
        self.verticalLayout.addWidget(self.trendBtn)
        self.histoBtn = QtWidgets.QPushButton(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.histoBtn.sizePolicy().hasHeightForWidth())
        self.histoBtn.setSizePolicy(sizePolicy)
        self.histoBtn.setMinimumSize(QtCore.QSize(100, 0))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.histoBtn.setFont(font)
        self.histoBtn.setIconSize(QtCore.QSize(20, 20))
        self.histoBtn.setCheckable(True)
        self.histoBtn.setAutoExclusive(True)
        self.histoBtn.setObjectName("histoBtn")
        self.verticalLayout.addWidget(self.histoBtn)
        self.ppqqBtn = QtWidgets.QPushButton(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ppqqBtn.sizePolicy().hasHeightForWidth())
        self.ppqqBtn.setSizePolicy(sizePolicy)
        self.ppqqBtn.setMinimumSize(QtCore.QSize(100, 0))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.ppqqBtn.setFont(font)
        self.ppqqBtn.setIconSize(QtCore.QSize(20, 20))
        self.ppqqBtn.setCheckable(True)
        self.ppqqBtn.setAutoExclusive(True)
        self.ppqqBtn.setObjectName("ppqqBtn")
        self.verticalLayout.addWidget(self.ppqqBtn)
        self.colorBtn = QtWidgets.QPushButton(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.colorBtn.sizePolicy().hasHeightForWidth())
        self.colorBtn.setSizePolicy(sizePolicy)
        self.colorBtn.setMinimumSize(QtCore.QSize(100, 0))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.colorBtn.setFont(font)
        self.colorBtn.setIconSize(QtCore.QSize(20, 20))
        self.colorBtn.setCheckable(True)
        self.colorBtn.setAutoExclusive(True)
        self.colorBtn.setObjectName("colorBtn")
        self.verticalLayout.addWidget(self.colorBtn)
        self.horizontalLayout.addWidget(self.frame)
        self.stackedWidget = QtWidgets.QStackedWidget(Setting)
        self.stackedWidget.setObjectName("stackedWidget")
        self.General = QtWidgets.QWidget()
        self.General.setObjectName("General")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.General)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.tablescrollArea = QtWidgets.QScrollArea(self.General)
        self.tablescrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tablescrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tablescrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tablescrollArea.setWidgetResizable(True)
        self.tablescrollArea.setObjectName("tablescrollArea")
        self.scrollAreaWidgetContents_3 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_3.setGeometry(QtCore.QRect(0, 0, 506, 277))
        self.scrollAreaWidgetContents_3.setObjectName("scrollAreaWidgetContents_3")
        self.gridLayout = QtWidgets.QGridLayout(self.scrollAreaWidgetContents_3)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setHorizontalSpacing(15)
        self.gridLayout.setVerticalSpacing(20)
        self.gridLayout.setObjectName("gridLayout")
        self.symbol_groupBox = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_3)
        self.symbol_groupBox.setObjectName("symbol_groupBox")
        self.gridLayout_file_symbol = QtWidgets.QGridLayout(self.symbol_groupBox)
        self.gridLayout_file_symbol.setObjectName("gridLayout_file_symbol")
        self.gridLayout.addWidget(self.symbol_groupBox, 5, 0, 1, 4)
        self.label_6 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 3, 0, 1, 1)
        self.langCombobox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.langCombobox.sizePolicy().hasHeightForWidth())
        self.langCombobox.setSizePolicy(sizePolicy)
        self.langCombobox.setCurrentText("English")
        self.langCombobox.setObjectName("langCombobox")
        self.langCombobox.addItem("")
        self.langCombobox.addItem("")
        self.gridLayout.addWidget(self.langCombobox, 0, 1, 1, 1)
        self.sortTestListComboBox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sortTestListComboBox.sizePolicy().hasHeightForWidth())
        self.sortTestListComboBox.setSizePolicy(sizePolicy)
        self.sortTestListComboBox.setObjectName("sortTestListComboBox")
        self.sortTestListComboBox.addItem("")
        self.sortTestListComboBox.addItem("")
        self.sortTestListComboBox.addItem("")
        self.gridLayout.addWidget(self.sortTestListComboBox, 4, 1, 1, 1)
        self.label_lang = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_lang.setObjectName("label_lang")
        self.gridLayout.addWidget(self.label_lang, 0, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 6, 0, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
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
        self.gridLayout.addWidget(self.notationCombobox, 1, 1, 1, 1)
        self.checkCpkcomboBox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkCpkcomboBox.sizePolicy().hasHeightForWidth())
        self.checkCpkcomboBox.setSizePolicy(sizePolicy)
        self.checkCpkcomboBox.setObjectName("checkCpkcomboBox")
        self.checkCpkcomboBox.addItem("")
        self.checkCpkcomboBox.addItem("")
        self.gridLayout.addWidget(self.checkCpkcomboBox, 3, 1, 1, 1)
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_5 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_5.setMinimumSize(QtCore.QSize(22, 0))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_10.addWidget(self.label_5)
        self.precisionSlider = QtWidgets.QSlider(self.scrollAreaWidgetContents_3)
        self.precisionSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    border: 0px;\n"
"    height: 6px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */\n"
"    background: rgb(173, 173, 173);\n"
"    margin: 2px 0;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: rgb(153, 153, 153);\n"
"    border: 1px solid #5c5c5c;\n"
"    width: 18px;\n"
"    margin: -2px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */\n"
"    border-radius: 3px;\n"
"}")
        self.precisionSlider.setMaximum(12)
        self.precisionSlider.setPageStep(3)
        self.precisionSlider.setProperty("value", 3)
        self.precisionSlider.setOrientation(QtCore.Qt.Horizontal)
        self.precisionSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.precisionSlider.setObjectName("precisionSlider")
        self.horizontalLayout_10.addWidget(self.precisionSlider)
        self.gridLayout.addLayout(self.horizontalLayout_10, 1, 3, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 4, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 1, 2, 1, 1)
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 2, 1, 1)
        self.label_9 = QtWidgets.QLabel(self.scrollAreaWidgetContents_3)
        self.label_9.setObjectName("label_9")
        self.gridLayout.addWidget(self.label_9, 3, 2, 1, 1)
        self.lineEdit_cpk = QtWidgets.QLineEdit(self.scrollAreaWidgetContents_3)
        self.lineEdit_cpk.setObjectName("lineEdit_cpk")
        self.gridLayout.addWidget(self.lineEdit_cpk, 3, 3, 1, 1)
        self.fontComboBox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontComboBox.sizePolicy().hasHeightForWidth())
        self.fontComboBox.setSizePolicy(sizePolicy)
        self.fontComboBox.setObjectName("fontComboBox")
        self.gridLayout.addWidget(self.fontComboBox, 0, 3, 1, 1)
        self.tablescrollArea.setWidget(self.scrollAreaWidgetContents_3)
        self.verticalLayout_3.addWidget(self.tablescrollArea)
        self.stackedWidget.addWidget(self.General)
        self.Trend = QtWidgets.QWidget()
        self.Trend.setObjectName("Trend")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.Trend)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.trendscrollArea = QtWidgets.QScrollArea(self.Trend)
        self.trendscrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.trendscrollArea.setWidgetResizable(True)
        self.trendscrollArea.setObjectName("trendscrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 282, 123))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setHorizontalSpacing(15)
        self.gridLayout_2.setVerticalSpacing(20)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.showMedian_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showMedian_trend.setChecked(True)
        self.showMedian_trend.setObjectName("showMedian_trend")
        self.gridLayout_2.addWidget(self.showMedian_trend, 4, 0, 1, 1)
        self.showHL_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showHL_trend.setChecked(True)
        self.showHL_trend.setObjectName("showHL_trend")
        self.gridLayout_2.addWidget(self.showHL_trend, 0, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem1, 6, 0, 1, 1)
        self.showHSpec_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showHSpec_trend.setChecked(True)
        self.showHSpec_trend.setObjectName("showHSpec_trend")
        self.gridLayout_2.addWidget(self.showHSpec_trend, 2, 0, 1, 1)
        self.showLL_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showLL_trend.setChecked(True)
        self.showLL_trend.setObjectName("showLL_trend")
        self.gridLayout_2.addWidget(self.showLL_trend, 0, 1, 1, 1)
        self.showLSpec_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showLSpec_trend.setChecked(True)
        self.showLSpec_trend.setObjectName("showLSpec_trend")
        self.gridLayout_2.addWidget(self.showLSpec_trend, 2, 1, 1, 1)
        self.showMean_trend = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.showMean_trend.setChecked(True)
        self.showMean_trend.setObjectName("showMean_trend")
        self.gridLayout_2.addWidget(self.showMean_trend, 4, 1, 1, 1)
        self.trendscrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_4.addWidget(self.trendscrollArea)
        self.stackedWidget.addWidget(self.Trend)
        self.Histo = QtWidgets.QWidget()
        self.Histo.setObjectName("Histo")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.Histo)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.histoscrollArea = QtWidgets.QScrollArea(self.Histo)
        self.histoscrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.histoscrollArea.setWidgetResizable(True)
        self.histoscrollArea.setObjectName("histoscrollArea")
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 302, 252))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setHorizontalSpacing(15)
        self.gridLayout_3.setVerticalSpacing(20)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.showMean_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showMean_histo.setChecked(True)
        self.showMean_histo.setObjectName("showMean_histo")
        self.gridLayout_3.addWidget(self.showMean_histo, 7, 1, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem2, 17, 0, 1, 1)
        self.showHSpec_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showHSpec_histo.setChecked(True)
        self.showHSpec_histo.setObjectName("showHSpec_histo")
        self.gridLayout_3.addWidget(self.showHSpec_histo, 5, 0, 1, 1)
        self.showHL_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showHL_histo.setChecked(True)
        self.showHL_histo.setObjectName("showHL_histo")
        self.gridLayout_3.addWidget(self.showHL_histo, 3, 0, 1, 1)
        self.showLL_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showLL_histo.setChecked(True)
        self.showLL_histo.setObjectName("showLL_histo")
        self.gridLayout_3.addWidget(self.showLL_histo, 3, 1, 1, 1)
        self.showMedian_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showMedian_histo.setChecked(True)
        self.showMedian_histo.setObjectName("showMedian_histo")
        self.gridLayout_3.addWidget(self.showMedian_histo, 7, 0, 1, 1)
        self.showLSpec_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showLSpec_histo.setChecked(True)
        self.showLSpec_histo.setObjectName("showLSpec_histo")
        self.gridLayout_3.addWidget(self.showLSpec_histo, 5, 1, 1, 1)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_8 = QtWidgets.QLabel(self.scrollAreaWidgetContents_2)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_7.addWidget(self.label_8)
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
        self.gridLayout_3.addLayout(self.horizontalLayout_7, 16, 0, 1, 2)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_2 = QtWidgets.QLabel(self.scrollAreaWidgetContents_2)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_4.addWidget(self.label_2)
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
        self.gridLayout_3.addLayout(self.horizontalLayout_4, 14, 1, 1, 1)
        self.showBar_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showBar_histo.setChecked(True)
        self.showBar_histo.setObjectName("showBar_histo")
        self.gridLayout_3.addWidget(self.showBar_histo, 14, 0, 1, 1)
        self.showBoxp_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showBoxp_histo.setChecked(True)
        self.showBoxp_histo.setObjectName("showBoxp_histo")
        self.gridLayout_3.addWidget(self.showBoxp_histo, 8, 0, 1, 1)
        self.showBpOutlier_histo = QtWidgets.QCheckBox(self.scrollAreaWidgetContents_2)
        self.showBpOutlier_histo.setChecked(True)
        self.showBpOutlier_histo.setObjectName("showBpOutlier_histo")
        self.gridLayout_3.addWidget(self.showBpOutlier_histo, 8, 1, 1, 1)
        self.histoscrollArea.setWidget(self.scrollAreaWidgetContents_2)
        self.verticalLayout_7.addWidget(self.histoscrollArea)
        self.stackedWidget.addWidget(self.Histo)
        self.PPQQ = QtWidgets.QWidget()
        self.PPQQ.setObjectName("PPQQ")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.PPQQ)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.ppqqscrollArea = QtWidgets.QScrollArea(self.PPQQ)
        self.ppqqscrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.ppqqscrollArea.setWidgetResizable(True)
        self.ppqqscrollArea.setObjectName("ppqqscrollArea")
        self.scrollAreaWidgetContents_5 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_5.setGeometry(QtCore.QRect(0, 0, 205, 84))
        self.scrollAreaWidgetContents_5.setObjectName("scrollAreaWidgetContents_5")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents_5)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_4.setHorizontalSpacing(15)
        self.gridLayout_4.setVerticalSpacing(20)
        self.gridLayout_4.setObjectName("gridLayout_4")
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_4.addItem(spacerItem3, 3, 0, 1, 1)
        self.xDataCombobox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.xDataCombobox.sizePolicy().hasHeightForWidth())
        self.xDataCombobox.setSizePolicy(sizePolicy)
        self.xDataCombobox.setObjectName("xDataCombobox")
        self.xDataCombobox.addItem("")
        self.xDataCombobox.addItem("")
        self.xDataCombobox.addItem("")
        self.xDataCombobox.addItem("")
        self.gridLayout_4.addWidget(self.xDataCombobox, 0, 1, 1, 1)
        self.yDataCombobox = QtWidgets.QComboBox(self.scrollAreaWidgetContents_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.yDataCombobox.sizePolicy().hasHeightForWidth())
        self.yDataCombobox.setSizePolicy(sizePolicy)
        self.yDataCombobox.setObjectName("yDataCombobox")
        self.yDataCombobox.addItem("")
        self.yDataCombobox.addItem("")
        self.yDataCombobox.addItem("")
        self.yDataCombobox.addItem("")
        self.gridLayout_4.addWidget(self.yDataCombobox, 1, 1, 1, 1)
        self.label_10 = QtWidgets.QLabel(self.scrollAreaWidgetContents_5)
        self.label_10.setObjectName("label_10")
        self.gridLayout_4.addWidget(self.label_10, 0, 0, 1, 1)
        self.label_11 = QtWidgets.QLabel(self.scrollAreaWidgetContents_5)
        self.label_11.setObjectName("label_11")
        self.gridLayout_4.addWidget(self.label_11, 1, 0, 1, 1)
        self.ppqqscrollArea.setWidget(self.scrollAreaWidgetContents_5)
        self.verticalLayout_5.addWidget(self.ppqqscrollArea)
        self.stackedWidget.addWidget(self.PPQQ)
        self.Color = QtWidgets.QWidget()
        self.Color.setObjectName("Color")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.Color)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.colorscrollArea = QtWidgets.QScrollArea(self.Color)
        self.colorscrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.colorscrollArea.setLineWidth(0)
        self.colorscrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.colorscrollArea.setWidgetResizable(True)
        self.colorscrollArea.setObjectName("colorscrollArea")
        self.scrollAreaWidgetContents_4 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_4.setGeometry(QtCore.QRect(0, 0, 506, 277))
        self.scrollAreaWidgetContents_4.setObjectName("scrollAreaWidgetContents_4")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_4)
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_9.setSpacing(12)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.site_groupBox = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_4)
        self.site_groupBox.setObjectName("site_groupBox")
        self.gridLayout_site_color = QtWidgets.QGridLayout(self.site_groupBox)
        self.gridLayout_site_color.setObjectName("gridLayout_site_color")
        self.verticalLayout_9.addWidget(self.site_groupBox)
        self.sbin_groupBox = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_4)
        self.sbin_groupBox.setObjectName("sbin_groupBox")
        self.gridLayout_sbin_color = QtWidgets.QGridLayout(self.sbin_groupBox)
        self.gridLayout_sbin_color.setObjectName("gridLayout_sbin_color")
        self.verticalLayout_9.addWidget(self.sbin_groupBox)
        self.hbin_groupBox = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_4)
        self.hbin_groupBox.setObjectName("hbin_groupBox")
        self.gridLayout_hbin_color = QtWidgets.QGridLayout(self.hbin_groupBox)
        self.gridLayout_hbin_color.setObjectName("gridLayout_hbin_color")
        self.verticalLayout_9.addWidget(self.hbin_groupBox)
        self.colorscrollArea.setWidget(self.scrollAreaWidgetContents_4)
        self.verticalLayout_8.addWidget(self.colorscrollArea)
        self.stackedWidget.addWidget(self.Color)
        self.horizontalLayout.addWidget(self.stackedWidget)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
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
        font.setBold(True)
        font.setWeight(75)
        self.Cancel.setFont(font)
        self.Cancel.setStyleSheet("QPushButton {\n"
"color: white;\n"
"background-color: rgb(120, 120, 120); \n"
"border: 1px solid rgb(120, 120, 120); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(50, 50, 50); \n"
"border: 1px solid rgb(50, 50, 50);}")
        self.Cancel.setObjectName("Cancel")
        self.horizontalLayout_3.addWidget(self.Cancel)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.retranslateUi(Setting)
        self.stackedWidget.setCurrentIndex(0)
        self.xDataCombobox.setCurrentIndex(2)
        self.showBoxp_histo.toggled['bool'].connect(self.showBpOutlier_histo.setEnabled)
        self.showBar_histo.toggled['bool'].connect(self.lineEdit_binCount.setEnabled)
        self.precisionSlider.sliderMoved['int'].connect(self.label_5.setNum)
        QtCore.QMetaObject.connectSlotsByName(Setting)

    def retranslateUi(self, Setting):
        _translate = QtCore.QCoreApplication.translate
        Setting.setWindowTitle(_translate("Setting", "Form"))
        self.generalBtn.setText(_translate("Setting", "General"))
        self.trendBtn.setText(_translate("Setting", "Trend Plot"))
        self.histoBtn.setText(_translate("Setting", "Histo Plot"))
        self.ppqqBtn.setText(_translate("Setting", "P-P/Q-Q Plot"))
        self.colorBtn.setText(_translate("Setting", "Color Setting"))
        self.symbol_groupBox.setTitle(_translate("Setting", "Point Style"))
        self.label_6.setText(_translate("Setting", "Find Low Cpk:"))
        self.langCombobox.setItemText(0, _translate("Setting", "English"))
        self.langCombobox.setItemText(1, _translate("Setting", "简体中文"))
        self.sortTestListComboBox.setItemText(0, _translate("Setting", "In Original Order"))
        self.sortTestListComboBox.setItemText(1, _translate("Setting", "By Test Number"))
        self.sortTestListComboBox.setItemText(2, _translate("Setting", "By Test Name"))
        self.label_lang.setText(_translate("Setting", "Language:"))
        self.label_3.setText(_translate("Setting", "Data Notation:"))
        self.notationCombobox.setItemText(0, _translate("Setting", "Automatic"))
        self.notationCombobox.setItemText(1, _translate("Setting", "Float Number"))
        self.notationCombobox.setItemText(2, _translate("Setting", "Scientific Notation"))
        self.checkCpkcomboBox.setItemText(0, _translate("Setting", "Enable"))
        self.checkCpkcomboBox.setItemText(1, _translate("Setting", "Disable"))
        self.label_5.setText(_translate("Setting", "3"))
        self.label_7.setText(_translate("Setting", "Sort TestList:"))
        self.label_4.setText(_translate("Setting", "Data Precison:"))
        self.label.setText(_translate("Setting", "Font:"))
        self.label_9.setText(_translate("Setting", "Cpk Threshold:"))
        self.showMedian_trend.setText(_translate("Setting", "Show Median Line"))
        self.showHL_trend.setText(_translate("Setting", "Show Upper Limit"))
        self.showHSpec_trend.setText(_translate("Setting", "Show High Spec"))
        self.showLL_trend.setText(_translate("Setting", "Show Lower Limit"))
        self.showLSpec_trend.setText(_translate("Setting", "Show Low Spec"))
        self.showMean_trend.setText(_translate("Setting", "Show Mean Line"))
        self.showMean_histo.setText(_translate("Setting", "Show Mean Line"))
        self.showHSpec_histo.setText(_translate("Setting", "Show High Spec"))
        self.showHL_histo.setText(_translate("Setting", "Show Upper Limit"))
        self.showLL_histo.setText(_translate("Setting", "Show Lower Limit"))
        self.showMedian_histo.setText(_translate("Setting", "Show Median Line"))
        self.showLSpec_histo.setText(_translate("Setting", "Show Low Spec"))
        self.label_8.setText(_translate("Setting", "σ Lines:"))
        self.sigmaCombobox.setItemText(0, _translate("Setting", "Hide All"))
        self.sigmaCombobox.setItemText(1, _translate("Setting", "Show ±3σ"))
        self.sigmaCombobox.setItemText(2, _translate("Setting", "Show ±3σ, ±6σ"))
        self.sigmaCombobox.setItemText(3, _translate("Setting", "Show ±3σ, ±6σ, ±9σ"))
        self.label_2.setText(_translate("Setting", "Bin Count:"))
        self.showBar_histo.setText(_translate("Setting", "Show Histo Bars"))
        self.showBoxp_histo.setText(_translate("Setting", "Show Boxplot"))
        self.showBpOutlier_histo.setText(_translate("Setting", "Show Boxplot Outlier"))
        self.xDataCombobox.setItemText(0, _translate("Setting", "Data Quantiles"))
        self.xDataCombobox.setItemText(1, _translate("Setting", "Data Percentiles"))
        self.xDataCombobox.setItemText(2, _translate("Setting", "Normal Quantiles"))
        self.xDataCombobox.setItemText(3, _translate("Setting", "Normal Percentiles"))
        self.yDataCombobox.setItemText(0, _translate("Setting", "Data Quantiles"))
        self.yDataCombobox.setItemText(1, _translate("Setting", "Data Percentiles"))
        self.yDataCombobox.setItemText(2, _translate("Setting", "Normal Quantiles"))
        self.yDataCombobox.setItemText(3, _translate("Setting", "Normal Percentiles"))
        self.label_10.setText(_translate("Setting", "X Axis:"))
        self.label_11.setText(_translate("Setting", "Y Axis:"))
        self.site_groupBox.setTitle(_translate("Setting", "Site Colors"))
        self.sbin_groupBox.setTitle(_translate("Setting", "Software Bin Colors"))
        self.hbin_groupBox.setTitle(_translate("Setting", "Hardware Bin Colors"))
        self.Confirm.setText(_translate("Setting", "Confirm"))
        self.Confirm.setShortcut(_translate("Setting", "Return"))
        self.Cancel.setText(_translate("Setting", "Cancel"))
        self.Cancel.setShortcut(_translate("Setting", "Esc"))
