# -*- coding: utf-8 -*-

#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtWidgets


class Ui_loadingUI(object):
    def setupUi(self, loadingUI):
        loadingUI.setObjectName("loadingUI")
        loadingUI.resize(308, 50)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(loadingUI.sizePolicy().hasHeightForWidth())
        loadingUI.setSizePolicy(sizePolicy)
        self.horizontalLayout = QtWidgets.QHBoxLayout(loadingUI)
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.progressBar = QtWidgets.QProgressBar(loadingUI)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy)
        self.progressBar.setMinimumSize(QtCore.QSize(250, 20))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.horizontalLayout.addWidget(self.progressBar)

        self.retranslateUi(loadingUI)
        QtCore.QMetaObject.connectSlotsByName(loadingUI)

    def retranslateUi(self, loadingUI):
        _translate = QtCore.QCoreApplication.translate
        loadingUI.setWindowTitle(_translate("loadingUI", "Loading STD file..."))
        self.progressBar.setFormat(_translate("loadingUI", "Reading: %p%"))
