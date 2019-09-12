from PyQt5.QtWidgets import QDialogButtonBox, QGridLayout, QTreeView, QItemDelegate, QSpinBox, \
    QAction, QMenu, QMessageBox, QPushButton
from PyQt5.QtCore import QAbstractItemModel
from PyQt5.QtCore import Qt, QModelIndex

from app.data.database import DB

from app.editor.custom_gui import SimpleDialog

class StatDialog(SimpleDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent
        self._data = DB.stats

        self.setWindowTitle('Stat Editor')

        self.saved_data = self.save()

        self.model = MultiAttrListModel(self._data, ("nid", "name", "maximum", "desc"), {"HP", "MOV"}, self)
        self.view = RightClickTreeView(self)
        self.view.setModel(self.model)
        delegate = IntDelegate(self.view)
        self.view.setItemDelegate(delegate)

        layout = QGridLayout(self)
        layout.addWidget(self.view, 0, 0, 1, 2)
        self.setLayout(layout)

        self.add_button = QPushButton("Add Stat")
        self.add_button.clicked.connect(self.model.add_new_row)
        layout.addWidget(self.add_button, 1, 0, alignment=Qt.AlignLeft)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        layout.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

    def save(self):
        return self._data.serialize()

    def restore(self, data):
        self._data.restore(data)

    def accept(self):
        super().accept()

    def reject(self):
        self.restore(self.saved_data)
        super().reject()

class RightClickTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.uniformItemSizes = True

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customMenuRequested)

    def customMenuRequested(self, pos):
        index = self.indexAt(pos)

        delete_action = QAction("Delete", self, triggered=lambda: self.delete(index.row()))
        menu = QMenu(self)
        menu.addAction(delete_action)

        menu.popup(self.viewport().mapToGlobal(pos))

    def delete(self, idx):
        self.parent().model.delete(idx)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Delete:
            self.delete(self.currentIndex().row())

class IntDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 2:
            editor = QSpinBox(parent)
            editor.setRange(1, 255)
            return editor
        else:
            return super().createEditor(parent, option, index)

class MultiAttrListModel(QAbstractItemModel):
    def __init__(self, data, headers, locked=None, parent=None):
        super().__init__(parent)
        self.window = parent
        self._data = data
        self._headers = headers
        self.locked = locked
        if not locked:
            self.locked = set()

    def delete(self, idx):
        if self._data.values()[idx].nid not in self.locked:
            self._data.pop(idx)
            self.layoutChanged.emit()
        else:
            QMessageBox.critical(self.window, 'Error', "Cannot delete this row!")

    def add_new_row(self):
        self._data.add_new_default()
        self.layoutChanged.emit()
        last_index = self.index(self.rowCount() - 1, 0)
        self.window.view.setCurrentIndex(last_index)

    def headerData(self, idx, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Vertical:
            return None
        elif orientation == Qt.Horizontal:
            return self._headers[idx].capitalize()

    def index(self, row, column, parent_index=QModelIndex()):
        if self.hasIndex(row, column, parent_index):
            return self.createIndex(row, column)
        return QModelIndex()

    def parent(self, index):
        return QModelIndex()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            data = self._data.values()[index.row()]
            return getattr(data, self._headers[index.column()])
        elif role == Qt.EditRole:
            data = self._data.values()[index.row()]
            return getattr(data, self._headers[index.column()])
        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        data = self._data.values()[index.row()]
        setattr(data, self._headers[index.column()], value)
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        basic_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemNeverHasChildren
        if self._data.values()[index.row()].nid not in self.locked or index.column() != 0:
            basic_flags |= Qt.ItemIsEditable
        return basic_flags

# Testing
# Run "python -m app.editor.stat_database" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = StatDialog()
    window.show()
    app.exec_()
