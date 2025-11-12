# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SnapMerge.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenuBar, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QStatusBar, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_SnapMergeWindow(object):
    def setupUi(self, SnapMergeWindow):
        if not SnapMergeWindow.objectName():
            SnapMergeWindow.setObjectName(u"SnapMergeWindow")
        SnapMergeWindow.resize(724, 565)
        self.centralwidget = QWidget(SnapMergeWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_input = QLabel(self.centralwidget)
        self.label_input.setObjectName(u"label_input")

        self.gridLayout.addWidget(self.label_input, 0, 0, 1, 1)

        self.input_line = QLineEdit(self.centralwidget)
        self.input_line.setObjectName(u"input_line")

        self.gridLayout.addWidget(self.input_line, 0, 1, 1, 1)

        self.browse_input_btn = QPushButton(self.centralwidget)
        self.browse_input_btn.setObjectName(u"browse_input_btn")

        self.gridLayout.addWidget(self.browse_input_btn, 0, 2, 1, 1)

        self.label_output = QLabel(self.centralwidget)
        self.label_output.setObjectName(u"label_output")

        self.gridLayout.addWidget(self.label_output, 1, 0, 1, 1)

        self.output_line = QLineEdit(self.centralwidget)
        self.output_line.setObjectName(u"output_line")

        self.gridLayout.addWidget(self.output_line, 1, 1, 1, 1)

        self.browse_output_btn = QPushButton(self.centralwidget)
        self.browse_output_btn.setObjectName(u"browse_output_btn")

        self.gridLayout.addWidget(self.browse_output_btn, 1, 2, 1, 1)

        self.optionsLayout = QHBoxLayout()
        self.optionsLayout.setObjectName(u"optionsLayout")
        self.include_sub_chk = QCheckBox(self.centralwidget)
        self.include_sub_chk.setObjectName(u"include_sub_chk")
        self.include_sub_chk.setChecked(True)

        self.optionsLayout.addWidget(self.include_sub_chk)

        self.label_sortby = QLabel(self.centralwidget)
        self.label_sortby.setObjectName(u"label_sortby")

        self.optionsLayout.addWidget(self.label_sortby)

        self.sort_by_combo = QComboBox(self.centralwidget)
        self.sort_by_combo.addItem("")
        self.sort_by_combo.addItem("")
        self.sort_by_combo.addItem("")
        self.sort_by_combo.setObjectName(u"sort_by_combo")

        self.optionsLayout.addWidget(self.sort_by_combo)

        self.sort_desc_chk = QCheckBox(self.centralwidget)
        self.sort_desc_chk.setObjectName(u"sort_desc_chk")

        self.optionsLayout.addWidget(self.sort_desc_chk)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.optionsLayout.addItem(self.horizontalSpacer_3)


        self.gridLayout.addLayout(self.optionsLayout, 2, 0, 1, 3)

        self.controlsLayout = QHBoxLayout()
        self.controlsLayout.setObjectName(u"controlsLayout")
        self.progress_bar = QProgressBar(self.centralwidget)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.controlsLayout.addWidget(self.progress_bar)

        self.run_btn = QPushButton(self.centralwidget)
        self.run_btn.setObjectName(u"run_btn")

        self.controlsLayout.addWidget(self.run_btn)

        self.cancel_btn = QPushButton(self.centralwidget)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.controlsLayout.addWidget(self.cancel_btn)


        self.gridLayout.addLayout(self.controlsLayout, 3, 0, 1, 3)


        self.verticalLayout.addLayout(self.gridLayout)

        self.log_text = QTextEdit(self.centralwidget)
        self.log_text.setObjectName(u"log_text")
        self.log_text.setReadOnly(True)

        self.verticalLayout.addWidget(self.log_text)

        SnapMergeWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(SnapMergeWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 724, 33))
        SnapMergeWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(SnapMergeWindow)
        self.statusbar.setObjectName(u"statusbar")
        SnapMergeWindow.setStatusBar(self.statusbar)

        self.retranslateUi(SnapMergeWindow)

        QMetaObject.connectSlotsByName(SnapMergeWindow)
    # setupUi

    def retranslateUi(self, SnapMergeWindow):
        SnapMergeWindow.setWindowTitle(QCoreApplication.translate("SnapMergeWindow", u"SnapMerge", None))
        self.label_input.setText(QCoreApplication.translate("SnapMergeWindow", u"Input folder:", None))
        self.browse_input_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Browse\u2026", None))
        self.label_output.setText(QCoreApplication.translate("SnapMergeWindow", u"Output PDF:", None))
        self.browse_output_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Save as\u2026", None))
        self.include_sub_chk.setText(QCoreApplication.translate("SnapMergeWindow", u"Include subfolders", None))
        self.label_sortby.setText(QCoreApplication.translate("SnapMergeWindow", u"Sort by:", None))
        self.sort_by_combo.setItemText(0, QCoreApplication.translate("SnapMergeWindow", u"name", None))
        self.sort_by_combo.setItemText(1, QCoreApplication.translate("SnapMergeWindow", u"created", None))
        self.sort_by_combo.setItemText(2, QCoreApplication.translate("SnapMergeWindow", u"modified", None))

        self.sort_desc_chk.setText(QCoreApplication.translate("SnapMergeWindow", u"Descending", None))
        self.run_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Generate PDF", None))
        self.cancel_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Cancel", None))
    # retranslateUi

