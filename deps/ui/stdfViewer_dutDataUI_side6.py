# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stdfViewer_dutDataUI.ui'
##
## Created by: Qt User Interface Compiler version 6.0.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Ui_dutData(object):
    def setupUi(self, dutData):
        if not dutData.objectName():
            dutData.setObjectName(u"dutData")
        dutData.resize(993, 385)
        self.verticalLayout = QVBoxLayout(dutData)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tableView_dutData = QTableView(dutData)
        self.tableView_dutData.setObjectName(u"tableView_dutData")

        self.verticalLayout.addWidget(self.tableView_dutData)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.save = QPushButton(dutData)
        self.save.setObjectName(u"save")
        self.save.setMinimumSize(QSize(0, 25))
        font = QFont()
        font.setFamily(u"Tahoma")
        font.setBold(True)
        self.save.setFont(font)
        self.save.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(0, 100, 200); \n"
"border: 1px solid rgb(0, 100, 200); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(0, 50, 100); \n"
"border: 1px solid rgb(0, 50, 100);}")

        self.horizontalLayout.addWidget(self.save)

        self.save_xlsx = QPushButton(dutData)
        self.save_xlsx.setObjectName(u"save_xlsx")
        self.save_xlsx.setMinimumSize(QSize(0, 25))
        self.save_xlsx.setFont(font)
        self.save_xlsx.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(0, 120, 0); \n"
"border: 1px solid rgb(0, 120, 0); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(0, 50, 0); \n"
"border: 1px solid rgb(0, 50, 0);}")

        self.horizontalLayout.addWidget(self.save_xlsx)

        self.close = QPushButton(dutData)
        self.close.setObjectName(u"close")
        self.close.setMinimumSize(QSize(0, 25))
        self.close.setFont(font)
        self.close.setStyleSheet(u"QPushButton {\n"
"color: white;\n"
"background-color: rgb(120, 120, 120); \n"
"border: 1px solid rgb(120, 120, 120); \n"
"border-radius: 5px;}\n"
"\n"
"QPushButton:pressed {\n"
"background-color: rgb(50, 50, 50); \n"
"border: 1px solid rgb(50, 50, 50);}")

        self.horizontalLayout.addWidget(self.close)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(dutData)

        QMetaObject.connectSlotsByName(dutData)
    # setupUi

    def retranslateUi(self, dutData):
        dutData.setWindowTitle(QCoreApplication.translate("dutData", u"STDF Viewer - DUT Data Table", None))
        self.save.setText(QCoreApplication.translate("dutData", u"Save to CSV", None))
        self.save_xlsx.setText(QCoreApplication.translate("dutData", u"Save to XLSX", None))
        self.close.setText(QCoreApplication.translate("dutData", u"Close", None))
    # retranslateUi

