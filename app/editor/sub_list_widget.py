from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QTreeView, QTableView
from PyQt5.QtCore import Qt

from app.editor.custom_gui import SingleListModel, MultiAttrListModel, RightClickTreeView

class BasicSingleListWidget(QWidget):
    def __init__(self, data, title, dlgate, parent=None):
        super().__init__(parent)
        self.initiate(data, parent)

        self.model = SingleListModel(self.current, title, self)
        self.view = QTreeView(self)
        self.view.setModel(self.model)
        delegate = dlgate(self.view)
        self.view.setItemDelegate(delegate)
        self.view.resizeColumnToContents(0)

        self.placement(data, title)

    def initiate(self, data, parent):
        self.window = parent
        self.current = data
        self._actions = []

    def placement(self, data, title):
        self.layout = QGridLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.view, 1, 0, 1, 2)
        self.setLayout(self.layout)

        label = QLabel(title)
        label.setAlignment(Qt.AlignBottom)
        self.layout.addWidget(label, 0, 0)

    def set_current(self, data):
        self.current = data
        self.model.set_new_data(self.current)

class AppendSingleListWidget(BasicSingleListWidget):
    def __init__(self, data, title, dlgate, parent=None):
        QWidget.__init__(self, parent)
        self.initiate(data, parent)

        self.model = SingleListModel(self.current, title, self)
        self.view = RightClickTreeView(parent=self)
        self.view.setModel(self.model)
        delegate = dlgate(self.view)
        self.view.setItemDelegate(delegate)
        self.view.resizeColumnToContents(0)

        self.placement(data, title)

        add_button = QPushButton("+")
        add_button.setMaximumWidth(30)
        add_button.clicked.connect(self.model.add_new_row)
        self.layout.addWidget(add_button, 0, 1, alignment=Qt.AlignRight)

class BasicMultiListWidget(BasicSingleListWidget):
    def __init__(self, data, title, attrs, dlgate, parent=None):
        QWidget.__init__(self, parent)
        self.initiate(data, parent)

        self.model = MultiAttrListModel(self.current, attrs, parent=self)
        self.view = QTreeView(self)
        self.view.setModel(self.model)
        delegate = dlgate(self.view)
        self.view.setItemDelegate(delegate)
        for col in range(len(attrs)):
            self.view.resizeColumnToContents(col)

        self.placement(data, title)

class AppendMultiListWidget(BasicSingleListWidget):
    def __init__(self, data, title, attrs, dlgate, parent=None):
        QWidget.__init__(self, parent)
        self.initiate(data, parent)

        self.model = MultiAttrListModel(self.current, attrs, parent=self)
        self.view = RightClickTreeView(parent=self)
        self.view.setModel(self.model)
        delegate = dlgate(self.view)
        self.view.setItemDelegate(delegate)
        for col in range(len(attrs)):
            self.view.resizeColumnToContents(col)

        self.placement(data, title)

        add_button = QPushButton("+")
        add_button.setMaximumWidth(30)
        add_button.clicked.connect(self.model.add_new_row)
        self.layout.addWidget(add_button, 0, 1, alignment=Qt.AlignRight)
