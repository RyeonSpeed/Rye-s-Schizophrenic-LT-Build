from functools import partial
import os
from typing import List, Optional, Tuple
from app.editor.file_manager.project_initializer import ProjectInitializer
from app.editor.settings.project_history_controller import ProjectHistoryEntry

from app.extensions.custom_gui import SimpleDialog
from app.utilities import str_utils
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QDir
from PyQt5.QtWidgets import (QListView, QLabel, QLineEdit, QTableView, QHBoxLayout, QHeaderView, QFileDialog, QMessageBox,
                             QPushButton, QVBoxLayout)
from PyQt5.QtGui import QStandardItemModel, QStandardItem


class RecentProjectsModel(QAbstractTableModel):
    def __init__(self, data: List[ProjectHistoryEntry]):
        super(RecentProjectsModel, self).__init__()
        self._data = data
        self.header_labels = ["Project Title",
                              "Project Full Path", "Last Opened on..."]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.getColumnProperty(index, self._data[index.row()])
        # elif role == Qt.TextAlignmentRole:
        #     return Qt.AlignRight
        return None

    def rowCount(self, index: QModelIndex):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index: QModelIndex):
        return 3

    def getColumnProperty(self, index: QModelIndex, entry: ProjectHistoryEntry) -> str:
        if index.column() == 0:
            return entry.name
        elif index.column() == 1:
            return entry.path
        elif index.column() == 2:
            return entry.get_last_open_time().isoformat() if entry.get_last_open_time() else "Unknown"

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)


class RecentProjectDialog(SimpleDialog):
    def __init__(self, recent_projects: List[ProjectHistoryEntry]):
        super().__init__()
        self.setWindowTitle("Recent Projects")
        self.projects = recent_projects
        self._selected_path: Optional[str] = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.project_table = QTableView()
        self.project_table.horizontalHeader().setStretchLastSection(True)
        self.project_table.verticalHeader().hide()
        self.project_table.setShowGrid(False)
        self.model = RecentProjectsModel(self.projects)
        self.project_table.setModel(self.model)
        self.project_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.project_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        self.project_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_table.resizeColumnsToContents()
        self.project_table.setSelectionBehavior(QTableView.SelectRows)
        self.project_table.doubleClicked.connect(self.on_select_project)

        button_layout = QHBoxLayout()
        self.open_other_button = QPushButton("Open other...", self)
        self.open_other_button.clicked.connect(self.on_click_open)
        button_layout.addWidget(self.open_other_button)
        self.new_button = QPushButton("Create New...", self)
        self.new_button.clicked.connect(self.on_click_new)
        button_layout.addWidget(self.new_button)

        layout.addWidget(self.project_table)
        layout.addLayout(button_layout)

        dialogWidth = self.project_table.horizontalHeader().length() + 24
        dialogHeight = self.project_table.verticalHeader().length() + 104
        self.setFixedSize(dialogWidth, dialogHeight)

    def on_select_project(self, index: QModelIndex):
        row = index.row()
        project = self.projects[row]
        self._selected_path = project.path
        self.accept()

    def on_click_open(self):
        if self.projects:
            starting_path = os.path.join(self.projects[0].path, '..')
        else:
            starting_path = QDir.currentPath()
        fn = QFileDialog.getExistingDirectory(
            self, "Open Project Directory", starting_path)
        if fn:
            if not fn.endswith('.ltproj'):
                QMessageBox.warning(self.parent, "Incorrect directory type",
                                    "%s is not an .ltproj." % fn)
            else:
                self._selected_path = fn
                self.accept()

    def on_click_new(self):
        project_initializer = ProjectInitializer()
        result = project_initializer.full_create_new_project()
        if result:
            _, _, path = result
            self._selected_path = path
            self.accept()

    def get_selected(self) -> Optional[ProjectHistoryEntry]:
        return self._selected_path
