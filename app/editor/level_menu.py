from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QDialog, QLabel
from PyQt5.QtWidgets import QFormLayout, QLineEdit, QDialogButtonBox, QListView
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QColor
from PyQt5.QtCore import Qt

from app.data.database import DB

from app.editor import commands

class LevelListModel(QStandardItemModel):
    def __init__(self, window=None):
        super().__init__(window)
        self.level_list = DB.level_list
        for level in self.level_list:
            item = QStandardItem(level.nid + ' : ' + level.title)
            self.appendRow(item)

    def insert(self, idx, level):
        self.level_list.insert(idx, level)
        item = QStandardItem(level.nid + ' : ' + level.title)
        self.insertRow(idx, item)
        return self.indexFromItem(item)

    def remove(self, idx, level):
        self.level_list.remove(level)
        self.takeRow(idx)

    def get_index(self, level):
        return self.level_list.index(level)

    def get_level_from_index(self, model_index):
        row = model_index.row()
        if row >= 0:
            return self.level_list[row]
        else:
            return None

    def get_nids(self):
        return [level.nid for level in self.level_list]

class LevelView(QListView):
    def currentChanged(self, current, previous):
        super().currentChanged(current, previous)
        level = self.model().get_level_from_index(current)
        if level:
            self.parentWidget().main_editor.set_current_level(level)

class LevelMenu(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.main_editor = window

        self.grid = QGridLayout()
        self.setLayout(self.grid)

        self.listview = LevelView(self)
        self.listview.setMinimumSize(128, 320)
        self.listview.uniformItemSizes = True

        self.model = LevelListModel(self)
        self.listview.setModel(self.model)

        self.button = QPushButton("Create New Level...")
        self.button.clicked.connect(self.create_new_level_dialog)

        self.grid.addWidget(self.listview, 0, 0)
        self.grid.addWidget(self.button, 1, 0)

    def create_new_level_dialog(self):
        dialog = NewLevelDialog(self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            new_level_command = dialog.get_command()
            self.main_editor.undo_stack.push(new_level_command)
            self.main_editor.map_view.update_view()

class NewLevelDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.level_menu = parent
        self.setWindowTitle("Create New Level...")

        self.form = QFormLayout(self)
        self.level_name = QLineEdit(self)
        self.level_id = QLineEdit(self)
        self.level_id.textChanged.connect(self.level_id_changed)
        self.warning_message = QLabel('')
        self.warning_message.setStyleSheet("QLabel { color : red; }")
        self.form.addRow('Full Title: ', self.level_name)
        self.form.addRow('Internal ID: ', self.level_id)
        self.form.addRow(self.warning_message)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.form.addRow(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        # No level id set
        accept_button = self.buttonbox.button(QDialogButtonBox.Ok)
        accept_button.setEnabled(False)
        self.warning_message.setText('No Level ID set.')

    def level_id_changed(self, text):
        if text in self.level_menu.model.get_nids():
            accept_button = self.buttonbox.button(QDialogButtonBox.Ok)
            accept_button.setEnabled(False)
            self.warning_message.setText('Level ID is already in use.')
        elif text:
            accept_button = self.buttonbox.button(QDialogButtonBox.Ok)
            accept_button.setEnabled(True)
            self.warning_message.setText('')
        else:
            accept_button = self.buttonbox.button(QDialogButtonBox.Ok)
            accept_button.setEnabled(False)
            self.warning_message.setText('No Level ID set.')

    def get_command(self):
        title = self.level_name.text()
        nid = self.level_id.text()
        return commands.CreateNewLevel(title, nid, self.level_menu)
