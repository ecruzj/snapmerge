# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'snap_merge_app.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMenuBar, QProgressBar, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

class Ui_SnapMergeWindow(object):
    def setupUi(self, SnapMergeWindow):
        if not SnapMergeWindow.objectName():
            SnapMergeWindow.setObjectName(u"SnapMergeWindow")
        SnapMergeWindow.resize(940, 581)
        self.centralwidget = QWidget(SnapMergeWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolbarLayout = QHBoxLayout()
        self.toolbarLayout.setObjectName(u"toolbarLayout")
        self.add_files_btn = QPushButton(self.centralwidget)
        self.add_files_btn.setObjectName(u"add_files_btn")

        self.toolbarLayout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton(self.centralwidget)
        self.add_folder_btn.setObjectName(u"add_folder_btn")

        self.toolbarLayout.addWidget(self.add_folder_btn)

        self.include_subfolders_chk = QCheckBox(self.centralwidget)
        self.include_subfolders_chk.setObjectName(u"include_subfolders_chk")

        self.toolbarLayout.addWidget(self.include_subfolders_chk)

        self.allow_duplicate_files_chk = QCheckBox(self.centralwidget)
        self.allow_duplicate_files_chk.setObjectName(u"allow_duplicate_files_chk")

        self.toolbarLayout.addWidget(self.allow_duplicate_files_chk)

        self.clean_work_chk = QCheckBox(self.centralwidget)
        self.clean_work_chk.setObjectName(u"clean_work_chk")
        self.clean_work_chk.setChecked(True)

        self.toolbarLayout.addWidget(self.clean_work_chk)

        self.remove_btn = QPushButton(self.centralwidget)
        self.remove_btn.setObjectName(u"remove_btn")

        self.toolbarLayout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton(self.centralwidget)
        self.clear_btn.setObjectName(u"clear_btn")

        self.toolbarLayout.addWidget(self.clear_btn)

        self.spacer_toolbar_1 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolbarLayout.addItem(self.spacer_toolbar_1)

        self.move_up_btn = QPushButton(self.centralwidget)
        self.move_up_btn.setObjectName(u"move_up_btn")

        self.toolbarLayout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton(self.centralwidget)
        self.move_down_btn.setObjectName(u"move_down_btn")

        self.toolbarLayout.addWidget(self.move_down_btn)

        self.spacer_toolbar_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.toolbarLayout.addItem(self.spacer_toolbar_2)

        self.sort_name_btn = QPushButton(self.centralwidget)
        self.sort_name_btn.setObjectName(u"sort_name_btn")

        self.toolbarLayout.addWidget(self.sort_name_btn)

        self.sort_type_btn = QPushButton(self.centralwidget)
        self.sort_type_btn.setObjectName(u"sort_type_btn")

        self.toolbarLayout.addWidget(self.sort_type_btn)


        self.verticalLayout.addLayout(self.toolbarLayout)

        self.files_table = QTableWidget(self.centralwidget)
        if (self.files_table.columnCount() < 6):
            self.files_table.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.files_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.files_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.files_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.files_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.files_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.files_table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        self.files_table.setObjectName(u"files_table")
        self.files_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.files_table.setDragEnabled(True)
        self.files_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.files_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.files_table.setProperty(u"dropIndicatorShown", True)

        self.verticalLayout.addWidget(self.files_table)

        self.bottomLayout = QGridLayout()
        self.bottomLayout.setObjectName(u"bottomLayout")
        self.label_output = QLabel(self.centralwidget)
        self.label_output.setObjectName(u"label_output")

        self.bottomLayout.addWidget(self.label_output, 1, 0, 1, 1)

        self.browse_output_btn = QPushButton(self.centralwidget)
        self.browse_output_btn.setObjectName(u"browse_output_btn")

        self.bottomLayout.addWidget(self.browse_output_btn, 1, 2, 1, 1)

        self.runLayout = QHBoxLayout()
        self.runLayout.setObjectName(u"runLayout")
        self.total_pages_label = QLabel(self.centralwidget)
        self.total_pages_label.setObjectName(u"total_pages_label")

        self.runLayout.addWidget(self.total_pages_label)

        self.spacer_run = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.runLayout.addItem(self.spacer_run)

        self.run_btn = QPushButton(self.centralwidget)
        self.run_btn.setObjectName(u"run_btn")

        self.runLayout.addWidget(self.run_btn)

        self.cancel_btn = QPushButton(self.centralwidget)
        self.cancel_btn.setObjectName(u"cancel_btn")

        self.runLayout.addWidget(self.cancel_btn)


        self.bottomLayout.addLayout(self.runLayout, 3, 0, 1, 4)

        self.output_line = QLineEdit(self.centralwidget)
        self.output_line.setObjectName(u"output_line")

        self.bottomLayout.addWidget(self.output_line, 1, 1, 1, 1)

        self.overwrite_chk = QCheckBox(self.centralwidget)
        self.overwrite_chk.setObjectName(u"overwrite_chk")

        self.bottomLayout.addWidget(self.overwrite_chk, 1, 3, 1, 1)


        self.verticalLayout.addLayout(self.bottomLayout)

        self.log_text = QTextEdit(self.centralwidget)
        self.log_text.setObjectName(u"log_text")
        self.log_text.setReadOnly(True)

        self.verticalLayout.addWidget(self.log_text)

        self.merge_progress_bar = QProgressBar(self.centralwidget)
        self.merge_progress_bar.setObjectName(u"merge_progress_bar")
        self.merge_progress_bar.setValue(0)
        self.merge_progress_bar.setTextVisible(True)

        self.verticalLayout.addWidget(self.merge_progress_bar)

        SnapMergeWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(SnapMergeWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 940, 33))
        SnapMergeWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(SnapMergeWindow)
        self.statusbar.setObjectName(u"statusbar")
        SnapMergeWindow.setStatusBar(self.statusbar)

        self.retranslateUi(SnapMergeWindow)

        QMetaObject.connectSlotsByName(SnapMergeWindow)
    # setupUi

    def retranslateUi(self, SnapMergeWindow):
        SnapMergeWindow.setWindowTitle(QCoreApplication.translate("SnapMergeWindow", u"SnapMerge", None))
        self.add_files_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Add files\u2026", None))
        self.add_folder_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Add folder\u2026", None))
        self.include_subfolders_chk.setText(QCoreApplication.translate("SnapMergeWindow", u"Subfolders", None))
        self.allow_duplicate_files_chk.setText(QCoreApplication.translate("SnapMergeWindow", u"Allow Duplicate Files", None))
        self.clean_work_chk.setText(QCoreApplication.translate("SnapMergeWindow", u"Clean Work", None))
        self.remove_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Remove", None))
        self.clear_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Clear", None))
        self.move_up_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Move up", None))
        self.move_down_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Move down", None))
        self.sort_name_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Sort by name", None))
        self.sort_type_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Sort by type", None))
        ___qtablewidgetitem = self.files_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("SnapMergeWindow", u"#", None));
        ___qtablewidgetitem1 = self.files_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("SnapMergeWindow", u"Name", None));
        ___qtablewidgetitem2 = self.files_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("SnapMergeWindow", u"Type", None));
        ___qtablewidgetitem3 = self.files_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("SnapMergeWindow", u"Size", None));
        ___qtablewidgetitem4 = self.files_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("SnapMergeWindow", u"Pages", None));
        ___qtablewidgetitem5 = self.files_table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("SnapMergeWindow", u"Path", None));
        self.label_output.setText(QCoreApplication.translate("SnapMergeWindow", u"Destination file:", None))
        self.browse_output_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Browse\u2026", None))
        self.total_pages_label.setText(QCoreApplication.translate("SnapMergeWindow", u"Total Pages: 0", None))
        self.run_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Merge", None))
        self.cancel_btn.setText(QCoreApplication.translate("SnapMergeWindow", u"Cancel", None))
        self.overwrite_chk.setText(QCoreApplication.translate("SnapMergeWindow", u"Overwrite if exists", None))
    # retranslateUi

