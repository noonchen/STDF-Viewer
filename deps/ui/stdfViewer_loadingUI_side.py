# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stdfViewer_loadingUI.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_loadingUI(object):
    def setupUi(self, loadingUI):
        if not loadingUI.objectName():
            loadingUI.setObjectName(u"loadingUI")
        loadingUI.resize(308, 50)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(loadingUI.sizePolicy().hasHeightForWidth())
        loadingUI.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(loadingUI)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.progressBar = QProgressBar(loadingUI)
        self.progressBar.setObjectName(u"progressBar")
        sizePolicy.setHeightForWidth(self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy)
        self.progressBar.setMinimumSize(QSize(250, 20))
        self.progressBar.setValue(0)

        self.horizontalLayout.addWidget(self.progressBar)


        self.retranslateUi(loadingUI)

        QMetaObject.connectSlotsByName(loadingUI)
    # setupUi

    def retranslateUi(self, loadingUI):
        loadingUI.setWindowTitle(QCoreApplication.translate("loadingUI", u"Loading STD file...", None))
        self.progressBar.setFormat(QCoreApplication.translate("loadingUI", u"Reading: %p%", None))
    # retranslateUi

